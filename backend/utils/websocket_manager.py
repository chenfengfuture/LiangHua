"""
WebSocket 全局管理器 — 单例模式

职责：
  - 维护所有活跃的 WebSocket 连接
  - 支持按 channel 分组（前端可订阅特定频道）
  - 支持广播 / 指定连接发送
  - 自动清理断开的连接
  - 异步安全（可在同步线程中调用，自动桥接到事件循环）

使用方式：
  from utils.websocket_manager import ws_manager

  # 前端连接端点中：
  await ws_manager.connect(websocket, channels=["news", "collect"])

  # 任意位置发送（自动检测当前线程/事件循环）：
  ws_manager.broadcast("news", {"type": "update", "data": ...})
"""

import asyncio
import json
import logging
import threading
from typing import Dict, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger("websocket")


class ConnectionManager:
    """WebSocket 全局单例连接管理器"""

    def __init__(self):
        # 所有活跃连接
        self._connections: Dict[WebSocket, Set[str]] = {}
        # 主事件循环引用（FastAPI 启动时设置）
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        # 线程锁
        self._lock = threading.Lock()

    # ─── 生命周期 ────────────────────────────────────────────────────────────

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """绑定主事件循环，在 FastAPI startup 中调用"""
        self._loop = loop

    async def connect(self, websocket: WebSocket, channels: Optional[list] = None):
        """接受新连接，可选订阅频道"""
        await websocket.accept()
        chs = set(channels) if channels else {"general"}
        with self._lock:
            self._connections[websocket] = chs
        logger.info(f"[WS] 新连接加入，频道: {chs}，当前连接数: {self.active_count}")

    async def disconnect(self, websocket: WebSocket):
        """移除断开的连接"""
        with self._lock:
            self._connections.pop(websocket, None)
        logger.info(f"[WS] 连接断开，当前连接数: {self.active_count}")

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._connections)

    # ─── 频道管理 ────────────────────────────────────────────────────────────

    async def subscribe(self, websocket: WebSocket, channels: list):
        """订阅频道"""
        with self._lock:
            if websocket in self._connections:
                self._connections[websocket].update(channels)

    async def unsubscribe(self, websocket: WebSocket, channels: list):
        """取消订阅频道"""
        with self._lock:
            if websocket in self._connections:
                self._connections[websocket] -= set(channels)

    # ─── 发送 ────────────────────────────────────────────────────────────────

    @staticmethod
    def _serialize(data: dict) -> str:
        """序列化消息，确保中文不转义"""
        return json.dumps(data, ensure_ascii=False, default=str)

    async def _send_to_ws(self, websocket: WebSocket, message: str):
        """安全发送单条消息（自动清理断开连接）"""
        try:
            await websocket.send_text(message)
        except Exception:
            logger.debug("[WS] 发送失败，移除断开连接")
            await self.disconnect(websocket)

    async def _send(self, websocket: WebSocket, data: dict):
        """序列化并发送"""
        await self._send_to_ws(websocket, self._serialize(data))

    # ─── 广播 ────────────────────────────────────────────────────────────────

    async def broadcast(self, channel: str, data: dict):
        """
        向订阅了指定频道的所有连接广播消息。

        可从 async 上下文直接调用，也可通过 broadcast_sync() 从同步线程调用。
        """
        if not self._connections:
            return

        message = self._serialize(data)
        targets = []

        with self._lock:
            for ws, channels in self._connections.items():
                if channel in channels:
                    targets.append(ws)

        # 并发发送
        if targets:
            await asyncio.gather(
                *[self._send_to_ws(ws, message) for ws in targets],
                return_exceptions=True,
            )

    async def broadcast_all(self, data: dict):
        """向所有连接广播（不区分频道）"""
        if not self._connections:
            return

        message = self._serialize(data)

        with self._lock:
            targets = list(self._connections.keys())

        if targets:
            await asyncio.gather(
                *[self._send_to_ws(ws, message) for ws in targets],
                return_exceptions=True,
            )

    # ─── 同步桥接（供非 async 线程调用） ────────────────────────────────────

    def broadcast_sync(self, channel: str, data: dict):
        """
        同步广播 — 可在任意线程中调用（如采集线程、LLM 线程）。
        自动检测是否在事件循环中，否则通过 run_coroutine_threadsafe 桥接。
        """
        if self._loop is None:
            logger.warning("[WS] 事件循环未设置，消息丢弃")
            return

        try:
            asyncio.run_coroutine_threadsafe(self.broadcast(channel, data), self._loop)
        except RuntimeError as e:
            logger.warning(f"[WS] 广播失败: {e}")

    def send_to_ws_sync(self, websocket: WebSocket, data: dict):
        """同步发送给指定连接"""
        if self._loop is None:
            logger.warning("[WS] 事件循环未设置，消息丢弃")
            return

        try:
            asyncio.run_coroutine_threadsafe(self._send(websocket, data), self._loop)
        except RuntimeError as e:
            logger.warning(f"[WS] 发送失败: {e}")

    def broadcast_all_sync(self, data: dict):
        """同步广播给所有连接"""
        if self._loop is None:
            logger.warning("[WS] 事件循环未设置，消息丢弃")
            return

        try:
            asyncio.run_coroutine_threadsafe(self.broadcast_all(data), self._loop)
        except RuntimeError as e:
            logger.warning(f"[WS] 广播失败: {e}")

    # ─── 批量清理 ────────────────────────────────────────────────────────────

    async def cleanup(self):
        """清理所有连接"""
        with self._lock:
            self._connections.clear()
        logger.info("[WS] 所有连接已清理")


# ─── 全局单例 ────────────────────────────────────────────────────────────────

ws_manager = ConnectionManager()
