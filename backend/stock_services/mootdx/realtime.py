#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mootdx 实时行情服务 — 不入库，仅写入 Redis Hash（TTL 30分钟，覆盖更新）

设计要点：
  · 复用 MootdxKlineService 的线程本地 mootdx 连接池
  · 单 Redis Hash Key `realtime:quotes`，field=symbol，value=JSON
  · 每次写入刷新 TTL，盘中持续活跃，盘后自动过期
  · 支持批量符号查询，前端一次传多股
"""

import json
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_service import MootdxBaseService
from system_service.service_result import  *
from stock_services.common.logging import get_module_logger

log = get_module_logger("MootdxRealtimeService")

# Redis Key 设计
REALTIME_REDIS_KEY = "realtime:quotes"
REALTIME_TTL = 60*600  # 30 分钟

# mootdx quotes() 返回字段 → 输出字段映射
# 注意：原始数据不含 name/change_percent，需从其他字段计算
_QUOTE_FIELDS = {
    "code": "symbol",
    "price": "price",
    "last_close": "last_close",
    "open": "open",
    "high": "high",
    "low": "low",
    "volume": "volume",
    "amount": "amount",
    "vol": "turnover",
    "bid1": "bid1",
    "bid_vol1": "bid1_vol",
    "ask1": "ask1",
    "ask_vol1": "ask1_vol",
    "bid2": "bid2",
    "bid_vol2": "bid2_vol",
    "ask2": "ask2",
    "ask_vol2": "ask2_vol",
    "bid3": "bid3",
    "bid_vol3": "bid3_vol",
    "ask3": "ask3",
    "ask_vol3": "ask3_vol",
    "bid4": "bid4",
    "bid_vol4": "bid4_vol",
    "ask4": "ask4",
    "ask_vol4": "ask4_vol",
    "bid5": "bid5",
    "bid_vol5": "bid5_vol",
    "ask5": "ask5",
    "ask_vol5": "ask5_vol",
}


class MootdxRealtimeService(MootdxBaseService):
    """Mootdx 实时行情服务（Redis Hash 缓存，不入库），继承 MootdxBaseService"""
    LOGGER_NAME = "MootdxRealtimeService"

    def __init__(self):
        super().__init__(service_name="MootdxRealtimeService")
        # mootdx 客户端由基类 MootdxBaseService._get_mootdx_client() 提供

    # ─────────────────────────────────────────────────────────────
    #  核心：从 mootdx 拉取实时行情
    # ─────────────────────────────────────────────────────────────

    def fetch_realtime(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        从 mootdx 拉取实时行情数据（批量查询）。

        Args:
            symbols: 股票代码列表，如 ["000001", "600519"]

        Returns:
            记录列表，空列表表示失败或无数据
        """
        if not symbols:
            return []

        client = self._get_mootdx_client()
        if client is None:
            log.warning("[realtime] mootdx 客户端不可用")
            return []

        try:
            import pandas as pd
            df = client.quotes(symbol=symbols)
            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                log.warning(f"[realtime] mootdx 返回为空: symbols={symbols}")
                return []

            records = []
            now_str = datetime.now().strftime("%H:%M:%S")
            for _, row in df.iterrows():
                rec = self._build_record(row, now_str)
                if rec:
                    records.append(rec)

            log.info(f"[realtime] mootdx 拉取完成: symbols={len(symbols)} "
                     f"got={len(records)}")
            return records

        except Exception as e:
            log.error(f"[realtime] mootdx 拉取异常: {e}")
            return []

    def _build_record(self, row: Any, now_str: str) -> Optional[Dict[str, Any]]:
        """将 mootdx DataFrame 的行转换为标准 dict"""
        try:
            code = str(row.get("code", "")).strip()
            if not code:
                return None

            rec: Dict[str, Any] = {
                "symbol": code,
                "update_time": now_str,
            }
            # 遍历字段映射，逐字段转换
            for src_field, dst_field in _QUOTE_FIELDS.items():
                if dst_field == "symbol":
                    continue  # 已处理
                val = row.get(src_field)
                if val is not None:
                    try:
                        if src_field.startswith("bid_vol") or src_field.startswith("ask_vol") \
                                or src_field in ("volume", "vol"):
                            rec[dst_field] = int(val)
                        else:
                            rec[dst_field] = round(float(val), 2)
                    except (ValueError, TypeError):
                        rec[dst_field] = None
                else:
                    rec[dst_field] = None

            # 计算衍生字段
            price = rec.get("price")
            last_close = rec.get("last_close")
            if price is not None and last_close is not None and last_close != 0:
                rec["change"] = round(price - last_close, 2)
                rec["change_percent"] = round((price - last_close) / last_close * 100, 2)

            return rec
        except Exception as e:
            log.debug(f"[realtime] _build_record 异常: {e}")
            return None

    # ─────────────────────────────────────────────────────────────
    #  Redis 缓存读写
    # ─────────────────────────────────────────────────────────────

    def _write_redis(self, records: List[Dict[str, Any]]) -> int:
        """
        写入 Redis Hash（覆盖更新 + 刷新 TTL）。

        Args:
            records: 行情记录列表

        Returns:
            成功写入条数
        """
        if not records:
            return 0

        r = self._get_client()
        if r is None:
            return 0

        ok = 0
        try:
            pipe = r.pipeline(transaction=False)
            for rec in records:
                sym = rec.get("symbol", "")
                if not sym:
                    continue
                val = json.dumps(rec, ensure_ascii=False, default=str)
                pipe.hset(REALTIME_REDIS_KEY, sym, val)
                ok += 1
            pipe.expire(REALTIME_REDIS_KEY, REALTIME_TTL)
            pipe.execute()
            log.info(f"[realtime] Redis 写入完成: {ok}/{len(records)} 条, "
                     f"TTL={REALTIME_TTL}s")
        except Exception as e:
            log.error(f"[realtime] Redis 写入异常: {e}")

        return ok

    def _read_redis(self, symbols: List[str]) -> Dict[str, Optional[Dict]]:
        """
        从 Redis Hash 批量读取行情数据。

        Returns:
            {symbol: record_dict | None, ...}
            None 表示该股在 Redis 中不存在
        """
        if not symbols:
            return {}

        r = self._get_client()
        if r is None:
            return {s: None for s in symbols}

        try:
            raw_values = r.hmget(REALTIME_REDIS_KEY, symbols)
            result: Dict[str, Optional[Dict]] = {}
            for i, sym in enumerate(symbols):
                raw = raw_values[i] if i < len(raw_values) else None
                if raw:
                    try:
                        val_str = raw.decode() if isinstance(raw, bytes) else raw
                        result[sym] = json.loads(val_str)
                    except Exception:
                        result[sym] = None
                else:
                    result[sym] = None
            return result
        except Exception as e:
            log.warning(f"[realtime] Redis 读取异常: {e}")
            return {s: None for s in symbols}

    # ─────────────────────────────────────────────────────────────
    #  统一入口
    # ─────────────────────────────────────────────────────────────

    def get_realtime(self, symbols: List[str],
                     force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取实时行情（Redis 缓存优先 → mootdx 兜底）。

        Args:
            symbols:       股票代码列表
            force_refresh: 强制从 mootdx 拉取，跳过 Redis

        Returns:
            {
                "success": True,
                "data": {symbol: record_dict, ...},
                "source": "redis|mootdx",
                "update_time": "14:30:25",
            }
        """
        t0 = time.time()
        symbols = [str(s).strip() for s in symbols if s and str(s).strip()]
        if not symbols:
            return error_result("symbols 不可为空")

        # 清理重复符号
        seen = set()
        unique_syms = []
        for s in symbols:
            if s not in seen:
                seen.add(s)
                unique_syms.append(s)
        symbols = unique_syms

        result: Dict[str, Any] = {}
        source = "redis"

        if not force_refresh:
            # 1. 查 Redis 缓存
            cached = self._read_redis(symbols)
            missing = [s for s, v in cached.items() if v is None]
            for s, v in cached.items():
                if v is not None:
                    result[s] = v

            if not missing:
                # 全部命中缓存
                elapsed = round(time.time() - t0, 3)
                log.info(f"[realtime] 全部 Redis 命中: {len(symbols)} 条, "
                         f"elapsed={elapsed}s")
                now_str = datetime.now().strftime("%H:%M:%S")
                return {
                    "success": True,
                    "data": result,
                    "source": source,
                    "update_time": now_str,
                    "elapsed_s": elapsed,
                }
        else:
            missing = symbols[:]

        # 2. 缺失或强制刷新 → mootdx 拉取
        mootdx_records = self.fetch_realtime(missing)
        if mootdx_records:
            self._write_redis(mootdx_records)
            for rec in mootdx_records:
                sym = rec.get("symbol", "")
                if sym:
                    result[sym] = rec
            source = "mootdx"

        elapsed = round(time.time() - t0, 3)
        now_str = datetime.now().strftime("%H:%M:%S")
        log.info(f"[realtime] 完成: symbols={len(symbols)} "
                 f"source={source} elapsed={elapsed}s")

        return {
            "success": True,
            "data": result,
            "source": source,
            "update_time": now_str,
            "elapsed_s": elapsed,
        }


# 模块级单例
mootdx_realtime_service = MootdxRealtimeService()


# ═══════════════════════════════════════════════════════════════════
#  路由入口包装函数
# ═══════════════════════════════════════════════════════════════════

def get_realtime_quotes(symbols: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    路由入口：获取实时行情。

    Args:
        symbols:      逗号分隔的股票代码，如 "000001,600519"
        force_refresh: 强制从 mootdx 拉取

    Returns:
        {success, data: {symbol: record}, source, update_time, elapsed_s}
    """
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not sym_list:
        return error_result("不可为空")
    return mootdx_realtime_service.get_realtime(sym_list, force_refresh=force_refresh)


