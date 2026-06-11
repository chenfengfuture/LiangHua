"""
WebSocket 通用调用函数 — 全项目任意位置可用

设计原则：
  - 所有函数都是同步的（broadcast_sync），可从任意线程调用
  - 自动异常处理，不会因为 WebSocket 问题影响业务逻辑
  - 中文不转义（ensure_ascii=False）

频道约定：
  - news     : 新闻分析结果推送
  - collect  : 数据采集状态推送
  - llm      : LLM 分析进度推送（预留）
  - general  : 通用广播（默认频道）

使用方式：
  from utils.websocket_utils import ws_send_news_update, ws_send_collect_status

  # 在任意位置直接调用
  ws_send_news_update(12345, {"ai_interpretation": "...", "sentiment": 0.8})
  ws_send_collect_status("company", "collecting", 42)
"""

import logging
import time
from typing import Any, Dict, Optional

from utils.websocket_manager import ws_manager

logger = logging.getLogger("websocket_utils")


# ─── 新闻分析结果推送 ───────────────────────────────────────────────────────

def ws_send_news_update(news_id: int, data: Dict[str, Any]):
    """
    推送新闻分析结果到前端。

    Args:
        news_id: 新闻 ID
        data: 分析结果字典（ai_interpretation, ai_event_type, sentiment 等字段）
    """
    try:
        payload = {
            "type": "news_update",
            "news_id": news_id,
            "data": data,
            "timestamp": time.time(),
        }
        ws_manager.broadcast_sync("news", payload)
        logger.debug(f"[WS] 新闻分析推送: news_id={news_id}")
    except Exception as e:
        logger.warning(f"[WS] 新闻分析推送异常: {e}")


def ws_send_news_batch(results: list):
    """
    批量推送新闻分析结果。

    Args:
        results: [{"news_id": int, "data": dict}, ...]
    """
    try:
        payload = {
            "type": "news_batch",
            "results": results,
            "timestamp": time.time(),
        }
        ws_manager.broadcast_sync("news", payload)
        logger.debug(f"[WS] 新闻批量推送: {len(results)} 条")
    except Exception as e:
        logger.warning(f"[WS] 新闻批量推送异常: {e}")


# ─── 采集状态推送 ───────────────────────────────────────────────────────────

def ws_send_collect_status(
    source: str,
    status: str,
    count: int = 0,
    detail: Optional[str] = None,
):
    """
    推送数据采集状态到前端。

    Args:
        source: 采集来源 (company / caixin / global / notice / stock / cctv)
        status: 状态 (started / collecting / completed / failed)
        count:  已采集数量
        detail: 附加信息（错误消息等）
    """
    try:
        payload = {
            "type": "collect_status",
            "source": source,
            "status": status,
            "count": count,
            "detail": detail,
            "timestamp": time.time(),
        }
        ws_manager.broadcast_sync("collect", payload)
        logger.debug(f"[WS] 采集状态: {source} → {status} ({count})")
    except Exception as e:
        logger.warning(f"[WS] 采集状态推送异常: {e}")


def ws_send_collect_progress(
    source: str,
    total: int,
    current: int,
):
    """
    推送采集进度百分比。

    Args:
        source: 采集来源
        total:  总数
        current: 当前数
    """
    try:
        pct = round(current / total * 100, 1) if total > 0 else 0
        payload = {
            "type": "collect_progress",
            "source": source,
            "total": total,
            "current": current,
            "percent": pct,
            "timestamp": time.time(),
        }
        ws_manager.broadcast_sync("collect", payload)
    except Exception as e:
        logger.warning(f"[WS] 采集进度推送异常: {e}")


# ─── 通用推送 ───────────────────────────────────────────────────────────────

def ws_broadcast(channel: str, data: Dict[str, Any], msg_type: str = "message"):
    """
    通用频道广播。

    Args:
        channel: 频道名
        data: 消息数据
        msg_type: 消息类型标识
    """
    try:
        payload = {
            "type": msg_type,
            "data": data,
            "timestamp": time.time(),
        }
        ws_manager.broadcast_sync(channel, payload)
    except Exception as e:
        logger.warning(f"[WS] 通用广播异常: channel={channel}, {e}")
