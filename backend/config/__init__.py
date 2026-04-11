"""
config/ — 量华平台配置中心

所有配置统一在此管理，各模块通过 from config import ... 引用。
私密配置（密码、API Key）从 config/.env 加载。
"""

from config.settings import *  # noqa: F401,F403
from config.settings import (
    # 服务配置
    SERVER_HOST,
    SERVER_PORT,
    CORS_ORIGINS,
    # 数据库
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
    DB_CHARSET,
    DB_CONFIG,
    DB_POOL_CONFIG,
    DB_POOL_CONFIG_COLLECTOR,
    # 新闻数据库
    NEWS_DB_HOST,
    NEWS_DB_PORT,
    NEWS_DB_USER,
    NEWS_DB_PASSWORD,
    NEWS_DB_NAME,
    NEWS_DB_CHARSET,
    NEWS_DB_CONFIG,
    NEWS_DB_POOL_CONFIG,
    # 大模型
    ARK_API_KEY,
    ARK_BASE_URL,
    DEFAULT_LLM_MODEL,
    AVAILABLE_LLM_MODELS,
    # 采集器
    COLLECT_WORKERS,
    COLLECT_BATCH,
    COLLECT_BARS,
    COLLECT_RETRY,
    COLLECT_RETRY_SLEEP,
    COLLECT_SCHEDULE,
    # Redis
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PASSWORD,
    REDIS_DB,
    REDIS_DECODE,
)
