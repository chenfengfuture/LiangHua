#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K 线 WebSocket 流式采集器

功能：
  · 接收前端 WS 消息 → 启动后台采集线程
  · 全市场扫描时每批返回进度（通过 ws_manager broadcast）
  · 逐步推送结果，不阻塞长 HTTP 连接
  · 采集完自动写 Redis Hash + DB，不影响 REST 查询

前端订阅频道：kline
  ws.send(JSON.stringify({ "action": "subscribe", "channels": ["kline"] }))

前端触发采集：
  ws.send(JSON.stringify({
    "action": "kline_collect",
    "freq": "day",
    "start_date": "20260501",
    "end_date": "20260526"
  }))

WS 消息格式：
  {"type": "kline_progress", "done": 200, "total": 5000,
   "records": 8000, "failed": 3, "elapsed_s": 12.5}
  {"type": "kline_stock_done", "symbol": "000001", "name": "平安银行",
   "records": 20, "stock_idx": 42, "total": 5000}
  {"type": "kline_complete", "total_records": 120000,
   "queued_to_db": 120000, "failed": 10, "elapsed_s": 45.2}
  {"type": "kline_error", "error": "..."}
"""

import threading
import time
from datetime import date, datetime, timedelta
from typing import Optional

from utils.websocket_manager import ws_manager

from .base_service import MootdxBaseService
from .kline_redis import kline_redis_service
from .service import mootdx_kline_service
from .table_helper import get_kline_full_table_name
from stock_services.common.date_utils import get_trading_days
from stock_services.common.logging import get_module_logger

log = get_module_logger("kline_ws_collector")

# 每批推送间隔（股票数）
PROGRESS_BATCH = 200
# WS 广播频道
WS_CHANNEL = "kline"


class KlineWSCollector(MootdxBaseService):
    """
    WebSocket 流式 K 线采集器，继承 MootdxBaseService

    支持全市场和多股采集，通过 ws_manager 逐步推送进度。
    """
    LOGGER_NAME = "kline_ws_collector"

    def __init__(self):
        super().__init__(service_name="KlineWSCollector")
        self._active_tasks = {}  # task_id -> thread

    # ─── 触发采集 ──────────────────────────────────────────────────

    def start_collect(self, params: dict) -> str:
        """
        启动后台采集任务（非阻塞）。

        Args:
            params: {
                "symbol": None (全市场) / "000001" (单股) / "000001,600519" (多股),
                "freq": "day",
                "start_date": "20260501",
                "end_date": "20260526",
            }

        Returns:
            task_id: 任务标识
        """
        task_id = f"kline_{int(time.time() * 1000)}"
        t = threading.Thread(
            target=self._run_collect,
            args=(task_id, params),
            daemon=True,
            name=f"kline-ws-{task_id}",
        )
        t.start()
        self._active_tasks[task_id] = t
        log.info(f"[kline-ws] 采集任务已启动: task_id={task_id} params={params}")
        return task_id

    # ─── 后台采集逻辑 ──────────────────────────────────────────────

    def _run_collect(self, task_id: str, params: dict):
        """后台线程：全市场/多股 K 线采集 + 逐步推送"""
        t0 = time.time()
        freq = params.get("freq", "day")
        start_str = params.get("start_date")
        end_str = params.get("end_date")
        symbol_param = params.get("symbol")  # None=全市场

        start_d = self._parse_date(start_str, 30)
        end_d = self._parse_date(end_str, 0)

        # 校验日期范围
        valid_start, valid_end, skipped = mootdx_kline_service._validate_date_range(
            start_d, end_d, freq
        )
        if valid_start is None:
            ws_manager.broadcast_sync(WS_CHANNEL, {
                "type": "kline_error",
                "task_id": task_id,
                "error": f"日期范围 {start_d}~{end_d} 内无交易日",
                "skipped": skipped,
            })
            return

        start_d, end_d = valid_start, valid_end

        # 获取 freq_code + offset
        freq_code = mootdx_kline_service.FREQ_MAP.get(freq)
        if freq_code is None:
            ws_manager.broadcast_sync(WS_CHANNEL, {
                "type": "kline_error", "task_id": task_id,
                "error": f"未知频率: {freq}",
            })
            return

        offset = mootdx_kline_service._calc_offset(start_d, end_d, freq_code)

        # ── 加载股票列表 ──────────────────────────────────────
        if symbol_param is None:
            # 全市场
            stocks = mootdx_kline_service._load_active_stocks()
            # 预检已有数据的股票（方案B）
            existing_set = mootdx_kline_service._load_existing_complete_stocks(
                start_d, end_d, freq
            )
            stocks_to_fetch = [(s, n) for s, n in stocks if s not in existing_set]
            skip_count = len(existing_set)
        else:
            # 单股 / 多股
            if isinstance(symbol_param, str) and "," in symbol_param:
                syms = [s.strip() for s in symbol_param.split(",") if s.strip()]
            else:
                syms = [str(symbol_param).strip()]

            stocks_to_fetch = []
            for sym in syms:
                name = mootdx_kline_service._get_stock_name(sym)
                stocks_to_fetch.append((sym, name))
            skip_count = 0

        total_fetch = len(stocks_to_fetch)
        if not stocks_to_fetch:
            ws_manager.broadcast_sync(WS_CHANNEL, {
                "type": "kline_complete",
                "task_id": task_id,
                "total_records": 0,
                "queued_to_db": 0,
                "failed": 0,
                "skipped": skip_count,
                "elapsed_s": round(time.time() - t0, 2),
                "message": "所有股票已有完整数据，无需采集",
            })
            return

        # 推送初始进度
        ws_manager.broadcast_sync(WS_CHANNEL, {
            "type": "kline_progress",
            "task_id": task_id,
            "done": 0,
            "total": total_fetch,
            "records": 0,
            "failed": 0,
            "skip_existing": skip_count,
            "elapsed_s": 0,
        })

        # ── 逐批采集 ──────────────────────────────────────────
        all_records = []
        failed_list = []
        lock = threading.Lock()
        done_count = 0
        last_progress = 0

        for idx, (sym, name) in enumerate(stocks_to_fetch):
            df = mootdx_kline_service._fetch_one_raw(sym, freq_code, offset)
            if df is None:
                with lock:
                    failed_list.append(sym)
                    done_count += 1
                continue

            recs = mootdx_kline_service._df_to_records(df, sym, name, start_d, end_d)

            with lock:
                all_records.extend(recs)
                done_count += 1

            # 每只股票推送一次进度
            if done_count - last_progress >= PROGRESS_BATCH or done_count >= total_fetch:
                last_progress = done_count
                elapsed = time.time() - t0
                # 先把已收集的数据写入 Redis + DB
                batch_records = []
                with lock:
                    batch_records = list(all_records)
                    all_records = []

                if batch_records:
                    self._persist_batch(batch_records, freq, start_d, end_d)

                ws_manager.broadcast_sync(WS_CHANNEL, {
                    "type": "kline_progress",
                    "task_id": task_id,
                    "done": done_count,
                    "total": total_fetch,
                    "records": len(batch_records),
                    "failed": len(failed_list),
                    "skip_existing": skip_count,
                    "elapsed_s": round(elapsed, 2),
                })
                log.info(
                    f"[kline-ws] 进度 {task_id}: {done_count}/{total_fetch} "
                    f"batch_records={len(batch_records)} failed={len(failed_list)} "
                    f"elapsed={elapsed:.1f}s"
                )

        # 处理最后一批（如有残留）
        if all_records:
            self._persist_batch(all_records, freq, start_d, end_d)

        elapsed = time.time() - t0

        # 推送完成消息
        ws_manager.broadcast_sync(WS_CHANNEL, {
            "type": "kline_complete",
            "task_id": task_id,
            "total_fetch": total_fetch,
            "failed": len(failed_list),
            "failed_list": failed_list[:20],
            "skip_existing": skip_count,
            "elapsed_s": round(elapsed, 2),
            "message": f"采集完成: 共 {total_fetch} 只, 失败 {len(failed_list)} 只, "
                       f"耗时 {elapsed:.1f}s",
        })

        log.info(
            f"[kline-ws] 采集完成 {task_id}: "
            f"fetched={total_fetch} failed={len(failed_list)} "
            f"skip={skip_count} elapsed={elapsed:.1f}s"
        )

        # 清理
        self._active_tasks.pop(task_id, None)

    # ─── 批次持久化 ────────────────────────────────────────────────

    @staticmethod
    def _persist_batch(records: list, freq: str, start_d: date, end_d: date):
        """批量写入 Redis Hash + DB"""
        if not records:
            return

        # 写 Redis Hash
        try:
            kline_redis_service.kline_hset_batch(records, freq)
        except Exception as e:
            log.warning(f"[kline-ws] Redis Hash 写入失败: {e}")

        # 写 DB
        try:
            mootdx_kline_service._async_persist_kline(records, freq)
        except Exception as e:
            log.warning(f"[kline-ws] DB 写入失败: {e}")

        # 标记完整性（每只股票每年）
        years = set()
        stocks_with_years = {}
        for r in records:
            sym = r.get("symbol", "")
            yr = r.get("year")
            if sym and yr:
                key = (sym, int(yr))
                stocks_with_years[key] = stocks_with_years.get(key, 0) + 1

        for (sym, yr), count in stocks_with_years.items():
            try:
                yr_result = get_trading_days(
                    date(yr, 1, 1), date(yr, 12, 31)
                )
                yr_days = yr_result.get('data', {}).get('trading_day', [])
                if count >= len(yr_days):
                    kline_redis_service.kline_hset_complete(sym, freq, yr, len(yr_days))
            except Exception:
                pass

    # ─── 日期工具 ──────────────────────────────────────────────────
    # 继承自 MootdxBaseService._parse_date()


# 模块级单例
kline_ws_collector = KlineWSCollector()