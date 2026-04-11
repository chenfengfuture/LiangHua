"""
utils/ — 量华平台核心高性能工具包

    from utils import get_conn, call_llm, run_collect, get_mootdx_client
"""

# 数据库
from utils.db import get_conn, get_cursor, get_pool, batch_insert, table_exists, warmup as db_warmup

# LLM
from utils.llm import call_llm, stream_llm, call_llm_with_history, AVAILABLE_MODELS, warmup as llm_warmup

# 采集器
from utils.collector import (
    get_mootdx_client,
    get_thread_client,
    is_trading_day,
    fetch_one_kline,
    batch_upsert_klines,
    run_collect,
    warmup as collector_warmup,
)

# WebSocket
from utils.websocket_manager import ws_manager
from utils.websocket_utils import ws_send_news_update, ws_send_collect_status

# Redis（新闻采集状态缓存）
from utils.redis_client import (
    redis_get, redis_set, redis_exists, redis_expire,
    close_redis, init_news_keys,
    get_last_collect_time, set_last_collect_time,
    seconds_since_last_collect, should_collect,
    is_cctv_today_done, set_cctv_today_done, reset_cctv_today_done,
    get_all_collect_status,
)
