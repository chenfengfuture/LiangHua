#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api/news/routes.py — 新闻模块统一路由（纯路由层）

参考 api/stock/routes.py 的结构：
  - 所有路由只做参数透传 + service 调用 + 返回
  - 任何业务逻辑均在 news_services/services/ 内

包含两类接口：
  1. 采集调度管理：状态、手动触发、Redis 清理
  2. 数据查询：单板块 / 多板块聚合 / 采集状态轮询

后台任务生命周期（start_scheduler / stop_scheduler）由 main.py 的 lifespan 调用。
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from news_services import (
    news_collect_service,
    news_fetch_service,
    news_finbert_manual_service,
    news_finbert_service,
    news_llm_service,
    news_persist_service,
    start_scheduled_batch,
    stop_scheduled_batch,
)
from utils.redis_client_compat import (
    NEWS_CCTV_TODONE_KEY,
    NEWS_COLLECT_TIME_KEYS,
    _get_client,
    get_all_collect_status,
)

logger = logging.getLogger("news_routes")
router = APIRouter(prefix="/api/news", tags=["news"])


# ═══════════════════════════════════════════════════════════════════
#  后台任务生命周期（由 main.py 的 lifespan 调用）
# ═══════════════════════════════════════════════════════════════════

def start_scheduler():
    """
    统一启动所有后台任务（项目启动时调用一次，幂等安全）。
    启动顺序：消费者先就位，再开生产者
      persist → llm → collect
    FinBERT 定时批量任务独立启动（每15分钟，非持续队列消费）
    """
    try:
        logger.info("[news] 启动后台任务...")
        news_persist_service.start()
        news_llm_service.start()
        news_collect_service.start()
        start_scheduled_batch()  # FinBERT 定时批量（每15分钟）
    except Exception as e:
        logger.error(f"[news] 启动后台任务失败: {e}")


def stop_scheduler():
    """
    停止所有后台任务（服务关闭时调用）
    关闭顺序：生产者先停，再停消费者
      collect → llm → persist
    """
    try:
        stop_scheduled_batch()  # FinBERT 定时批量先停
        news_collect_service.stop()
        news_llm_service.stop()
        news_persist_service.stop()
    except Exception as e:
        logger.error(f"[news] 停止后台任务失败: {e}")


# ═══════════════════════════════════════════════════════════════════
#  路由：模块状态 / 采集调度
# ═══════════════════════════════════════════════════════════════════

