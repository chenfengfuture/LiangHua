"""
config/ — 量华平台配置中心

所有配置统一在此管理，各模块通过 from config import ... 引用。
私密配置（密码、API Key）从 config/.env 加载。
"""

from config.settings import *  # noqa: F401,F403
from config.settings import (  # 服务配置; 数据库; 新闻数据库; 大模型; 采集器; Redis
    ARK_API_KEY,
    ARK_BASE_URL,
    AVAILABLE_LLM_MODELS,
    COLLECT_BARS,
    COLLECT_BATCH,
    COLLECT_RETRY,
    COLLECT_RETRY_SLEEP,
    COLLECT_SCHEDULE,
    COLLECT_WORKERS,
    CORS_ORIGINS,
    DB_CHARSET,
    DB_CONFIG,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_POOL_CONFIG,
    DB_POOL_CONFIG_COLLECTOR,
    DB_PORT,
    DB_USER,
    DEFAULT_LLM_MODEL,
    NEWS_DB_CHARSET,
    NEWS_DB_CONFIG,
    NEWS_DB_HOST,
    NEWS_DB_NAME,
    NEWS_DB_PASSWORD,
    NEWS_DB_POOL_CONFIG,
    NEWS_DB_PORT,
    NEWS_DB_USER,
    REDIS_DB,
    REDIS_DECODE,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    SERVER_HOST,
    SERVER_PORT,
)
