#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化交易平台 - FastAPI 后端

重构原则：
1. 模块化：三大模块（股票、新闻、LLM）作为独立子包
2. 依赖注入：通过FastAPI的Depends()传递服务实例
3. 服务层分离：业务逻辑在services/目录，路由只负责HTTP层


数据库：lianghua (MySQL)，按年分表：stock_klines_YYYY
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

    # 1.1 确保所有基础表存在
    from models.stock_models import ensure_all_base_tables
    ensure_all_base_tables()
    logger.info("[启动] 数据库基础表检查完成")

    # 2. 行情采集器预热（后台线程）
    from utils.collector import warmup as collector_warmup
    collector_warmup()
    logger.info("[启动] 行情采集器预热完成")

    # 3. LLM API 可达性验证（后台线程）
    import threading
    from utils.llm import LLM
    threading.Thread(target=lambda: LLM().warmup(), daemon=True).start()
    logger.info("[启动] LLM API 可达性验证启动")

    # 4. 初始化Redis键
    from utils.redis_client import init_news_keys
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

    logger.info("应用启动完成")

    yield

    # 关闭时
    logger.info("应用关闭中...")

    # 1. 停止新闻后台任务
    from api.news.routes import stop_scheduler
    stop_scheduler()
    logger.info("[关闭] 新闻后台任务已停止")

    # 2. 关闭Redis连接
    from utils.redis_client import close_redis
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
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, reload=False)