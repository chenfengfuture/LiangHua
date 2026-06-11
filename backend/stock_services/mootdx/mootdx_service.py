from typing import Dict, Any, List, Optional
from datetime import datetime, time as dt_time
import json

from stock_services.common.date_utils import is_market_closed
from stock_services.mootdx.base_service import MootdxBaseService
from stock_services.services.basic_services import BaseStockService
from stock_services.unity import get_minute_ticks
from stock_services.common.logging import get_module_logger
from stock_services.unity.mootdx.service import get_transaction_service, get_history_transaction_service
from system_service import success_result, error_result, submit_async_upsert, simple_upsert

logger = get_module_logger("mootdx_service")
TRANSACTION_CACHE_TTL = 28800          # 8小时


# ========== 辅助函数（模块级） ==========
def _load_cache(redis_client, cache_key: str) -> Optional[List[dict]]:
    """从 Redis List 读取全量缓存，返回 None 表示异常，空列表表示无数据"""
    try:
        raw = redis_client.lrange(cache_key, 0, -1)
        return [json.loads(x) for x in raw if x] if raw else []
    except Exception as e:
        logger.warning(f"读取缓存失败 {cache_key}: {e}")
        return None

def _save_cache(redis_client, cache_key: str, records: List[dict], ttl: int = TRANSACTION_CACHE_TTL):
    """全量覆写 Redis List，删除旧 key 后重新 rpush，并设置 TTL"""
    try:
        redis_client.delete(cache_key)
        if records:
            serialized = [json.dumps(rec, ensure_ascii=False, default=str) for rec in records]
            redis_client.rpush(cache_key, *serialized)
        redis_client.expire(cache_key, ttl)
    except Exception as e:
        logger.error(f"写入缓存失败 {cache_key}: {e}")

def _build_fingerprint(record: dict) -> str:
    """构建去重指纹：trade_date|time_label|price|volume"""
    return "|".join(str(record.get(f, '')) for f in ["trade_date", "time_label", "price", "volume"])

def _dedup_sort(records: List[dict]) -> List[dict]:
    """基于交易日期+时间+价格+成交量去重，并按时间正序排序"""
    seen = set()
    res = []
    for rec in records:
        fp = _build_fingerprint(rec)
        if fp not in seen:
            seen.add(fp)
            res.append(rec)
    res.sort(key=lambda r: (str(r.get('trade_date', '')), str(r.get('time_label', ''))))
    return res


def _full_fetch(redis_client, cache_key: str, symbol: str, persist: bool, async_write: bool) -> Dict[str, Any]:
    """
    全量分页拉取：从 start=0 开始每次取 1000 条，直到不满页或到达收盘时间。
    去重排序后写入 Redis，可选持久化到 MySQL。
    """
    all_data = []
    start_idx = 0
    page_size = 1000
    while True:
        res = get_transaction_service({"symbol": symbol, "start": start_idx, "offset": page_size})
        if not res.get("success"):
            break
        batch = res.get("data", [])
        if not batch:
            break
        all_data.extend(batch)
        if len(batch) < page_size or is_market_closed():
            break
        start_idx += page_size

    if not all_data:
        _save_cache(redis_client, cache_key, [], ttl=60)
        return success_result(data=[], message="当前无逐笔数据")

    unique = _dedup_sort(all_data)
    _save_cache(redis_client, cache_key, unique)
    if persist:
        _do_persist(unique, async_write)
    return success_result(data=unique, message="数据获取成功")

def _incr_fetch(redis_client, cache_key: str, symbol: str, cached: List[dict],
                persist: bool, async_write: bool) -> Dict[str, Any]:
    """
    增量拉取：从现有缓存长度（即已拉取数量）作为 start 继续分页。
    合并新旧数据后去重排序，覆写缓存。
    """
    new_data = []
    start_idx = len(cached)
    page_size = 1000
    while True:
        res = get_transaction_service({"symbol": symbol, "start": start_idx, "offset": page_size})
        if not res.get("success"):
            break
        batch = res.get("data", [])
        if not batch:
            break
        new_data.extend(batch)
        if len(batch) < page_size or is_market_closed():
            break
        start_idx += page_size

    if not new_data:
        return success_result(data=cached, message="无新数据")

    merged = cached + new_data
    unique = _dedup_sort(merged)
    _save_cache(redis_client, cache_key, unique)
    if persist:
        _do_persist(new_data, async_write)
    logger.info(f"增量更新完成: 新增={len(new_data)} 总={len(unique)}")
    return success_result(data=unique, message="增量更新成功")

def _fallback_fetch(symbol: str, persist: bool, async_write: bool) -> Dict[str, Any]:
    """Redis 不可用或异常时，直连 mootdx 取最新 1000 条作为兜底"""
    try:
        res = get_transaction_service({"symbol": symbol, "start": 0, "offset": 1000})
        if not res.get("success"):
            return res
        records = res.get("data", [])
        unique = _dedup_sort(records)
        if persist:
            _do_persist(unique, async_write)
        return success_result(data=unique, message="直连mootdx兜底")
    except Exception as e:
        return error_result(message=f"数据获取失败: {e}")

