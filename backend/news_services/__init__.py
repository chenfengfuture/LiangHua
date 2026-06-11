"""
news_services/ — 新闻系统服务包

参考 stock_services/ 的三层架构：
  routes (api/news/) → services (news_services/services/) → sources (news_services/sources/)

对外导出：
  - news_collect_service         采集服务
  - news_llm_service             LLM 分析服务
  - news_finbert_service         FinBERT 金融情感分析服务
  - news_finbert_manual_service  手动批量 FinBERT 分析服务
  - news_persist_service         持久化服务
  - news_fetch_service           数据查询服务（Redis + MySQL）
  - BaseNewsService              基类（如需扩展新服务）
"""

from news_services.services import (
    news_collect_service,
    news_llm_service,
    news_finbert_service,
    news_finbert_manual_service,
    news_persist_service,
    news_fetch_service,
)
from news_services.services.base_news_service import BaseNewsService
from news_services.services.news_finbert_manual_service import (
    start_scheduled_batch,
    stop_scheduled_batch,
)

__all__ = [
    "news_collect_service",
    "news_llm_service",
    "news_finbert_service",
    "news_finbert_manual_service",
    "news_persist_service",
    "news_fetch_service",
    "BaseNewsService",
    "start_scheduled_batch",
    "stop_scheduled_batch",
]
