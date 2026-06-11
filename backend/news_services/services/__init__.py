"""
news_services/services/ — 服务编排层

导出六个核心服务单例：
  - news_collect_service         采集服务（含 APScheduler）
  - news_llm_service             LLM 分析服务
  - news_finbert_service         FinBERT 金融情感分析服务（LLM 之后、persist 之前）
  - news_finbert_manual_service  手动批量 FinBERT 分析服务（不入队列，同步执行）
  - news_persist_service         持久化服务
  - news_fetch_service           数据查询服务（Redis + MySQL）
"""

from .news_collect_service import news_collect_service
from .news_llm_service import news_llm_service
from .news_finbert_service import news_finbert_service
from .news_finbert_manual_service import news_finbert_manual_service
from .news_persist_service import news_persist_service
from .news_fetch_service import news_fetch_service

__all__ = [
    "news_collect_service",
    "news_llm_service",
    "news_finbert_service",
    "news_finbert_manual_service",
    "news_persist_service",
    "news_fetch_service",
]