def _do_persist(records: List[dict], async_write: bool = True):
    """异步或同步写入 MySQL，使用 upsert 避免重复"""
    if not records:
        return
    try:
        if async_write:
            submit_async_upsert("stock_transactions", records, ["symbol", "trade_date", "seq"])
        else:
            simple_upsert("stock_transactions", records)
    except Exception as e:
        logger.error(f"MySQL写入异常: {e}")

# ========== 服务类（整洁版） ==========

class MootdxService(BaseStockService):
    def __init__(self, service_name: str = "MinuteTickService"):
        super().__init__(service_name=service_name)

    def get_minute_ticks(self, symbol: str, date: str, async_write: bool = True) -> Dict[str, Any]:
        """获取历史分时 tick 数据（每分钟一条）"""
        year_month = date[:6]
        table_name = f"minute_ticks_{year_month}"
        return self.execute_cached_fetch(
            table_name=table_name,
            params={"symbol": symbol, "date": date},
            fetch_func=get_minute_ticks,
            validate_rules={"symbol": "stock", "date": "date_format"},
            cache_key_type=True,
            async_write=async_write,
            cache_empty=True,
            ttl_redis=self.REDIS_TTL_MINUTE_TICK,
            ttl_db=self.DB_TTL_MINUTE_TICK,
            write_to_db=True,
            dedup_keys=["symbol", "trade_date", "minute_idx"],
        )

    def get_transaction(self, symbol: str, start: int = 0, offset: int = 800,
                        async_write: bool = True, persist: bool = False,
                        read_from_db: bool = False) -> Dict[str, Any]:
        """获取实时逐笔成交数据（分页拉取 + Redis List 缓存）"""
        cache_key = f"transaction:{symbol}"
        r = self._get_client()
        if r is None:
            return _fallback_fetch(symbol, persist, async_write)

        cached = _load_cache(r, cache_key)
        if cached is None:
            return _fallback_fetch(symbol, persist, async_write)

        # 无缓存或已收盘 → 全量拉取
        if not cached or is_market_closed():
            if not cached:
                logger.info(f"[transaction] 缓存为空，全量拉取: {cache_key}")
            else:
                logger.info(f"[transaction] 已收盘，返回完整缓存: {cache_key}, 条数={len(cached)}")
            return success_result(data=cached, message="数据获取成功") if cached else _full_fetch(r, cache_key, symbol, persist, async_write)

        # 未收盘且有缓存 → 增量拉取
        return _incr_fetch(r, cache_key, symbol, cached, persist, async_write)

    def get_history_transaction(self, symbol: str, date: str, start: int = 0, offset: int = 800,
                                async_write: bool = True, persist: bool = True,
                                auto_clean: bool = True, retention_days: int = 1000) -> Dict[str, Any]:
        """
        获取指定日期的历史逐笔成交（全量，后端自动分页合并）。
        前端只需调用一次，后端循环拉取所有分页数据，合并去重后缓存。
        """
        offset = min(int(offset), 1000)  # 单页最大1000
        retention_days = max(1, min(int(retention_days), 3650))
        year_month = date[:6]
        table_name = f"stock_history_transactions_{year_month}"

        # 定义全量拉取的包装函数
        def fetch_all_history(params: Dict[str, Any]) -> Dict[str, Any]:
            """循环调用 get_history_transaction_service 直到拉取全部数据"""
            symbol = params['symbol']
            date = params['date']
            page_size = params.get('offset', 800)
            all_data = []
            current_start = 0
            while True:
                # 调用原始的历史逐笔接口（注意：可能每次只能返回1000条）
                res = get_history_transaction_service({
                    "symbol": symbol,
                    "date": date,
                    "start": current_start,
                    "offset": page_size,
                })
                if not res.get("success"):
                    # 如果某一页失败，返回已获取的部分（或失败）
                    break
                batch = res.get("data", [])
                if not batch:
                    break
                all_data.extend(batch)
                # 不满页说明已取完
                if len(batch) < page_size:
                    break
                current_start += page_size
                if current_start > 100000:
                    logger.warning(f"[history] 循环拉取超过限制，中止: {symbol} {date}")
                    break
            if all_data:
                # 使用 time_label 排序，格式如 "09:30:01.000"
                all_data.sort(key=lambda x: (x.get('trade_date', ''), x.get('time_label', '')))
            return {"success": True, "data": all_data, "message": f"{date}分笔成交数据,拉取成功"}

        # 使用 execute_cached_fetch，但 fetch_func 使用我们自己的包装函数
        return self.execute_cached_fetch(
            table_name=table_name,
            params={
                "symbol": symbol,
                "date": date,
                "start": start,  # 保留但实际内部循环会忽略这个 start
                "offset": offset,
                "auto_clean": auto_clean,
                "retention_days": retention_days,
                "key_type": f"history_transaction_{year_month}",
            },
            fetch_func=fetch_all_history,  # 关键：使用包装函数
            validate_rules={"symbol": "stock", "date": "date_format"},
            async_write=async_write,
            cache_empty=True,
            ttl_redis=self.REDIS_TTL_MINUTE_TICK,
            ttl_db=self.DB_TTL_MINUTE_TICK,
            write_to_db=persist,
            cache_key_exclude_fields=None,
            dedup_keys=["symbol", "trade_date", "seq"],
        )

mootdx_service = MootdxService()