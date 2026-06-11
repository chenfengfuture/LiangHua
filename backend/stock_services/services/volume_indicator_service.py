"""
stock_services/services/volume_indicator_service.py — 成交量指标 Service 层

职责：
  - 读取 K 线数据 → 计算成交量指标（VWMA/VR/Volume Bias）
  - 仅 Redis 缓存，不写入 MySQL
  - 提供三个独立接口方法

🔁 缓存 Key 已委派至 common/cache.CacheKeyBuilder：
    CacheKeyBuilder.build(prefix, indicator, symbol, params=params)
    替代自有 _build_cache_key() 实现
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from system_service.redis_service import RedisServiceBase
from stock_services.indicators.volume_indicators import (
    calc_vwma,
    calc_vr,
    calc_volume_bias,
)
from stock_services.mootdx import kline_query_layer
from stock_services.common.cache import CacheKeyBuilder
from stock_services.common.logging import get_module_logger

logger = get_module_logger("VolumeIndicatorService")


class VolumeIndicatorService(RedisServiceBase):
    """
    成交量指标计算服务（仅 Redis 缓存，不落库）。

    缓存 Key 格式：
      volume_indicator:v1:{indicator}:{symbol}:{params_md5}
    TTL: 8 小时
    """

    CACHE_PREFIX = "volume_indicator"  # CacheKeyBuilder 会自动拼接版本号
    CACHE_TTL = 8 * 3600  # 8 小时

    def __init__(self):
        super().__init__(service_name="VolumeIndicatorService")

    # ─────────────────────────────────────────────────────────────
    #  私有工具
    # ─────────────────────────────────────────────────────────────

    def _build_cache_key(self, indicator: str, symbol: str, params: dict) -> str:
        """
        生成 Redis 缓存键（委派至 common/cache.CacheKeyBuilder）。

        向后兼容包装，新代码请直接使用：
            CacheKeyBuilder.build(self.CACHE_PREFIX, indicator, symbol, params=params)
        """
        return CacheKeyBuilder.build(self.CACHE_PREFIX, indicator, symbol, params=params)

    def _redis_get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """尝试从 Redis 读取缓存。"""
        client = self._get_client()
        if client is None:
            return None
        try:
            raw = client.get(cache_key)
            if raw is not None:
                logger.info(f"[volume_indicator] Redis 命中: {cache_key}")
                return json.loads(raw)
        except Exception as e:
            logger.warning(f"[volume_indicator] Redis 读取异常: {e}")
        return None

    def _redis_set(self, cache_key: str, data: Dict[str, Any], ttl: int) -> None:
        """写入 Redis 缓存，失败不阻塞。"""
        client = self._get_client()
        if client is None:
            return
        try:
            client.setex(cache_key, ttl, json.dumps(data, ensure_ascii=False))
            logger.info(f"[volume_indicator] Redis 写入: {cache_key}, TTL={ttl}s")
        except Exception as e:
            logger.warning(f"[volume_indicator] Redis 写入异常: {e}")

    def _load_klines(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        need_extra_days: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        加载 K 线数据，自动向前扩展 need_extra_days 以保证计算窗口完整。

        KlineQueryLayer 自带 Redis → MySQL → mootdx 三层缓存。
        """
        if not start_date:
            start_date = (datetime.now() - timedelta(days=366)).strftime("%Y%m%d")

        # 向前扩展 N 天，确保滑动窗口有足够历史数据
        start_dt = datetime.strptime(start_date, "%Y%m%d")
        extended_start = (start_dt - timedelta(days=need_extra_days + 30)).strftime("%Y%m%d")

        result = kline_query_layer.get_kline_with_cache(
            symbol=symbol,
            freq="day",
            start_date=extended_start,
            end_date=end_date,
            mode="standard",
        )

        if not result.get("success") or not result.get("records"):
            logger.warning(f"[volume_indicator] K 线数据不足: {symbol}")
            return []

        records = result["records"]
        # 确保按日期升序
        records.sort(key=lambda r: str(r.get("datetime", "")))
        # 归一化：将 datetime 字段映射为 trade_date，与 calc_* 函数约定一致
        for r in records:
            dt = r.get("datetime") or r.get("trade_date", "")
            if hasattr(dt, "strftime"):
                r["trade_date"] = dt.strftime("%Y-%m-%d")
            else:
                r["trade_date"] = str(dt)[:10]
        return records

    def _trim_by_date_range(
        self,
        records: List[Dict],
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[Dict]:
        """根据用户请求的日期范围裁剪结果。支持 YYYYMMDD 和 YYYY-MM-DD 格式。"""
        if not start_date and not end_date:
            return records

        def _normalize(d: str) -> str:
            return d[:4] + "-" + d[4:6] + "-" + d[6:8] if len(d) == 8 else d

        sd = _normalize(start_date) if start_date else ""
        ed = _normalize(end_date) if end_date else ""

        result = []
        for r in records:
            trade_date = str(r.get("trade_date", ""))
            if sd and trade_date < sd:
                continue
            if ed and trade_date > ed:
                continue
            result.append(r)
        return result

    # ─────────────────────────────────────────────────────────────
    #  公开接口：VWMA
    # ─────────────────────────────────────────────────────────────

    def get_vwma(
        self,
        symbol: str,
        period: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """查询 VWMA 指标。"""
        # 参数校验
        symbol = str(symbol).strip()
        period = max(5, min(int(period), 120))

        params = {"period": period, "start_date": start_date or "", "end_date": end_date or ""}
        cache_key = self._build_cache_key("vwma", symbol, params)

        # 1. 尝试 Redis 缓存
        cached = self._redis_get(cache_key)
        if cached is not None:
            cached["source"] = "redis"
            return cached

        # 2. 加载 K 线数据（需 extra=period 天窗口）
        klines = self._load_klines(symbol, start_date or "", end_date or "", need_extra_days=period)

        if not klines:
            return {
                "success": True,
                "data": [],
                "message": "K 线数据为空",
                "source": "none",
                "indicator": "vwma",
                "params": params,
            }

        # 3. 计算
        computed = calc_vwma(klines, period=period)

        # 4. 裁剪到用户请求的日期范围
        trimmed = self._trim_by_date_range(computed, start_date, end_date)

        response = {
            "success": True,
            "data": trimmed,
            "source": "computed",
            "indicator": "vwma",
            "params": params,
        }

        # 5. 写入 Redis 缓存（8 小时）
        self._redis_set(cache_key, response, self.CACHE_TTL)

        return response

    # ─────────────────────────────────────────────────────────────
    #  公开接口：VR
    # ─────────────────────────────────────────────────────────────

    def get_vr(
        self,
        symbol: str,
        period: int = 26,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """查询 VR 指标。"""
        symbol = str(symbol).strip()
        period = max(10, min(int(period), 60))

        params = {"period": period, "start_date": start_date or "", "end_date": end_date or ""}
        cache_key = self._build_cache_key("vr", symbol, params)

        cached = self._redis_get(cache_key)
        if cached is not None:
            cached["source"] = "redis"
            return cached

        klines = self._load_klines(symbol, start_date or "", end_date or "", need_extra_days=period)

        if not klines:
            return {
                "success": True,
                "data": [],
                "message": "K 线数据为空",
                "source": "none",
                "indicator": "vr",
                "params": params,
            }

        computed = calc_vr(klines, period=period)
        trimmed = self._trim_by_date_range(computed, start_date, end_date)

        response = {
            "success": True,
            "data": trimmed,
            "source": "computed",
            "indicator": "vr",
            "params": params,
        }

        self._redis_set(cache_key, response, self.CACHE_TTL)
        return response

    # ─────────────────────────────────────────────────────────────
    #  公开接口：Volume Bias
    # ─────────────────────────────────────────────────────────────

    def get_volume_bias(
        self,
        symbol: str,
        periods: Optional[List[int]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """查询 Volume Bias 指标。"""
        symbol = str(symbol).strip()
        if not periods:
            periods = [5, 10, 20]
        periods = [max(2, min(int(p), 120)) for p in periods]

        params = {"periods": periods, "start_date": start_date or "", "end_date": end_date or ""}
        cache_key = self._build_cache_key("volume_bias", symbol, params)

        cached = self._redis_get(cache_key)
        if cached is not None:
            cached["source"] = "redis"
            return cached

        max_p = max(periods)
        klines = self._load_klines(symbol, start_date or "", end_date or "", need_extra_days=max_p)

        if not klines:
            return {
                "success": True,
                "data": [],
                "message": "K 线数据为空",
                "source": "none",
                "indicator": "volume_bias",
                "params": params,
            }

        computed = calc_volume_bias(klines, periods=periods)
        trimmed = self._trim_by_date_range(computed, start_date, end_date)

        response = {
            "success": True,
            "data": trimmed,
            "source": "computed",
            "indicator": "volume_bias",
            "params": params,
        }

        self._redis_set(cache_key, response, self.CACHE_TTL)
        return response


# 全局单例
volume_indicator_service = VolumeIndicatorService()