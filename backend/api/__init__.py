#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API模块统一入口 - 重构版本

将三大模块（股票、新闻、LLM）作为独立子包，统一组装路由。
每个模块内部维护自己的路由和依赖，通过依赖注入解耦。

优化：路由导入延迟到函数调用时，避免模块加载时触发整个 import 树。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import APIRouter


def configure_routes(app):
    """
    统一配置所有路由到FastAPI应用（延迟导入，加速启动）
    
    参数：
        app: FastAPI应用实例
    """
    from .llm.routes import router as llm_router
    from .news.routes import router as news_router
    from .stock.routes import router as stock_router

    app.include_router(stock_router, tags=["stock"])
    app.include_router(news_router, tags=["news"])
    app.include_router(llm_router, tags=["AI"])
    print("[api] 已注册 3 个路由模块")


def get_all_routers():
    """获取所有路由配置（惰性导入）"""
    from .llm.routes import router as llm_router
    from .news.routes import router as news_router
    from .stock.routes import router as stock_router
    return [
        {"router": stock_router, "prefix": "", "tags": ["stock"], "description": "股票数据接口"},
        {"router": news_router, "prefix": "", "tags": ["news"], "description": "新闻采集管理 + 数据查询接口"},
        {"router": llm_router, "prefix": "", "tags": ["AI"], "description": "AI对话接口"},
    ]


def get_routers():
    """获取所有路由（向后兼容，返回元组）"""
    from .llm.routes import router as llm_router
    from .news.routes import router as news_router
    from .stock.routes import router as stock_router
    return (llm_router, news_router, stock_router)


__all__ = [
    "configure_routes",
    "get_all_routers",
    "get_routers",
]