@router.get("/")
def get_news_status() -> Dict[str, Any]:
    """新闻模块状态概览"""
    try:
        return {
            "success": True,
            "module": "news",
            "timestamp": datetime.now().isoformat(),
            "queues": {
                "pending_llm": news_llm_service.get_pending_count(),
                "pending_finbert": news_finbert_service.get_pending_count(),
                "pending_persist": news_persist_service.get_pending_count(),
            },
            "analyzer": news_llm_service.get_status().get("data", {}),
            "finbert": news_finbert_service.get_status().get("data", {}),
            "persist": news_persist_service.get_status().get("data", {}),
            "collector": news_collect_service.get_status().get("data", {}),
            "redis_keys": {
                "cctv_todone": NEWS_CCTV_TODONE_KEY,
                "collect_time_keys": NEWS_COLLECT_TIME_KEYS,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/collect_all")
def collect_all_news_endpoint() -> Dict[str, Any]:
    """手动触发一次全量采集"""
    try:
        result = news_collect_service.collect_all()
        return {
            "success": result.get("success", True),
            "message": result.get("message", "全量新闻采集完成"),
            "data": result.get("data", {}),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"采集失败: {str(e)}")


@router.get("/status")
def get_detailed_status() -> Dict[str, Any]:
    """详细状态信息（采集、调度器、Redis 队列、LLM、持久化）"""
    try:
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "collect_status": get_all_collect_status(),
            "analyzer": news_llm_service.get_status().get("data", {}),
            "finbert": news_finbert_service.get_status().get("data", {}),
            "persist": news_persist_service.get_status().get("data", {}),
            "queues": {
                "pending_llm": news_llm_service.get_pending_count(),
                "pending_finbert": news_finbert_service.get_pending_count(),
                "pending_persist": news_persist_service.get_pending_count(),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取详细状态失败: {str(e)}")


@router.get("/clear_redis")
def clear_redis_cache() -> Dict[str, Any]:
    """清空采集时间缓存 + 待处理队列（不清 news:data:*）"""
    try:
        redis_client = _get_client()
        for key in NEWS_COLLECT_TIME_KEYS:
            redis_client.delete(key)
        redis_client.delete(NEWS_CCTV_TODONE_KEY)
        redis_client.delete("news:pending_llm")
        redis_client.delete("news:pending_finbert")
        redis_client.delete("news:pending_persist")

        return {
            "success": True,
            "message": "Redis缓存已清空",
            "cleared_keys": [
                *NEWS_COLLECT_TIME_KEYS,
                NEWS_CCTV_TODONE_KEY,
                "news:pending_llm",
                "news:pending_finbert",
                "news:pending_persist",
            ],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空Redis缓存失败: {str(e)}")


@router.get("/analyzer_status")
def get_llm_analyzer_status() -> Dict[str, Any]:
    """LLM 分析引擎状态"""
    return news_llm_service.get_status().get("data", {"running": False})


@router.get("/persist_status")
def get_persist_status() -> Dict[str, Any]:
    """持久化层状态"""
    return news_persist_service.get_status().get("data", {"running": False})


@router.get("/finbert_status")
def get_finbert_status() -> Dict[str, Any]:
    """FinBERT 情感分析层状态"""
    return news_finbert_service.get_status().get("data", {"running": False})


@router.post("/finbert/manual_batch")
def manual_finbert_batch(
    news_type: Optional[str] = Query(
        None,
        description="新闻类型（逗号分隔），如 company,cctv,caixin,global,notice,stock；为空则扫描所有类型",
    ),
    year_month: Optional[str] = Query(
        None,
        description="月份 YYYYMM，如 202605；为空则不限月份（扫描所有月份的分表）",
    ),
    limit: int = Query(
        500, ge=1, le=5000,
        description="每张分表最多扫描的候选记录数（1-5000）",
    ),
    force: bool = Query(
        False,
        description="是否强制重算（True 时忽略 sentiment_confidence 已有值；默认仅处理未做过的）",
    ),
) -> Dict[str, Any]:
    """
    手动触发批量 FinBERT 情感分析（同步执行）。

    流程：
      1. 直接扫描 MySQL 分表，捞出已完成 LLM 但未做 FinBERT 的新闻
      2. 调用 FinbertClient 单例做批量推理
      3. 同时更新 Redis（news:data:*）和 MySQL（CASE 批量 UPDATE）

    与后台 NewsFinbertService 完全独立，不入 pending_finbert 队列。
    """
    try:
        result = news_finbert_manual_service.run_manual_batch(
            news_type=news_type,
            year_month=year_month,
            limit=limit,
            force=force,
        )
        return {
            "success":   result.get("success", True),
            "message":   result.get("message", ""),
            "data":      result.get("data", {}),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("[news] 手动 FinBERT 批处理失败: %s", e)
        raise HTTPException(status_code=500, detail=f"手动 FinBERT 批处理失败: {str(e)}")


# ═══════════════════════════════════════════════════════════════════
#  路由：新闻数据查询（原 fetch_routes.py）
# ═══════════════════════════════════════════════════════════════════

@router.get("/fetch")
def fetch_all_sections(
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD，默认今天"),
    sections: Optional[str] = Query(None, description="板块列表，逗号分隔，默认全部"),
    limit: int = Query(500, ge=1, le=1000, description="每板块返回条数限制"),
    auto_collect: bool = Query(True, description="当日无数据时是否自动触发采集"),
) -> Dict[str, Any]:
    """多板块聚合查询接口（并行拉取所有板块数据）"""
    return news_fetch_service.fetch_all_sections(date, sections, limit, auto_collect)


@router.get("/fetch/status")
def fetch_status() -> Dict[str, Any]:
    """查询当前正在后台采集的板块列表"""
    return news_fetch_service.get_fetch_status()


@router.get("/fetch/{section}")
def fetch_single_section(
    section: str,
    date: Optional[str] = Query(None, description="日期 YYYY-MM-DD，默认今天"),
    limit: int = Query(500, ge=1, le=1000, description="返回条数限制 1-1000"),
    auto_collect: bool = Query(True, description="当日无数据时是否自动触发采集"),
) -> Dict[str, Any]:
    """单板块新闻查询接口"""
    return news_fetch_service.fetch_single_section(section, date, limit, auto_collect)
