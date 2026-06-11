#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K 线 Redis 服务 — 继承 system_service.RedisServiceBase

复用：
  · 连接池单例 (_get_client)
  · JSON 序列化 (_json_get / _json_set)
  · 异常自捕获

Hash 压缩方法（1 Hash key 替代 N 个单 key）：
  · kline_hset_batch       日/周/月线 Hash 批量写入
  · kline_hset_complete    设置 __complete__ 完整性标记
  · kline_hcheck_complete  检查 Hash 数据完整性
  · kline_hget_all         读取某年所有 Hash 数据
  · kline_hget_range       跨年按日期范围读取 Hash 数据
  · minute_hset_batch      分钟线 Hash 批量写入
  · minute_hget_all        读取某月所有分钟 Hash 数据"""

import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_service import MootdxBaseService


# ─── 硬编码常量 ───────────────────────────────────────────────────
# 日/周/月线 Redis TTL（30 天）
KLINE_TTL_SECONDS = 30 * 24 * 3600

# 分钟线 Redis TTL（24 小时，复用基类常量值）
MINUTE_KLINE_TTL_SECONDS = 24 * 3600

# 批量 pipeline 单次大小
PIPELINE_BATCH = 500


class KlineRedisService(MootdxBaseService):
    """
    K 线 Redis 服务（Hash 压缩版）

    Key 命名：
      日/周/月线：kline:data:{freq}:{symbol}:{YYYY}  (field=MMDD)
      分钟线：    kline:minute:{freq}:{symbol}:{YYYYMM} (field=DDHHMM)
    """

    # Key 命名空间
    KLINE_DATA_PREFIX = "kline:data:"
    KLINE_MINUTE_PREFIX = "kline:minute:"

    def __init__(self):
        super().__init__(service_name="KlineRedisService")

    # ══════════════════════════════════════════════════════════════
    #  Hash Key 构建
    # ══════════════════════════════════════════════════════════════

    def _build_hash_key(self, freq: str, symbol: str, year: int) -> str:
        """Hash key：kline:data:{freq}:{symbol}:{YYYY}（1 key/股票/年）"""
        return f"{self.KLINE_DATA_PREFIX}{freq}:{symbol}:{year:04d}"

    def _build_minute_hash_key(self, freq: str, symbol: str, yyyymm: int) -> str:
        """分钟线 Hash key：kline:minute:{freq}:{symbol}:{YYYYMM}（1 key/股票/月）"""
        return f"{self.KLINE_MINUTE_PREFIX}{freq}:{symbol}:{yyyymm:06d}"

    # ══════════════════════════════════════════════════════════════
    #  日/周/月线 Hash 批量写入
    # ══════════════════════════════════════════════════════════════

    def kline_hset_batch(self, records: List[Dict[str, Any]], freq: str) -> int:
        """
        按 (symbol, year) 分组写入 Redis Hash。

        Hash key:   kline:data:{freq}:{symbol}:{YYYY}
        Hash field: {MMDD}（日线）或 {YYYYWww} / {YYYYMM}（周/月线）

        Args:
            records: K 线记录列表
            freq:    day / week / month

        Returns:
            成功写入条数
        """
        if not records:
            return 0

        r = self._get_client()
        if r is None:
            return 0

        # 按 (symbol, year) 分组
        groups = defaultdict(list)
        for rec in records:
            try:
                sym = rec.get("symbol", "")
                year_val = int(rec.get("year", 0))
                month_val = int(rec.get("month", 0))
                day_val = int(rec.get("day", 0))

                if freq == "day":
                    field_key = f"{month_val:02d}{day_val:02d}"
                elif freq == "week":
                    iso_cal = date(year_val, month_val, day_val).isocalendar()
                    field_key = f"{year_val:04d}W{iso_cal[1]:02d}"
                elif freq == "month":
                    field_key = f"{year_val:04d}{month_val:02d}"
                else:
                    field_key = f"{month_val:02d}{day_val:02d}"

                groups[(sym, year_val)].append((field_key, rec))
            except Exception:
                continue

        if not groups:
            return 0

        ok = 0
        try:
            for (sym, year_val), items in groups.items():
                hash_key = self._build_hash_key(freq, sym, year_val)
                pipe = r.pipeline(transaction=False)
                for field_key, rec in items:
                    try:
                        val = json.dumps(rec, ensure_ascii=False, default=str)
                        pipe.hset(hash_key, field_key, val)
                    except Exception:
                        continue
                pipe.expire(hash_key, KLINE_TTL_SECONDS)
                try:
                    pipe.execute()
                    ok += len(items)
                except Exception as e:
                    self.logger.error(f"[kline_redis] Hash 写入失败 {hash_key}: {e}")
        except Exception as e:
            self.logger.error(f"[kline_redis] kline_hset_batch 异常: {e}")

        if ok:
            self.logger.info(
                f"[kline_redis] Hash 写入成功: freq={freq} 写入={ok}/{len(records)} "
                f"groups={len(groups)} TTL={KLINE_TTL_SECONDS}s"
            )
        return ok

    def kline_hset_complete(self, symbol: str, freq: str, year: int, trade_day_count: int):
        """
        标记该股票该年数据已完整采集。

        Hash 中写入 __complete__ 字段记录完整交易日数。
        """
        r = self._get_client()
        if r is None:
            return False
        hash_key = self._build_hash_key(freq, symbol, year)
        try:
            r.hset(hash_key, "__complete__", str(trade_day_count))
            return True
        except Exception as e:
            self.logger.error(f"[kline_redis] __complete__ 设置失败 {hash_key}: {e}")
            return False

    def kline_hcheck_complete(self, symbol: str, freq: str, year: int,
                              expected: int) -> Optional[bool]:
        """
        检查 Redis Hash 中该股票某年数据是否完整。

        Args:
            symbol:   股票代码
            freq:     day / week / month
            year:     年份
            expected: 预期数据条数（交易日数）

        Returns:
            True 完整 / False 不完整 / None 无法判断（Redis 不可用）
        """
        r = self._get_client()
        if r is None:
            return None
        hash_key = self._build_hash_key(freq, symbol, year)
        try:
            # 优先检查 __complete__ 标记
            val = r.hget(hash_key, "__complete__")
            if val is not None:
                stored = int(val)
                return stored >= expected
            # 无标记时检查 HLEN
            hlen = r.hlen(hash_key)
            return hlen >= expected
        except Exception:
            return None

    def kline_hget_all(self, symbol: str, freq: str, year: int) -> List[Dict[str, Any]]:
        """
        读取某股票某年 Redis Hash 中所有 K 线数据。

        Returns:
            按日期排序的 K 线记录列表
        """
        r = self._get_client()
        if r is None:
            return []
        hash_key = self._build_hash_key(freq, symbol, year)
        try:
            data = r.hgetall(hash_key)
            # 过滤元数据字段
            data.pop("__complete__", None)
            result = []
            for field_key, val in data.items():
                try:
                    result.append(json.loads(val))
                except Exception:
                    continue
            result.sort(key=lambda x: (x.get("year", 0), x.get("month", 0),
                                       x.get("day", 0)))
            return result
        except Exception as e:
            self.logger.error(f"[kline_redis] HGETALL 失败 {hash_key}: {e}")
            return []

    def kline_hget_range(self, symbol: str, freq: str,
                         start_d: date, end_d: date) -> List[Dict[str, Any]]:
        """
        跨年份按日期范围读取 Hash 中的 K 线数据。

        自动处理跨年场景（如 2025-12-15 ~ 2026-01-15）。
        """
        years = set()
        cur = start_d
        while cur <= end_d:
            years.add(cur.year)
            cur += timedelta(days=1)

        all_records = []
        for yr in sorted(years):
            records = self.kline_hget_all(symbol, freq, yr)
            # 按日期过滤
            for rec in records:
                try:
                    d = date(int(rec["year"]), int(rec["month"]), int(rec["day"]))
                    if start_d <= d <= end_d:
                        all_records.append(rec)
                except Exception:
                    continue

        return all_records

    # ══════════════════════════════════════════════════════════════
    #  分钟线 Hash 批量写入
    # ══════════════════════════════════════════════════════════════

    def minute_hset_batch(self, records: List[Dict[str, Any]], freq: str,
                          ttl: int = MINUTE_KLINE_TTL_SECONDS) -> int:
        """
        分钟线按月写入 Hash。

        Hash key:   kline:minute:{freq}:{symbol}:{YYYYMM}
        Hash field: {DDHHMM}（如 260930 表示 26日09:30）
        """
        if not records:
            return 0

        r = self._get_client()
        if r is None:
            return 0

        # 按 (symbol, yyyymm) 分组
        groups = defaultdict(list)
        for rec in records:
            try:
                sym = rec.get("symbol", "")
                mo = int(rec.get("month", 0))
                dy = int(rec.get("day", 0))
                hr = int(rec.get("hour", 0))
                mi = int(rec.get("minute", 0))
                yr = int(rec.get("year", 0))
                yyyymm = yr * 100 + mo
                field_key = f"{dy:02d}{hr:02d}{mi:02d}"
                groups[(sym, yyyymm)].append((field_key, rec))
            except Exception:
                continue

        if not groups:
            return 0

        ok = 0
        try:
            for (sym, yyyymm), items in groups.items():
                hash_key = self._build_minute_hash_key(freq, sym, yyyymm)
                pipe = r.pipeline(transaction=False)
                for field_key, rec in items:
                    try:
                        val = json.dumps(rec, ensure_ascii=False, default=str)
                        pipe.hset(hash_key, field_key, val)
                    except Exception:
                        continue
                pipe.expire(hash_key, ttl)
                try:
                    pipe.execute()
                    ok += len(items)
                except Exception as e:
                    self.logger.error(f"[kline_redis] 分钟 Hash 写入失败 {hash_key}: {e}")
        except Exception as e:
            self.logger.error(f"[kline_redis] minute_hset_batch 异常: {e}")

        if ok:
            self.logger.info(
                f"[kline_redis] 分钟 Hash 写入成功: freq={freq} 写入={ok}/{len(records)} "
                f"groups={len(groups)} TTL={ttl}s"
            )
        return ok

    def minute_hget_all(self, symbol: str, freq: str,
                        year: int, month: int) -> List[Dict[str, Any]]:
        """
        读取某股票某月分钟线 Hash 所有数据。
        """
        r = self._get_client()
        if r is None:
            return []
        yyyymm = year * 100 + month
        hash_key = self._build_minute_hash_key(freq, symbol, yyyymm)
        try:
            data = r.hgetall(hash_key)
            result = []
            for field_key, val in data.items():
                try:
                    result.append(json.loads(val))
                except Exception:
                    continue
            result.sort(key=lambda x: (x.get("day", 0), x.get("hour", 0),
                                       x.get("minute", 0)))
            return result
        except Exception as e:
            self.logger.error(f"[kline_redis] 分钟 HGETALL 失败 {hash_key}: {e}")
            return []


# 模块级单例
kline_redis_service = KlineRedisService()