"""
量化交易平台 - FastAPI 后端
数据库：lianghua (MySQL)，按年分表：stock_klines_YYYY

目录结构：
  main.py               # 只启动服务，不写任何接口
  config/               # 配置中心
  api/                  # 接口总目录
    news/routes.py      # 新闻模块（完全独立）
    stock/routes.py     # 股市模块（完全独立）
  utils/                # 核心高性能工具
    db.py               # 全局数据库连接池
    llm.py              # 全局 LLM 预加载
    collector.py        # 高性能采集器
    websocket_manager.py # 全局 WebSocket 单例
"""
import sys
import asyncio
import json
import logging
import threading

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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 导入配置
from config.settings import SERVER_HOST, SERVER_PORT, CORS_ORIGINS

# 导入路由模块
from api.stock.routes import router as stock_router
from api.news.routes import router as news_router
from api.news.fetch_routes import router as news_fetch_router
from api.llm.routes import router as llm_router

# WebSocket 管理器
from utils.websocket_manager import ws_manager

logger = logging.getLogger("main")

app = FastAPI(
    title="量华量化平台 API",
    description="股票日K线数据接口，对接 lianghua 数据库",
    version="1.0.0"
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


# ─── 启动事件：预热全局资源 ───────────────────────────────────────────────────

@app.on_event("startup")
def _warmup_all():
    """启动时预热：数据库连接池 + mootdx + LLM + WebSocket 事件循环"""
    from utils.db import warmup as db_warmup
    from utils.collector import warmup as collector_warmup
    from utils.llm import LLM

    # 1. 数据库连接池（同步预热，确保启动就绪）
    db_warmup()

    # 2. mootdx 行情连接（后台线程，不阻塞启动）
    collector_warmup()

    # 3. LLM API 可达性验证（后台线程，不阻塞启动）
    threading.Thread(target=lambda: LLM().warmup(), daemon=True).start()

    # 4. 绑定 WebSocket 事件循环（供同步线程广播使用）
    loop = asyncio.get_event_loop()
    ws_manager.set_loop(loop)
    logger.info("[启动] WebSocket 事件循环已绑定")

    # 5. Redis 连接 + 初始化新闻采集状态 key
    from utils.redis_client import init_news_keys, close_redis
    init_news_keys()

    # 6. 启动新闻定时采集任务（APScheduler，每 1 分钟检查一次）
    from api.news.routes import start_scheduler, stop_scheduler
    start_scheduler()

    # 注册关闭时释放资源
    @app.on_event("shutdown")
    def _shutdown_all():
        stop_scheduler()
        close_redis()


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


# ─── CORS ────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── 注册路由 ───────────────────────────────────────────────────────────────

app.include_router(stock_router)
app.include_router(news_router)
app.include_router(news_fetch_router)
app.include_router(llm_router)


# ─── 启动 ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, reload=False)
