"""mootdx K线服务

公开导出：
  · MootdxKlineService           K 线服务类
  · mootdx_kline_service         模块级单例
  · get_kline_data               路由入口（日/周/月线 + 分钟线自动分流）
  · get_mootdx_minute_kline      分钟线专用入口
  · kline_redis_service          K 线 Redis 服务单例
  · KlineRedisService            K 线 Redis 服务类（含 Hash 压缩方法）
  · ensure_kline_year_table      按需懒建分年表
  · ensure_kline_year_tables     批量懒建分年表
  · is_trading_day               交易日判断（排除周末+节假日）
  · get_trading_days             获取日期段内所有交易日列表
  · start_daily_kline_collector  启动自愈型收盘后自动采集后台线程
  · kline_query_layer            三层查询层单例（Redis → DB → mootdx）
  · KlineQueryLayer              三层查询层类
  · kline_ws_collector           WebSocket 流式采集器单例
  · KlineWSCollector             WebSocket 流式采集器类
  · query_kline_with_cache       路由入口（三层缓存查询 + 单/多/全市场分流）
  · trigger_ws_kline_collect     路由入口（WS 全市场采集触发）
  · MootdxRealtimeService        实时行情服务类
  · mootdx_realtime_service      实时行情服务单例
  · get_realtime_quotes          路由入口（Redis 缓存 + mootdx 兜底）
"""

from .service import (
    MootdxKlineService,
    mootdx_kline_service,
    get_kline_data,
    get_mootdx_minute_kline,
    start_daily_kline_collector,
    query_kline_with_cache,
    trigger_ws_kline_collect,
)

from .kline_redis import KlineRedisService, kline_redis_service
from .table_helper import ensure_kline_year_table, ensure_kline_year_tables
from .kline_query import KlineQueryLayer, kline_query_layer
from .kline_ws_collector import KlineWSCollector, kline_ws_collector
from .kline_sse_streamer import KlineSSEStreamer, kline_sse_streamer
from .realtime import MootdxRealtimeService, mootdx_realtime_service, get_realtime_quotes


__all__ = [
    "MootdxKlineService",
    "mootdx_kline_service",
    "get_kline_data",
    "get_mootdx_minute_kline",
    "KlineRedisService",
    "kline_redis_service",
    "ensure_kline_year_table",
    "ensure_kline_year_tables",
    "start_daily_kline_collector",
    "KlineQueryLayer",
    "kline_query_layer",
    "KlineWSCollector",
    "kline_ws_collector",
    "query_kline_with_cache",
    "trigger_ws_kline_collect",
    "KlineSSEStreamer",
    "kline_sse_streamer",
    "MootdxRealtimeService",
    "mootdx_realtime_service",
    "get_realtime_quotes",
]
