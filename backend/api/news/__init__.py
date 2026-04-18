"""
================================================================================
api/news/__init__.py — 新闻模块公开接口导出
================================================================================

【模块结构】
  routes.py            → 新闻采集调度接口（调度器控制、手动采集、Redis管理）
  fetch_routes.py      → 新闻数据查询接口（按日期自动选择 Redis/MySQL 数据源）
  news_llm_analyzer.py → 8线程并行 LLM 分析引擎（常驻后台，消费 Redis 队列）
  news_persist.py      → 持久化层（单线程定时，批量写 MySQL）
  llm_analyzer.py      → 单条/批量分析工具函数（备用，调试用途）

【在 main.py 中的使用方式】
  from api.news.routes       import router as news_router
  from api.news.fetch_routes import router as news_fetch_router
  from api.news.routes       import start_scheduler, stop_scheduler

【架构总览（三层 Redis 管道）】
  采集层（APScheduler, 1分钟）
    → news:data:{id} (Redis String)
    → news:pending_llm (Redis Set)

  LLM 分析层（8线程, news_llm_analyzer.py）
    → 消费 pending_llm
    → 写回 news:data:{id}
    → news:pending_persist (Redis List)

  持久化层（1线程, news_persist.py）
    → 消费 pending_persist
    → CASE 批量更新 MySQL 分表
================================================================================
"""

# LLM 分析引擎单例（供外部状态查询）
from .news_llm_analyzer import get_news_analyzer

# 持久化层单例（供外部状态查询）
from .news_persist import get_persist_worker

# 后台任务控制（被 main.py lifespan 调用）
# 路由对象（被 main.py 注册到 FastAPI app）
from .routes import router, start_scheduler, stop_scheduler

__all__ = [
    "router",
    "start_scheduler",
    "stop_scheduler",
    "get_news_analyzer",
    "get_persist_worker",
]
