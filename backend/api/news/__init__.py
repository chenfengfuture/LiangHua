"""
api/news/__init__.py — 新闻模块对外接口

精简后只剩两个文件：
  __init__.py    — 本文件，对外导出 router、start_scheduler、stop_scheduler
  routes.py      — 纯路由层，所有业务逻辑在 news_services/ 内

业务实现位置：
  news_services/config.py        — 集中配置（采集频率、线程数、批次大小等）
  news_services/services/        — 四大服务（采集 / LLM / 持久化 / 数据查询）
  news_services/sources/         — 数据源（eastmoney / cls / cctv）
  news_services/utils/           — 清洗、敏感性过滤工具

在 main.py 中的使用方式（保持不变）：
  from api.news.routes import router as news_router
  from api.news.routes import start_scheduler, stop_scheduler
"""

from .routes import router, start_scheduler, stop_scheduler

__all__ = [
    "router",
    "start_scheduler",
    "stop_scheduler",
]
