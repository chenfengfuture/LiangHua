#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化交易平台 - FastAPI 后端

重构原则：
1. 模块化：三大模块（股票、新闻、LLM）作为独立子包
2. 依赖注入：通过FastAPI的Depends()传递服务实例
3. 服务层分离：业务逻辑在services/目录，路由只负责HTTP层


数据库：lianghua (MySQL)
主要分表策略：
  - 日K线按年分表：stock_klines_YYYY
  - 日内分时按日分表：intraday_transactions_YYYYMMDD
  - 新闻数据按月分表：news_global_YYYYMM
"""

import asyncio, json, logging, sys, os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 导入统一路由配置
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import configure_routes
# 导入配置
from config.settings import CORS_ORIGINS, SERVER_HOST, SERVER_PORT
# WebSocket 管理器
from utils.websocket_manager import ws_manager
# 导入日志配置
from config.logging_config import setup_logging, get_logger

# Windows 平台：修复 ProactorEventLoop 的 ConnectionResetError 警告
if sys.platform == 'win32':
    from asyncio.proactor_events import _ProactorBasePipeTransport

    def silence_event_loop_closed(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except RuntimeError as e:
                if str(e) != 'Event loop is closed':
                    raise
            except ConnectionResetError:
                pass
        return wrapper

    _ProactorBasePipeTransport.__del__ = silence_event_loop_closed(_ProactorBasePipeTransport.__del__)
    _ProactorBasePipeTransport._call_connection_lost = silence_event_loop_closed(_ProactorBasePipeTransport._call_connection_lost)


# 配置日志
setup_logging(
    log_dir="logs",
    log_file="lianghua.log",
    log_level="INFO",
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5,
    enable_console=True,
    enable_file=True
)

logger = get_logger("main")

# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时：
    1. 预热数据库连接池
    2. 启动行情采集器
    3. 验证LLM API可达性
    4. 初始化Redis键
    5. 启动新闻后台任务

    关闭时：
    1. 停止新闻后台任务
    2. 关闭Redis连接
    """
    # 启动时
    logger.info("应用启动中...")

    # 1. 数据库连接池预热
    from utils.db import warmup as db_warmup
    db_warmup()
    logger.info("[启动] 数据库连接池预热完成")

    # 1.1 确保所有基础表存在（使用统一初始化函数）
    from models import ensure_all_tables
    table_result = ensure_all_tables()
    if table_result["success"]:
        logger.info(f"[启动] 数据库表创建完成: 成功 {table_result['created']} 个表")
    else:
        logger.warning(f"[启动] 数据库表创建异常: {table_result['message']}")

    # 2. 行情采集器预热（后台线程）
    from utils.collector import warmup as collector_warmup
    collector_warmup()
    logger.info("[启动] 行情采集器预热完成")

    # 3. LLM API 可达性验证（后台线程）
    import threading
    from utils.llm import LLM
    threading.Thread(target=lambda: LLM().warmup(), daemon=True).start()
    logger.info("[启动] LLM API 可达性验证启动")

    # 3.5 FinBERT 模型预热（后台线程，避免阻塞启动；首次加载 ~2GB 内存）
    try:
        from news_services.config import FINBERT_ENABLED
        if FINBERT_ENABLED:
            from news_services.utils.finbert_client import FinbertClient
            threading.Thread(target=lambda: FinbertClient().warmup(), daemon=True).start()
            logger.info("[启动] FinBERT 模型预热启动")
    except Exception as e:
        logger.warning(f"[启动] FinBERT 预热触发失败（不影响启动）: {e}")

    # 4. 初始化Redis键
    from utils.redis_client_compat import init_news_keys
    init_news_keys()
    logger.info("[启动] Redis键初始化完成")

    # 5. 绑定 WebSocket 事件循环
    loop = asyncio.get_event_loop()
    ws_manager.set_loop(loop)
    logger.info("[启动] WebSocket 事件循环已绑定")

    # 6. 启动新闻后台任务
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from api.news.routes import start_scheduler
    start_scheduler()
    logger.info("[启动] 新闻后台任务已启动")

    # 6.5 启动 CCTV 历史数据回补（独立轻量线程，不阻塞）
    from news_services.services.news_cctv_backfill_service import start_cctv_backfill
    start_cctv_backfill()
    logger.info("[启动] CCTV 历史数据回补线程已启动")

    # 7. 启动收盘后自动K线采集（自愈型后台线程）
    from stock_services.mootdx.service import start_daily_kline_collector
    start_daily_kline_collector()
    logger.info("[启动] K线自动采集线程已启动")

    # 8. 启动收盘后指标计算（安全网：正常由 K 线采集完成后事件驱动触发）
    #    此线程作为兜底，防止采集触发失败导致指标漏算
    from stock_services.services.stock_indicator_service import stock_indicator_service

    def _indicator_compute_worker():
        """安全网：优先检测 Redis 标记（事件驱动），回退到收盘后兜底"""
        import time
        from datetime import datetime as _dt
        from stock_services.mootdx.service import MootdxKlineService
        while True:
            try:
                now = _dt.now()
                today_str = now.strftime("%Y%m%d")
                today_date = now.date()

                # 策略1: 先检查指标计算是否已完成
                already_done = False
                try:
                    from utils.redis_client_compat import _get_client
                    _rc = _get_client()
                    if _rc and _rc.exists(f"indicator:compute:running:{today_str}"):
                        logger.info("[indicator] 安全网：指标计算已在执行中，跳过")
                        time.sleep(3600)
                        continue
                    if _rc and _rc.exists(f"indicator:compute:done:{today_str}"):
                        already_done = True
                except Exception:
                    pass

                if already_done:
                    time.sleep(3600 * 6)
                    continue

                # 策略2: 检查 Redis 标记（kline 采集完成 → 触发指标计算的证据）
                redis_marker_found = False
                try:
                    from utils.redis_client_compat import _get_client
                    _rc = _get_client()
                    if _rc and _rc.exists(f"kline:collect:done:{today_str}"):
                        redis_marker_found = True
                except Exception:
                    pass

                # 策略3: 回退到时间检查（收盘后且为交易日）
                should_compute = redis_marker_found or (
                    now.hour >= 16 and MootdxKlineService.is_trading_day(today_date)
                )

                if should_compute:
                    logger.info("[indicator] 安全网：触发今日指标计算...")
                    stock_indicator_service.compute_today()
                    logger.info("[indicator] 安全网：今日指标计算完成")
                    time.sleep(3600 * 6)  # 算完后等 6 小时再检查
                else:
                    time.sleep(3600)
            except Exception as e:
                logger.warning(f"[indicator] 安全网异常: {e}")
                time.sleep(3600)

    t_indicator = threading.Thread(
        target=_indicator_compute_worker,
        daemon=True, name="indicator-auto-compute",
    )
    t_indicator.start()
    logger.info("[启动] 指标自动计算线程已启动")

    # 9. 初始化通用服务
    logger.info("应用启动完成")

    yield

    # 关闭时
    logger.info("应用关闭中...")

    # 1. 停止新闻后台任务
    from api.news.routes import stop_scheduler
    stop_scheduler()
    logger.info("[关闭] 新闻后台任务已停止")

    # 2. 关闭Redis连接
    from utils.redis_client_compat import close_redis
    close_redis()
    logger.info("[关闭] Redis连接已关闭")
    logger.info("应用关闭完成")


