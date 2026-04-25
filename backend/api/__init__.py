#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API模块统一入口 - 重构版本

将三大模块（股票、新闻、LLM）作为独立子包，统一组装路由。
每个模块内部维护自己的路由和依赖，通过依赖注入解耦。

重构原则：
1. 模块独立性：每个模块是独立的子包，有自己的路由、依赖和服务
2. 依赖注入：通过FastAPI的Depends()传递服务实例
3. 绝对导入：所有导入以backend为根
4. 禁止循环导入：使用TYPE_CHECKING和延迟导入
"""

from typing import TYPE_CHECKING

# 使用TYPE_CHECKING避免循环导入
if TYPE_CHECKING:
    from fastapi import APIRouter

# 导入路由（使用相对导入）
from .llm.routes import router as llm_router
from .news.routes import router as news_router
from .stock.routes import router as stock_router

# 导入新闻数据查询路由（可选，导入失败时降级不影响主流程）
try:
    from .news.fetch_routes import router as news_fetch_router
    HAS_NEWS_FETCH_ROUTER = True
except ImportError:
    HAS_NEWS_FETCH_ROUTER = False
    news_fetch_router = None

# 导出所有路由
__all__ = [
    # 主路由
    "news_router",
    "stock_router",
    "llm_router",

    # 新闻子路由
    "news_fetch_router",
    
    # 路由配置函数
    "configure_routes",
    "get_all_routers",
]

# 路由配置信息
ROUTER_CONFIGS = [
    {
        "router": stock_router,
        "prefix": "",  # stock_router已经有自己的prefix
        "tags": ["stock"],
        "description": "股票数据接口"
    },
    {
        "router": news_router,
        "prefix": "",  # news_router已经有自己的prefix
        "tags": ["news"],
        "description": "新闻采集管理接口"
    },
    {
        "router": llm_router,
        "prefix": "",  # llm_router已经有自己的prefix
        "tags": ["AI"],
        "description": "AI对话接口"
    }
]


# 如果有新闻采集路由，也添加到配置
if HAS_NEWS_FETCH_ROUTER and news_fetch_router:
    ROUTER_CONFIGS.append({
        "router": news_fetch_router,
        "prefix": "",  # news_fetch_router已经有自己的prefix
        "tags": ["news"],
        "description": "新闻数据查询接口"
    })


def configure_routes(app):
    """
    统一配置所有路由到FastAPI应用
    
    参数：
        app: FastAPI应用实例
    """
    for config in ROUTER_CONFIGS:
        app.include_router(
            config["router"],
            prefix=config.get("prefix", ""),
            tags=config.get("tags", []),
        )
    
    print(f"[api] 已注册 {len(ROUTER_CONFIGS)} 个路由模块")


def get_all_routers():
    """
    获取所有路由配置
    
    返回：
        路由配置列表
    """
    return ROUTER_CONFIGS


# 向后兼容导出（用于需要以元组形式获取路由的旧代码）
def get_routers():
    """
    获取所有路由（向后兼容版本，返回元组）
    
    建议新代码改用 get_all_routers() 或 configure_routes()。
    
    返回：
        (news_router, stock_router, llm_router, news_fetch_router)
    """
    return (news_router, stock_router, llm_router, news_fetch_router if HAS_NEWS_FETCH_ROUTER else None)