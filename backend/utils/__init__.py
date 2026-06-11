"""
utils/ — 量华平台核心高性能工具包

    from utils import get_conn, call_llm, run_collect, get_mootdx_client
"""

# 采集器
from .collector import (
    batch_upsert_klines,
    fetch_one_kline,
    get_mootdx_client,
    get_thread_client,
    is_trading_day,
    run_collect,
)
from .collector import warmup as collector_warmup

# 数据库
from .db import batch_insert, get_conn, get_cursor, get_pool, table_exists
from .db import warmup as db_warmup

# LLM
from utils.llm import AVAILABLE_MODELS, call_llm, call_llm_with_history, stream_llm
from utils.llm import warmup as llm_warmup

# Redis（新闻采集状态缓存）- 使用兼容层
from utils.redis_client_compat import (
    close_redis,
    get_all_collect_status,
    get_last_collect_time,
    init_news_keys,
    is_cctv_today_done,
    redis_exists,
    redis_expire,
    redis_get,
    redis_set,
    reset_cctv_today_done,
    seconds_since_last_collect,
    set_cctv_today_done,
    set_last_collect_time,
    should_collect,
)

# WebSocket
from utils.websocket_manager import ws_manager
from utils.websocket_utils import ws_send_collect_status, ws_send_news_update