# 创建FastAPI应用
app = FastAPI(
    title="量华量化平台",
    description="晨枫",
    version="2.0.0",
    lifespan=lifespan
)

# ─── 全局 JSON 编码：禁止 ASCII 转义，中文/特殊字符原样输出 ─────────────────
class _CJKJSONResponse(JSONResponse):
    """自定义 JSONResponse：ensure_ascii=False，中文原样返回，不转为 \\uXXXX"""
    def render(self, content) -> bytes:
        import json as _json
        return _json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            default=str,
        ).encode("utf-8")

app.router.default_response_class = _CJKJSONResponse


# ─── CORS 配置 ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── WebSocket 端点 ─────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    通用 WebSocket 端点。

    前端连接示例：
      const ws = new WebSocket("ws://host:port/ws");
      ws.onmessage = (e) => JSON.parse(e.data);

    订阅频道（可选）：
      ws.send(JSON.stringify({ "action": "subscribe", "channels": ["news", "collect"] }));
    """
    # 默认订阅 general 频道
    await ws_manager.connect(websocket, channels=["general"])
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                action = msg.get("action")
                if action == "subscribe":
                    channels = msg.get("channels", [])
                    if channels:
                        await ws_manager.subscribe(websocket, channels)
                        logger.debug(f"[WS] 订阅频道: {channels}")
                elif action == "unsubscribe":
                    channels = msg.get("channels", [])
                    if channels:
                        await ws_manager.unsubscribe(websocket, channels)
                        logger.debug(f"[WS] 取消订阅: {channels}")
                elif action == "ping":
                    await ws_manager._send(websocket, {"type": "pong"})
                elif action == "kline_collect":
                    """
                    触发全市场/单股 K 线采集，通过 kline 频道流式推送进度。

                    请求体：
                    {
                      "action": "kline_collect",
                      "symbol": null,          // null=全市场,"000001"=单股
                      "freq": "day",
                      "start_date": "20260501",
                      "end_date": "20260526"
                    }

                    收到消息后自动订阅 kline 频道，后续采集进度通过该频道推送。
                    """
                    await ws_manager.subscribe(websocket, ["kline"])
                    freq = msg.get("freq", "day")
                    start_date = msg.get("start_date")
                    end_date = msg.get("end_date")
                    symbol = msg.get("symbol")
                    from stock_services.mootdx.kline_ws_collector import kline_ws_collector as _ws_collector
                    task_id = _ws_collector.start_collect({
                        "symbol": symbol,
                        "freq": freq,
                        "start_date": start_date,
                        "end_date": end_date,
                    })
                    await ws_manager._send(websocket, {
                        "type": "kline_task_started",
                        "task_id": task_id,
                        "freq": freq,
                        "message": f"K线采集任务已启动: {task_id}, 结果将通过 kline 频道推送",
                    })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)


# ─── 注册所有路由 ─────────────────────────────────────────────────────────────
configure_routes(app)


# ─── 注册全局异常处理器 ────────────────────────────────────────────────────────
from system_service.exception_handler import register_global_exception_handler
register_global_exception_handler(app)


# ─── 启动入口 ───────────────────────────────────────────────────────────────
def try_kill_port_owner(port: int = 8001) -> bool:
    """
    检查指定端口是否被占用，如果是则强制 kill 占用进程。
    返回 True 表示成功释放端口，False 表示端口未被占用或无需处理。
    """
    import subprocess
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines = result.stdout.splitlines()
        target_pids = set()
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5 and f":{port}" in parts[1] and "LISTENING" in parts[3].upper():
                target_pids.add(parts[4])
        if not target_pids:
            return False
        for pid in target_pids:
            try:
                logger.warning(f"[启动] 正在释放端口 {port}，终止旧进程 PID={pid}")
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except Exception:
                pass
        # 等待端口释放
        import time; time.sleep(1)
        return True
    except Exception as e:
        logger.warning(f"[启动] 端口检查异常（不影响启动）: {e}")
        return False


if __name__ == "__main__":
    import uvicorn

    # 启动前清理：如果端口被占用，强制释放
    try_kill_port_owner(SERVER_PORT)

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, reload=False)