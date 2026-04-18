#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻采集调度接口 & 后台任务管理 - 简化版本

重构原则：
1. 路由层只负责HTTP请求处理、参数验证、响应组装
2. 业务逻辑通过服务层调用
3. 使用简单的依赖注入
4. 禁止在路由中直接操作Redis和数据库
"""

import threading
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

# 导入工具模块
from utils.redis_client import (
    NEWS_CCTV_TODONE_KEY,
    NEWS_COLLECT_TIME_KEYS,
    _get_client,
    get_all_collect_status,
    pending_llm_size,
    pending_persist_size,
)

router = APIRouter(prefix="/api/news", tags=["news"])


# ═══════════════════════════════════════════════════════════════════
#  数据模型
# ═══════════════════════════════════════════════════════════════════

class SchedulerAction(BaseModel):
    """调度器操作请求"""
    action: str  # "pause" 或 "resume"


# ═══════════════════════════════════════════════════════════════════
#  服务实例获取函数
# ═══════════════════════════════════════════════════════════════════

def get_news_collector_service():
    """获取新闻采集服务实例"""
    from system_service.news_service import get_news_collector_service as _get_service
    return _get_service()


def get_news_llm_analyzer_service():
    """获取新闻LLM分析服务实例"""
    from system_service.news_service import get_news_llm_analyzer_service as _get_service
    return _get_service()


def get_news_persist_service():
    """获取新闻持久化服务实例"""
    from system_service.news_service import get_news_persist_service as _get_service
    return _get_service()


# ═══════════════════════════════════════════════════════════════════
#  后台任务管理函数（供main.py调用）
# ═══════════════════════════════════════════════════════════════════

def start_scheduler():
    """
    统一启动所有后台任务（项目启动时调用一次）
    """
    try:
        # 获取服务实例
        collector_service = get_news_collector_service()
        analyzer_service = get_news_llm_analyzer_service()
        persist_service = get_news_persist_service()
        
        # 1. 启动LLM分析引擎
        analyzer_service.start_analyzer()
        
        # 2. 启动持久化线程
        persist_service.start_persist()
        
        # 3. 启动定时采集任务
        collector_service.start_scheduler()
        
        print("[news] 所有后台任务已启动")
        
    except Exception as e:
        print(f"[news] 启动后台任务失败: {e}")


def stop_scheduler():
    """停止所有后台任务"""
    try:
        # 获取服务实例
        collector_service = get_news_collector_service()
        analyzer_service = get_news_llm_analyzer_service()
        persist_service = get_news_persist_service()
        
        # 1. 停止定时采集任务
        collector_service.stop_scheduler()
        
        # 2. 停止LLM分析引擎
        analyzer_service.stop_analyzer()
        
        # 3. 停止持久化线程
        persist_service.stop_persist()
        
        print("[news] 所有后台任务已停止")
        
    except Exception as e:
        print(f"[news] 停止后台任务失败: {e}")


# ═══════════════════════════════════════════════════════════════════
#  REST API 接口
# ═══════════════════════════════════════════════════════════════════

@router.get("/")
def get_news_status() -> Dict[str, Any]:
    """
    新闻模块状态概览
    
    返回：
        模块状态、队列大小、调度器状态等
    """
    try:
        # 获取Redis队列状态
        redis_client = _get_client()
        pending_llm = pending_llm_size(redis_client)
        pending_persist = pending_persist_size(redis_client)
        
        # 获取服务状态
        collector_service = get_news_collector_service()
        analyzer_service = get_news_llm_analyzer_service()
        persist_service = get_news_persist_service()
        
        collector_status = collector_service.get_status()
        analyzer_status = analyzer_service.get_analyzer_status()
        persist_status = persist_service.get_persist_status()
        
        return {
            "success": True,
            "module": "news",
            "timestamp": datetime.now().isoformat(),
            "queues": {
                "pending_llm": pending_llm,
                "pending_persist": pending_persist,
            },
            "system_service": {
                "collector": collector_status,
                "analyzer": analyzer_status,
                "persist": persist_status,
            },
            "redis_keys": {
                "cctv_todone": NEWS_CCTV_TODONE_KEY,
                "collect_time_keys": NEWS_COLLECT_TIME_KEYS,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/collect_all")
def collect_all_news() -> Dict[str, Any]:
    """
    手动触发一次全量采集
    
    注意：此接口立即返回，采集任务在后台执行
    """
    try:
        collector_service = get_news_collector_service()
        result = collector_service.collect_all_news()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"采集失败: {str(e)}")


@router.get("/status")
def get_detailed_status() -> Dict[str, Any]:
    """
    详细状态信息（采集、调度器、Redis队列、LLM、持久化）
    """
    try:
        # 获取Redis状态
        redis_client = _get_client()
        collect_status = get_all_collect_status(redis_client)
        
        # 获取服务状态
        collector_service = get_news_collector_service()
        analyzer_service = get_news_llm_analyzer_service()
        persist_service = get_news_persist_service()
        
        collector_status = collector_service.get_status()
        analyzer_status = analyzer_service.get_analyzer_status()
        persist_status = persist_service.get_persist_status()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "collect_status": collect_status,
            "collector": collector_status,
            "analyzer": analyzer_status,
            "persist": persist_status,
            "queues": {
                "pending_llm": pending_llm_size(redis_client),
                "pending_persist": pending_persist_size(redis_client),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取详细状态失败: {str(e)}")


@router.get("/clear_redis")
def clear_redis_cache() -> Dict[str, Any]:
    """
    清空采集时间缓存 + 待处理队列（不清news:data:*）
    
    注意：此操作会清空pending_llm和pending_persist队列
    """
    try:
        redis_client = _get_client()
        
        # 清空采集时间缓存
        for key in NEWS_COLLECT_TIME_KEYS:
            redis_client.delete(key)
        
        # 清空CCTV今日完成标记
        redis_client.delete(NEWS_CCTV_TODONE_KEY)
        
        # 清空待处理队列
        redis_client.delete("news:pending_llm")
        redis_client.delete("news:pending_persist")
        
        return {
            "success": True,
            "message": "Redis缓存已清空",
            "cleared_keys": [
                *NEWS_COLLECT_TIME_KEYS,
                NEWS_CCTV_TODONE_KEY,
                "news:pending_llm",
                "news:pending_persist",
            ],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空Redis缓存失败: {str(e)}")