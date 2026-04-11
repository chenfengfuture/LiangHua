"""
api/stock/routes.py — 股市模块全部接口
从 main.py 拆分，完全独立。

新增接口：
  GET /api/stock/{symbol}/eastmoney-info
      东方财富个股信息查询，基于 akshare.stock_individual_info_em 接口
      参数：symbol (股票代码)
      返回：{success, data, error, symbol} JSON 结构
"""

import math
import json
import queue
import re
import threading
import subprocess
import sys
import os
import concurrent.futures
from typing import Optional, List, Dict
from datetime import date, datetime
from collections import defaultdict

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

# ─── 核心工具（全局连接池 / LLM / 采集器）──────────────────────────
from utils.db import get_conn
from utils.collector import get_mootdx_client
from utils.llm import LLM, call_llm, stream_llm, AVAILABLE_MODELS
from .stock_info_service import get_stock_info, get_stock_info_json

router = APIRouter(prefix="/api", tags=["stock"])



# ─── 工具函数 ─────────────────────────────────────────────────────────────────

def _date_str_to_mootdx(date_str: str) -> str:
    """YYYY-MM-DD → YYYYMMDD"""
    return date_str.replace('-', '')

def safe_float(val):
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else round(f, 4)
    except:
        return None


def get_table_names(start_year: int, end_year: int) -> List[str]:
    """根据年份范围返回需要查询的表名列表"""
    return [f"stock_klines_{y}" for y in range(start_year, end_year + 1)]



# ─── A股交易时间序列 ──────────────────────────────────────────────────────────



def _gen_trading_times():
    """生成 A 股完整交易时间序列，共 240 分钟"""
    times = []
    for h in range(9, 12):
        s_min = 31 if h == 9 else 0
        e_min = 30 if h == 11 else 60
        for m in range(s_min, e_min + 1 if h == 11 else e_min):
            times.append(f"{h:02d}:{m:02d}")
    for h in range(13, 16):
        s_min = 1 if h == 13 else 0
        e_min = 0 if h == 15 else 60
        if h == 15:
            times.append("15:00")
            break
        for m in range(s_min, 60):
            times.append(f"{h:02d}:{m:02d}")
    return times[:240]


_TRADING_TIMES = _gen_trading_times()


# ─── 内存缓存：已存在的分笔分表名 ─────────────────────────────────────────────
_known_trans_tables: set = set()
_known_trans_tables_loaded = False


# ─── 异步写入队列（分笔成交数据批量异步写入）───────────────────────────────────
_trans_write_queue = queue.Queue()
_trans_write_thread = None
_trans_write_lock = threading.Lock()


def _trans_write_worker():
    """后台线程：批量异步写入分笔成交数据"""
    while True:
        try:
            batch = []
            start_time = __import__('time').time()
            while len(batch) < 500:
                try:
                    item = _trans_write_queue.get(timeout=0.1)
                    if item is None:
                        return
                    batch.append(item)
                except queue.Empty:
                    if batch and (__import__('time').time() - start_time) > 1:
                        break
                    continue

            if batch:
                by_table = defaultdict(list)
                for item in batch:
                    by_table[(item['symbol'], item['date'])].append(item['records'])

                for (symbol, date), records_list in by_table.items():
                    all_records = []
                    for r in records_list:
                        all_records.extend(r)
                    _db_save_transactions(symbol, date, all_records)

        except Exception as e:
            print(f"[trans_worker] error: {e}")


def _start_trans_worker():
    """启动异步写入线程（懒启动）"""
    global _trans_write_thread
    with _trans_write_lock:
        if _trans_write_thread is None or not _trans_write_thread.is_alive():
            _trans_write_thread = threading.Thread(target=_trans_write_worker, daemon=True)
            _trans_write_thread.start()
            print("[trans_worker] started")


def enqueue_save_transactions(symbol: str, trade_date: str, records: list):
    """将分笔数据加入异步写入队列"""
    if not records:
        return
    _start_trans_worker()
    _trans_write_queue.put({
        'symbol': symbol,
        'date': trade_date,
        'records': records
    })


def _load_known_trans_tables(cur):
    """首次调用时加载所有已存在分表名到内存"""
    global _known_trans_tables_loaded
    if _known_trans_tables_loaded:
        return
    cur.execute(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA='lianghua' AND TABLE_NAME LIKE 'intraday_transactions_%'"
    )
    for row in cur.fetchall():
        _known_trans_tables.add(row["TABLE_NAME"])
    _known_trans_tables_loaded = True


# ─── 分时数据 DB 操作 ─────────────────────────────────────────────────────────

def _db_query_minutes(symbol: str, trade_date: str):
    """Query intraday_minutes cache from DB."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT minute_idx, time_label, price, vol, avg_price "
                "FROM intraday_minutes "
                "WHERE symbol=%s AND trade_date=%s "
                "ORDER BY minute_idx ASC",
                (symbol, trade_date)
            )
            rows = cur.fetchall()
        if not rows:
            return None
        return [
            {
                "time":      r["time_label"],
                "price":     safe_float(r["price"]),
                "vol":       int(r["vol"]),
                "avg_price": safe_float(r["avg_price"]),
            }
            for r in rows
        ]
    finally:
        conn.close()


def _db_save_minutes(symbol: str, trade_date: str, records: list):
    """Bulk-insert intraday_minutes rows, ignore duplicates."""
    if not records:
        return
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            sql = (
                "INSERT IGNORE INTO intraday_minutes "
                "(symbol, trade_date, time_label, minute_idx, price, vol, avg_price) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)"
            )
            data = [
                (symbol, trade_date, r["time"], i, r["price"] or 0, r["vol"] or 0, r["avg_price"] or 0)
                for i, r in enumerate(records)
            ]
            cur.executemany(sql, data)
        conn.commit()
    finally:
        conn.close()


# ─── 分笔数据 DB 操作 ─────────────────────────────────────────────────────────

def _trans_table(trade_date: str) -> str:
    return "intraday_transactions_" + trade_date.replace("-", "")


def _ensure_trans_table(cur, table_name: str):
    """如果分笔分表不存在则自动创建"""
    if table_name in _known_trans_tables:
        return
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS `{table_name}` (
          `id`         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          `symbol`     VARCHAR(10) NOT NULL,
          `trade_time` CHAR(8)     NOT NULL COMMENT '成交时间 HH:MM:SS',
          `seq`        SMALLINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '同秒序号',
          `price`      DECIMAL(10,4) NOT NULL DEFAULT 0,
          `vol`        INT UNSIGNED  NOT NULL DEFAULT 0,
          `side`       CHAR(1)       NOT NULL DEFAULT 'N' COMMENT 'B买入/S卖出/N中性',
          `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
          UNIQUE KEY `uq_sym_time_seq` (`symbol`, `trade_time`, `seq`),
          KEY `idx_sym_time` (`symbol`, `trade_time`)
        ) ENGINE=InnoDB COMMENT='股票日内分笔成交明细缓存（按天分表）'
    """)
    _known_trans_tables.add(table_name)


def _db_query_transactions(symbol: str, trade_date: str, limit: int | None):
    """从按天分表查询分笔缓存，limit=None 表示全部"""
    table = _trans_table(trade_date)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            _load_known_trans_tables(cur)
            if table not in _known_trans_tables:
                return None

            cur.execute(f"SELECT 1 FROM `{table}` WHERE symbol=%s LIMIT 1", (symbol,))
            if not cur.fetchone():
                return None

            if limit is None:
                cur.execute(
                    f"SELECT trade_time, price, vol, side FROM `{table}` WHERE symbol=%s "
                    f"ORDER BY trade_time ASC, seq ASC", (symbol,)
                )
            else:
                cur.execute(
                    f"SELECT trade_time, price, vol, side FROM `{table}` WHERE symbol=%s "
                    f"ORDER BY trade_time DESC, seq DESC LIMIT %s", (symbol, limit)
                )
            rows = cur.fetchall()
        if limit is not None:
            rows.reverse()
        return [
            {"time": r["trade_time"], "price": safe_float(r["price"]), "vol": int(r["vol"]), "side": r["side"]}
            for r in rows
        ]
    finally:
        conn.close()


def _db_save_transactions(symbol: str, trade_date: str, records: list):
    """批量写入分笔成交到按天分表"""
    if not records:
        return
    seq_counter = defaultdict(int)
    table = _trans_table(trade_date)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            _ensure_trans_table(cur, table)
            sql = f"INSERT IGNORE INTO `{table}` (symbol, trade_time, seq, price, vol, side) VALUES (%s, %s, %s, %s, %s, %s)"
            data = []
            for r in records:
                t = r["time"] or "00:00:00"
                seq = seq_counter[t]
                seq_counter[t] += 1
                data.append((symbol, t, seq, r["price"] or 0, r["vol"] or 0, r["side"] or "N"))

            batch_size = 1000
            total_inserted = 0
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                cur.executemany(sql, batch)
                total_inserted += cur.rowcount
        conn.commit()
        print(f"[trans] saved {len(data)} rows (inserted {total_inserted}) → {table}")
    except Exception as e:
        print(f"[trans] save error: {e}")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：股票基础
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/")
def root():
    return {"status": "ok", "message": "量华量化平台 API 运行中"}


@router.get("/stocks/search")
def search_stocks(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    """搜索股票（按代码前缀 / 名称模糊匹配）"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT symbol, name, market, list_date FROM stocks_info "
                "WHERE symbol LIKE %s OR name LIKE %s ORDER BY symbol LIMIT %s",
                (f"{q}%", f"%{q}%", limit)
            )
            rows = cur.fetchall()
        return {"data": rows, "total": len(rows)}
    finally:
        conn.close()


@router.get("/stocks/list")
def list_stocks(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), market: Optional[str] = None):
    """获取股票列表（分页）"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            where = "WHERE market = %s" if market else ""
            params = [market] if market else []
            cur.execute(f"SELECT COUNT(*) AS cnt FROM stocks_info {where}", params)
            total = cur.fetchone()["cnt"]
            offset = (page - 1) * page_size
            cur.execute(
                f"SELECT symbol, name, market, list_date FROM stocks_info {where} ORDER BY symbol LIMIT %s OFFSET %s",
                params + [page_size, offset]
            )
            rows = cur.fetchall()
        return {"data": rows, "total": total, "page": page, "page_size": page_size}
    finally:
        conn.close()


@router.get("/stock/{symbol}/info")
def get_stock_info(symbol: str):
    """获取单只股票基本信息"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol, name, market, list_date FROM stocks_info WHERE symbol = %s", (symbol,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"股票 {symbol} 不存在")

            current_year = date.today().year
            for yr in range(current_year, current_year - 3, -1):
                table = f"stock_klines_{yr}"
                cur.execute(
                    "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='lianghua' AND TABLE_NAME=%s",
                    (table,)
                )
                if not cur.fetchone():
                    continue
                cur.execute(
                    f"SELECT datetime, open, high, low, close, vol, amount FROM `{table}` WHERE symbol=%s ORDER BY datetime DESC LIMIT 2",
                    (symbol,)
                )
                latest = cur.fetchall()
                if latest:
                    break
            else:
                latest = []

        row["list_date"] = str(row["list_date"]) if row["list_date"] else None
        if latest:
            last = latest[0]
            row["last_price"] = safe_float(last["close"])
            row["last_date"] = str(last["datetime"])[:10]
            if len(latest) >= 2:
                prev = safe_float(latest[1]["close"])
                curr = safe_float(last["close"])
                if prev and curr:
                    row["change_pct"] = round((curr - prev) / prev * 100, 2)
                else:
                    row["change_pct"] = None
            else:
                row["change_pct"] = None
        return row
    finally:
        conn.close()


@router.get("/market/overview")
def market_overview():
    """市场概览：最新交易日各市场股票涨跌统计"""
    conn = get_conn()
    try:
        current_year = date.today().year
        table = f"stock_klines_{current_year}"
        with conn.cursor() as cur:
            cur.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='lianghua' AND TABLE_NAME=%s",
                (table,)
            )
            if not cur.fetchone():
                table = f"stock_klines_{current_year - 1}"

            cur.execute(f"SELECT MAX(DATE(datetime)) AS last_dt FROM `{table}`")
            last_dt = cur.fetchone()["last_dt"]
            if not last_dt:
                return {"date": None, "up": 0, "down": 0, "flat": 0}

            cur.execute(
                f"""SELECT k.symbol, k.close,
                       (SELECT close FROM `{table}` WHERE symbol=k.symbol AND DATE(datetime) < %s ORDER BY datetime DESC LIMIT 1) AS prev_close
                    FROM `{table}` k WHERE DATE(k.datetime) = %s""",
                (last_dt, last_dt)
            )
            rows = cur.fetchall()

        up = down = flat = 0
        for r in rows:
            c, p = safe_float(r["close"]), safe_float(r["prev_close"])
            if c is None or p is None or p == 0:
                flat += 1
            elif c > p:
                up += 1
            elif c < p:
                down += 1
            else:
                flat += 1

        return {"date": str(last_dt), "up": up, "down": down, "flat": flat, "total": up + down + flat}
    finally:
        conn.close()


@router.get("/stocks/hot")
def hot_stocks(date_str: Optional[str] = Query(None), limit: int = Query(20, ge=5, le=100)):
    """按成交额排行 Top N（热门股票）"""
    conn = get_conn()
    try:
        current_year = date.today().year
        table = f"stock_klines_{current_year}"
        with conn.cursor() as cur:
            cur.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='lianghua' AND TABLE_NAME=%s",
                (table,)
            )
            if not cur.fetchone():
                table = f"stock_klines_{current_year - 1}"

            if date_str:
                target_date = date_str
            else:
                cur.execute(f"SELECT MAX(DATE(datetime)) AS d FROM `{table}`")
                target_date = str(cur.fetchone()["d"])

            cur.execute(
                f"""SELECT k.symbol, k.name, k.open, k.high, k.low, k.close, k.vol, k.amount,
                       (SELECT close FROM `{table}` WHERE symbol=k.symbol AND DATE(datetime) < %s ORDER BY datetime DESC LIMIT 1) AS prev_close
                    FROM `{table}` k WHERE DATE(k.datetime) = %s ORDER BY k.amount DESC LIMIT %s""",
                (target_date, target_date, limit)
            )
            rows = cur.fetchall()

        result = []
        for r in rows:
            c, p = safe_float(r["close"]), safe_float(r["prev_close"])
            chg = round((c - p) / p * 100, 2) if (c and p and p != 0) else None
            result.append({
                "symbol": r["symbol"], "name": r["name"], "close": c,
                "open": safe_float(r["open"]), "high": safe_float(r["high"]),
                "low": safe_float(r["low"]), "vol": safe_float(r["vol"]),
                "amount": safe_float(r["amount"]), "change_pct": chg,
            })
        return {"date": target_date, "data": result}
    finally:
        conn.close()


@router.get("/stock/{symbol}/eastmoney-info")
def get_stock_eastmoney_info(symbol: str):
    """
    东方财富个股信息查询接口
    
    接口地址：GET /api/stock/{symbol}/eastmoney-info
    接口参数：
        symbol: 股票代码，如 "000001"、"603777"
    返回参数：
        success: bool - 是否成功
        data: dict - 个股信息字典，包含股票简称、最新价、涨跌幅等字段
        error: str | null - 错误信息，成功时为 null
        symbol: str - 查询的股票代码
    
    数据来源：akshare.stock_individual_info_em 东方财富接口
    异常处理：接口异常时返回错误信息，不崩溃、不阻塞主服务
    日志追踪：使用标准日志模块，前缀 [个股信息查询]
    """
    try:
        result = get_stock_info(symbol)
        return result
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"接口内部错误: {str(e)}",
            "symbol": symbol
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：K 线
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/klines/{symbol}")
def get_klines(
    symbol: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=3000),
    adjust: str = Query("none"),
):
    """获取指定股票日K线数据"""
    try:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date(2020, 1, 1)
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")

    tables = get_table_names(s_date.year, e_date.year)
    conn = get_conn()
    rows_all = []
    try:
        with conn.cursor() as cur:
            for table in tables:
                cur.execute(
                    "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='lianghua' AND TABLE_NAME=%s",
                    (table,)
                )
                if not cur.fetchone():
                    continue
                cur.execute(
                    f"SELECT datetime, open, high, low, close, vol, amount FROM `{table}` "
                    f"WHERE symbol = %s AND DATE(datetime) >= %s AND DATE(datetime) <= %s ORDER BY datetime ASC",
                    (symbol, s_date, e_date)
                )
                rows_all.extend(cur.fetchall())
    finally:
        conn.close()

    rows_all.sort(key=lambda r: r["datetime"])
    if len(rows_all) > limit:
        rows_all = rows_all[-limit:]

    candles, volumes = [], []
    prev_close = None

    for r in rows_all:
        ts = r["datetime"]
        time_str = ts.strftime("%Y-%m-%d") if isinstance(ts, datetime) else str(ts)[:10]
        o, h, l, c = safe_float(r["open"]), safe_float(r["high"]), safe_float(r["low"]), safe_float(r["close"])
        v, amt = safe_float(r["vol"]), safe_float(r.get("amount"))
        vol_val = v if v is not None else amt
        if None in (o, h, l, c):
            continue

        candles.append({"time": time_str, "open": o, "high": h, "low": l, "close": c, "vol": vol_val, "amount": amt, "prev_close": prev_close})

        if prev_close is not None:
            color = "#FF0000" if c >= prev_close else "#00B050"
        else:
            color = "#FF0000" if c >= o else "#00B050"
        volumes.append({"time": time_str, "value": vol_val or 0, "color": color})
        prev_close = c

    return {"symbol": symbol, "start_date": str(s_date), "end_date": str(e_date), "count": len(candles), "candles": candles, "volumes": volumes}


@router.get("/klines/{symbol}/ma")
def get_ma(
    symbol: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    periods: str = Query("5,10,20,60,120,250"),
    limit: int = Query(500, ge=1, le=3000),
):
    """获取均线数据（MA5/10/20/60/120/250）"""
    ma_periods = [int(p) for p in periods.split(",") if p.strip().isdigit()]
    max_period = max(ma_periods) if ma_periods else 250

    try:
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()
        s_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date(2015, 1, 1)
    except:
        raise HTTPException(status_code=400, detail="日期格式错误")

    total_limit = limit + max_period + 50
    kline_resp = get_klines(symbol, str(s_date), str(e_date), total_limit)
    candles = kline_resp["candles"]
    closes = [c["close"] for c in candles]
    times = [c["time"] for c in candles]

    result = {}
    for p in ma_periods:
        ma_series = []
        for i in range(len(closes)):
            if i + 1 >= p:
                avg = round(sum(closes[i - p + 1: i + 1]) / p, 4)
                ma_series.append({"time": times[i], "value": avg})
        result[f"MA{p}"] = ma_series
        if len(result[f"MA{p}"]) > limit:
            result[f"MA{p}"] = result[f"MA{p}"][-limit:]

    return {"symbol": symbol, "ma": result}


@router.get("/klines/{symbol}/detail")
def get_kline_detail(symbol: str, date_str: str = Query(...)):
    """获取某只股票指定交易日的详细日线数据"""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误")

    year = target_date.year
    table = f"stock_klines_{year}"

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='lianghua' AND TABLE_NAME=%s",
                (table,)
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail=f"表 {table} 不存在")

            cur.execute(
                f"SELECT datetime, open, high, low, close, vol, amount FROM `{table}` WHERE symbol=%s AND DATE(datetime)=%s LIMIT 1",
                (symbol, target_date)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"未找到 {symbol} 在 {date_str} 的数据")

            cur.execute(
                f"SELECT close FROM `{table}` WHERE symbol=%s AND DATE(datetime) < %s ORDER BY datetime DESC LIMIT 1",
                (symbol, target_date)
            )
            prev_row = cur.fetchone()

            if not prev_row and year > 1990:
                prev_table = f"stock_klines_{year - 1}"
                cur.execute(
                    "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='lianghua' AND TABLE_NAME=%s",
                    (prev_table,)
                )
                if cur.fetchone():
                    cur.execute(f"SELECT close FROM `{prev_table}` WHERE symbol=%s ORDER BY datetime DESC LIMIT 1", (symbol,))
                    prev_row = cur.fetchone()
    finally:
        conn.close()

    o, h, l, c = safe_float(row["open"]), safe_float(row["high"]), safe_float(row["low"]), safe_float(row["close"])
    v, amt = safe_float(row["vol"]), safe_float(row["amount"])
    prev_c = safe_float(prev_row["close"]) if prev_row else None

    change = round(c - prev_c, 4) if (c is not None and prev_c is not None) else None
    change_pct = round((c - prev_c) / prev_c * 100, 2) if (c and prev_c and prev_c != 0) else None
    amplitude = round((h - l) / prev_c * 100, 2) if (h and l and prev_c and prev_c != 0) else None

    return {
        "symbol": symbol, "date": date_str,
        "open": o, "high": h, "low": l, "close": c, "vol": v, "amount": amt,
        "prev_close": prev_c, "change": change, "change_pct": change_pct, "amplitude": amplitude,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：日内行情（分时 / 分笔 / SSE 流式）
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/intraday/{symbol}/minutes")
def get_intraday_minutes(symbol: str, date_str: str = Query(...)):
    """获取指定股票某交易日的分时行情（240分钟）"""
    cached = _db_query_minutes(symbol, date_str)
    if cached:
        return {"symbol": symbol, "date": date_str, "count": len(cached), "data": cached, "source": "cache"}

    client = get_mootdx_client()
    if not client:
        raise HTTPException(status_code=503, detail="行情服务器连接失败，请稍后重试")

    mdx_date = _date_str_to_mootdx(date_str)
    try:
        df = client.minutes(symbol=symbol, date=mdx_date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分时数据失败: {str(e)}")

    if df is None or (hasattr(df, 'empty') and df.empty):
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 在 {date_str} 的分时数据")

    rows = df.to_dict('records')
    result = []
    cum_vol, cum_amt = 0, 0.0
    for i, row in enumerate(rows):
        price = row.get('price', 0)
        vol = row.get('vol', 0) or row.get('volume', 0) or 0
        cum_vol += vol
        cum_amt += price * vol
        avg = round(cum_amt / cum_vol, 4) if cum_vol > 0 else price
        result.append({
            "time": _TRADING_TIMES[i] if i < len(_TRADING_TIMES) else f"{i}",
            "price": safe_float(price), "vol": int(vol), "avg_price": safe_float(avg),
        })

    threading.Thread(target=_db_save_minutes, args=(symbol, date_str, result), daemon=True).start()
    return {"symbol": symbol, "date": date_str, "count": len(result), "data": result, "source": "mootdx"}


@router.get("/intraday/{symbol}/transactions")
def get_intraday_transactions(symbol: str, date_str: str = Query(...), limit: int = Query(2000, ge=0, le=20000)):
    """获取指定股票某交易日的分笔成交记录"""
    cached = _db_query_transactions(symbol, date_str, limit if limit > 0 else None)
    if cached is not None:
        return {"symbol": symbol, "date": date_str, "count": len(cached), "data": cached, "source": "cache"}

    client = get_mootdx_client()
    if not client:
        raise HTTPException(status_code=503, detail="行情服务器连接失败，请稍后重试")

    mdx_date = _date_str_to_mootdx(date_str)
    all_rows, batch, page, max_pages = [], 800, 0, 50
    try:
        while page < max_pages:
            df = client.transactions(symbol=symbol, date=mdx_date, start=page * batch, offset=batch)
            if df is None or (hasattr(df, 'empty') and df.empty) or len(df) == 0:
                break
            all_rows.extend(df.to_dict('records'))
            if len(df) < batch:
                break
            page += 1
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分笔数据失败: {str(e)}")

    if not all_rows:
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 在 {date_str} 的分笔数据")

    all_rows.reverse()
    side_map = {0: 'S', 1: 'B', 2: 'N'}
    full_result = [
        {"time": r.get('time', ''), "price": safe_float(r.get('price', 0)),
         "vol": int(r.get('vol', 0) or r.get('volume', 0) or 0), "side": side_map.get(r.get('buyorsell', 2), 'N')}
        for r in all_rows
    ]

    enqueue_save_transactions(symbol, date_str, full_result)

    result = full_result if limit == 0 else (full_result[-limit:] if len(full_result) > limit else full_result)
    return {"symbol": symbol, "date": date_str, "count": len(result), "total": len(full_result), "data": result, "source": "mootdx"}


@router.get("/intraday/{symbol}/stream")
def get_intraday_stream(symbol: str, date_str: str = Query(...), limit: int = Query(2000, ge=0, le=20000)):
    """SSE 流式接口：分时数据先推，分笔数据后推"""
    t0_total = __import__('time').time()

    def _fetch_minutes():
        t0 = __import__('time').time()
        cached = _db_query_minutes(symbol, date_str)
        if cached:
            return {"data": cached, "source": "cache", "count": len(cached), "_ms": round((__import__('time').time() - t0) * 1000)}
        client = get_mootdx_client()
        if not client:
            return {"error": "行情服务器连接失败", "data": [], "count": 0, "_ms": 0}
        mdx_date = _date_str_to_mootdx(date_str)
        try:
            df = client.minutes(symbol=symbol, date=mdx_date)
        except Exception as e:
            return {"error": str(e), "data": [], "count": 0, "_ms": 0}
        if df is None or (hasattr(df, 'empty') and df.empty):
            return {"error": "无分时数据", "data": [], "count": 0, "_ms": 0}
        rows = df.to_dict('records')
        result = []
        cum_vol, cum_amt = 0, 0.0
        for i, row in enumerate(rows):
            price = row.get('price', 0)
            vol = row.get('vol', 0) or row.get('volume', 0) or 0
            cum_vol += vol; cum_amt += price * vol
            avg = round(cum_amt / cum_vol, 4) if cum_vol > 0 else price
            result.append({"time": _TRADING_TIMES[i] if i < len(_TRADING_TIMES) else str(i), "price": safe_float(price), "vol": int(vol), "avg_price": safe_float(avg)})
        threading.Thread(target=_db_save_minutes, args=(symbol, date_str, result), daemon=True).start()
        return {"data": result, "source": "mootdx", "count": len(result), "_ms": round((__import__('time').time() - t0) * 1000)}

    def _fetch_transactions():
        t0 = __import__('time').time()
        cached = _db_query_transactions(symbol, date_str, limit if limit > 0 else None)
        if cached is not None:
            return {"data": cached, "source": "cache", "count": len(cached), "_ms": round((__import__('time').time() - t0) * 1000)}
        client = get_mootdx_client()
        if not client:
            return {"error": "行情服务器连接失败", "data": [], "count": 0, "_ms": 0}
        mdx_date = _date_str_to_mootdx(date_str)
        all_rows, batch, page, max_pages = [], 800, 0, 50
        try:
            while page < max_pages:
                df = client.transactions(symbol=symbol, date=mdx_date, start=page * batch, offset=batch)
                if df is None or (hasattr(df, 'empty') and df.empty) or len(df) == 0:
                    break
                all_rows.extend(df.to_dict('records'))
                if len(df) < batch:
                    break
                page += 1
        except Exception as e:
            return {"error": str(e), "data": [], "count": 0, "_ms": 0}
        if not all_rows:
            return {"error": "无分笔数据", "data": [], "count": 0, "_ms": 0}
        all_rows.reverse()
        side_map = {0: 'S', 1: 'B', 2: 'N'}
        full_result = [
            {"time": r.get('time', ''), "price": safe_float(r.get('price', 0)),
             "vol": int(r.get('vol', 0) or r.get('volume', 0) or 0), "side": side_map.get(r.get('buyorsell', 2), 'N')}
            for r in all_rows
        ]
        enqueue_save_transactions(symbol, date_str, full_result)
        ret = full_result if limit == 0 else (full_result[-limit:] if len(full_result) > limit else full_result)
        return {"data": ret, "source": "mootdx", "count": len(ret), "total": len(full_result), "_ms": round((__import__('time').time() - t0) * 1000)}

    result_queue = queue.Queue()

    def _run_minutes():
        result_queue.put(("minutes", _fetch_minutes()))

    def _run_transactions():
        result_queue.put(("transactions", _fetch_transactions()))

    t_min = threading.Thread(target=_run_minutes, daemon=True)
    t_tx = threading.Thread(target=_run_transactions, daemon=True)
    t_min.start()
    t_tx.start()

    def _sse_gen():
        received, total = 0, 2
        while received < total:
            event_name, payload = result_queue.get()
            yield f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            received += 1
        elapsed = round((__import__('time').time() - t0_total) * 1000)
        yield f"event: done\ndata: {{\"ms\": {elapsed}}}\n\n"

    return StreamingResponse(_sse_gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/intraday/{symbol}/combined")
def get_intraday_combined(symbol: str, date_str: str = Query(...), limit: int = Query(2000, ge=0, le=20000)):
    """合并接口（保留兼容），新代码请使用 /stream 接口"""
    def fetch_minutes():
        cached = _db_query_minutes(symbol, date_str)
        if cached:
            return {"data": cached, "source": "cache", "count": len(cached)}
        client = get_mootdx_client()
        if not client:
            return {"error": "行情服务器连接失败", "data": [], "count": 0}
        mdx_date = _date_str_to_mootdx(date_str)
        try:
            df = client.minutes(symbol=symbol, date=mdx_date)
        except Exception as e:
            return {"error": str(e), "data": [], "count": 0}
        if df is None or (hasattr(df, 'empty') and df.empty):
            return {"error": "无分时数据", "data": [], "count": 0}
        rows = df.to_dict('records')
        result = []
        cum_vol, cum_amt = 0, 0.0
        for i, row in enumerate(rows):
            price = row.get('price', 0)
            vol = row.get('vol', 0) or row.get('volume', 0) or 0
            cum_vol += vol; cum_amt += price * vol
            avg = round(cum_amt / cum_vol, 4) if cum_vol > 0 else price
            result.append({"time": _TRADING_TIMES[i] if i < len(_TRADING_TIMES) else str(i), "price": safe_float(price), "vol": int(vol), "avg_price": safe_float(avg)})
        threading.Thread(target=_db_save_minutes, args=(symbol, date_str, result), daemon=True).start()
        return {"data": result, "source": "mootdx", "count": len(result)}

    def fetch_transactions():
        cached = _db_query_transactions(symbol, date_str, limit if limit > 0 else None)
        if cached is not None:
            return {"data": cached, "source": "cache", "count": len(cached)}
        client = get_mootdx_client()
        if not client:
            return {"error": "行情服务器连接失败", "data": [], "count": 0}
        mdx_date = _date_str_to_mootdx(date_str)
        all_rows, batch, page, max_pages = [], 800, 0, 50
        try:
            while page < max_pages:
                df = client.transactions(symbol=symbol, date=mdx_date, start=page * batch, offset=batch)
                if df is None or (hasattr(df, 'empty') and df.empty) or len(df) == 0:
                    break
                all_rows.extend(df.to_dict('records'))
                if len(df) < batch:
                    break
                page += 1
        except Exception as e:
            return {"error": str(e), "data": [], "count": 0}
        if not all_rows:
            return {"error": "无分笔数据", "data": [], "count": 0}
        all_rows.reverse()
        side_map = {0: 'S', 1: 'B', 2: 'N'}
        full_result = [
            {"time": r.get('time', ''), "price": safe_float(r.get('price', 0)),
             "vol": int(r.get('vol', 0) or r.get('volume', 0) or 0), "side": side_map.get(r.get('buyorsell', 2), 'N')}
            for r in all_rows
        ]
        enqueue_save_transactions(symbol, date_str, full_result)
        ret = full_result if limit == 0 else (full_result[-limit:] if len(full_result) > limit else full_result)
        return {"data": ret, "source": "mootdx", "count": len(ret), "total": len(full_result)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        min_res = ex.submit(fetch_minutes).result()
        trans_res = ex.submit(fetch_transactions).result()

    return {"symbol": symbol, "date": date_str, "minutes": min_res, "transactions": trans_res}


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：每日收盘采集
# ═══════════════════════════════════════════════════════════════════════════════

_collect_state = {
    "running": False, "date": None, "total": 0, "done": 0, "failed": 0,
    "started_at": None, "finished_at": None, "message": "",
}
_collect_lock = threading.Lock()


def _run_collect_bg(date_str: str | None, symbols: str | None):
    """后台线程：调用 daily_collector.py"""
    global _collect_state
    script = os.path.join(os.path.dirname(__file__), "..", "..", "daily_collector.py")
    cmd = [sys.executable, script, "--now"]
    if date_str:
        cmd += ["--date", date_str]
    if symbols:
        cmd += ["--symbols", symbols]

    with _collect_lock:
        _collect_state.update({
            "running": True, "date": date_str or "today",
            "total": 0, "done": 0, "failed": 0,
            "started_at": datetime.now().strftime("%H:%M:%S"),
            "finished_at": None, "message": "启动中…",
        })

    try:
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", cwd=backend_dir)
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            if line.startswith("[PROGRESS]"):
                m = re.search(r"done=(\d+).*?total=(\d+).*?failed=(\d+)", line)
                if m:
                    with _collect_lock:
                        _collect_state["done"] = int(m.group(1))
                        _collect_state["total"] = int(m.group(2))
                        _collect_state["failed"] = int(m.group(3))
                        _collect_state["message"] = f"已处理 {m.group(1)}/{m.group(2)} 只"
            else:
                with _collect_lock:
                    _collect_state["message"] = line[-120:]
        proc.wait()
    except Exception as e:
        with _collect_lock:
            _collect_state["message"] = f"错误: {e}"
    finally:
        with _collect_lock:
            _collect_state["running"] = False
            _collect_state["finished_at"] = datetime.now().strftime("%H:%M:%S")
            if not _collect_state["message"].startswith("错误"):
                _collect_state["message"] = f"完成 ✓ 成功 {_collect_state['done']-_collect_state['failed']} 只，失败 {_collect_state['failed']} 只"


@router.post("/collect/trigger")
def collect_trigger(date_str: Optional[str] = Query(None), symbols: Optional[str] = Query(None)):
    """手动触发每日收盘数据采集"""
    with _collect_lock:
        if _collect_state["running"]:
            return {"status": "running", "message": "已有采集任务在进行中", "progress": dict(_collect_state)}

    t = threading.Thread(target=_run_collect_bg, args=(date_str, symbols), daemon=True)
    t.start()
    return {"status": "started", "message": "采集任务已启动", "date": date_str or "today", "symbols": symbols or "全市场"}


@router.get("/collect/status")
def collect_status():
    """查询当前采集任务进度"""
    with _collect_lock:
        return dict(_collect_state)


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：压力位 / 支撑位
# ═══════════════════════════════════════════════════════════════════════════════

def _calc_levels(candles: list, n_local: int = 60, n_pivot: int = 1) -> dict:
    """核心计算函数：枢轴点+局部极值+斐波那契+均线压撑"""
    if not candles or len(candles) < 5:
        return {}

    ref = candles[-1]
    h_ref, l_ref, c_ref = ref["high"], ref["low"], ref["close"]

    PP = round((h_ref + l_ref + c_ref) / 3, 4)
    R1, R2, R3 = round(2 * PP - l_ref, 4), round(PP + (h_ref - l_ref), 4), round(PP + 2 * (h_ref - l_ref), 4)
    S1, S2, S3 = round(2 * PP - h_ref, 4), round(PP - (h_ref - l_ref), 4), round(PP - 2 * (h_ref - l_ref), 4)
    pivot = {"PP": PP, "R1": R1, "R2": R2, "R3": R3, "S1": S1, "S2": S2, "S3": S3}

    window = candles[-n_local:]
    recent_high = max(window, key=lambda x: x["high"])
    recent_low = min(window, key=lambda x: x["low"])
    local = {"recent_high": recent_high["high"], "high_date": recent_high["time"], "recent_low": recent_low["low"], "low_date": recent_low["time"]}

    fib_h, fib_l, fib_range = recent_high["high"], recent_low["low"], recent_high["high"] - recent_low["low"]
    fib = {"high": fib_h, "low": fib_l}
    for key, pct in [("f236", 0.236), ("f382", 0.382), ("f500", 0.500), ("f618", 0.618), ("f786", 0.786)]:
        fib[key] = round(fib_h - fib_range * pct, 4) if fib_range > 0 else None

    closes = [c["close"] for c in candles]
    ma_levels = {}
    for p in [5, 10, 20, 60]:
        ma_levels[f"MA{p}"] = round(sum(closes[-p:]) / p, 4) if len(closes) >= p else None

    current = c_ref
    resistance_raw, support_raw = [], []

    def add_level(price, label, method):
        if price is None:
            return
        entry = {"price": round(price, 4), "label": label, "method": method}
        if price > current:
            resistance_raw.append(entry)
        elif price < current:
            support_raw.append(entry)

    for r, l, s in [(R1, "R1", "pivot"), (R2, "R2", "pivot"), (R3, "R3", "pivot"), (S1, "S1", "pivot"), (S2, "S2", "pivot"), (S3, "S3", "pivot")]:
        add_level(r, l, s)
    add_level(local["recent_high"], "近期高点", "local")
    add_level(local["recent_low"], "近期低点", "local")
    for key, label in [("f236", "Fib 23.6%"), ("f382", "Fib 38.2%"), ("f500", "Fib 50.0%"), ("f618", "Fib 61.8%"), ("f786", "Fib 78.6%")]:
        add_level(fib[key], label, "fib")
    for ma_key, val in ma_levels.items():
        add_level(val, ma_key, "ma")

    def dedup(lst, ascending=True):
        lst = sorted(lst, key=lambda x: x["price"], reverse=not ascending)
        result = []
        for item in lst:
            if result and abs(item["price"] - result[-1]["price"]) / (result[-1]["price"] + 1e-9) < 0.003:
                prio = {"local": 4, "ma": 3, "pivot": 2, "fib": 1}
                if prio.get(item["method"], 0) > prio.get(result[-1]["method"], 0):
                    result[-1] = item
            else:
                result.append(item)
        return result

    return {
        "pivot": pivot, "local": local, "fib": fib, "ma_levels": ma_levels, "current": current,
        "summary": {"resistance": dedup(resistance_raw, ascending=True), "support": dedup(support_raw, ascending=False)},
    }


@router.get("/klines/{symbol}/levels")
def get_price_levels(
    symbol: str,
    end_date: Optional[str] = Query(None),
    n_local: int = Query(60, ge=10, le=500),
    n_data: int = Query(120, ge=30, le=600),
):
    """计算股票压力位 / 支撑位"""
    try:
        e_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误")

    total_need = n_data + n_local + 60
    s_date = date(e_date.year - 3, e_date.month, e_date.day) if total_need > 600 else date(e_date.year - 2, 1, 1)

    kline_resp = get_klines(symbol, str(s_date), str(e_date), min(total_need, 3000))
    candles = kline_resp.get("candles", [])
    if len(candles) < 10:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 数据不足，无法计算压力位")

    candles_used = candles[-n_data:] if len(candles) > n_data else candles
    levels = _calc_levels(candles_used, n_local=min(n_local, len(candles_used)))
    if not levels:
        raise HTTPException(status_code=500, detail="压力位计算失败")

    return {"symbol": symbol, "base_date": candles_used[-1]["time"], "n_local": n_local, "n_data": len(candles_used), **levels}


# ═══════════════════════════════════════════════════════════════════════════════
#  路由：火山方舟大模型（接口层，调用 utils/llm_chat.py）
# ═══════════════════════════════════════════════════════════════════════════════

class LlmChatRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    messages: Optional[List[Dict]] = None


@router.post("/llm/chat", response_class=JSONResponse)
async def llm_chat_v2(req: LlmChatRequest):
    """调用火山方舟大模型（非流式）"""
    try:
        result = call_llm(
            prompt=req.prompt, model=req.model, system_prompt=req.system_prompt,
            temperature=req.temperature, max_tokens=req.max_tokens, messages=req.messages,
        )
        return {"ok": True, "content": result, "model": req.model or "default"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm/stream")
async def llm_stream(req: LlmChatRequest):
    """调用火山方舟大模型（SSE 流式）"""
    def generate():
        try:
            for chunk in stream_llm(
                prompt=req.prompt, model=req.model, system_prompt=req.system_prompt,
                temperature=req.temperature, max_tokens=req.max_tokens, messages=req.messages,
            ):
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/llm/models")
async def llm_models():
    """获取可用模型列表"""
    return {"models": AVAILABLE_MODELS}


# ───────────────────────────────────────────────────────────────────
#  全球新闻全量补全接口
# ───────────────────────────────────────────────────────────────────

@router.post("/global-news/repair")
def repair_global_news(
    start_date: str,
    end_date: str = None,
    push_ws: bool = False,
):
    """
    全球新闻全量补全接口 - 使用新版东方财富API补全指定日期范围的全球新闻。

    POST /api/global-news/repair?start_date=2026-04-01&end_date=2026-04-10&push_ws=true

    【接口参数说明】
    - start_date: 开始日期，格式 YYYY-MM-DD（必需）
    - end_date: 结束日期，格式 YYYY-MM-DD（可选，默认与开始日期相同）
    - push_ws: 是否推送WebSocket到前端（可选，默认false，自动补全不推送，手动触发可推送）

    【数据源说明】
    - API地址: https://np-weblist.eastmoney.com/comm/web/getFastNewsList
    - fastColumn=102 代表全球新闻（7*24小时全球财经）
    - 分页机制: 使用 sortEnd 翻页，每页200条，最多25页
    - 采集频率: 每页间隔0.3秒，避免请求过快

    【处理流程】
    1. 分页获取指定日期范围的全球新闻（增量过滤）
    2. 基于内容哈希去重（标题+内容MD5）
    3. 批量写入MySQL（news_global_YYYYMM表）
    4. 写入Redis String（news:data:{id}）
    5. 推入LLM分析队列（news:pending_llm）
    6. 可选推送WebSocket到前端

    【返回参数说明】
    {
        "success": true/false,
        "start_date": "2026-04-01",
        "end_date": "2026-04-10",
        "total_days": 10,           # 补全的日期范围天数
        "total_fetched": 150,       # 从API获取到的新闻条数
        "total_pushed": 145,        # 成功推入系统的条数（去重后）
        "message": "成功补全145条全球新闻",
        "error": null 或错误信息
    }

    【稳定性保证】
    - 所有网络请求完整try-except，不崩溃
    - 空数据直接跳过，不中断采集
    - 时间解析失败跳过单条，继续处理
    - 有效条数为0立即退出循环，防止死循环
    - sortEnd为空立即结束翻页
    - 全页新闻均早于start_time时提前中止
    - 最多25页限制，防止无限循环
    """
    try:
        # 导入全量补全服务
        from utils.full_news_get import repair_global_news_date_range
        
        # 调用全量补全服务
        result = repair_global_news_date_range(
            start_date=start_date,
            end_date=end_date,
            push_to_ws=push_ws,
        )
        
        return result
        
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        return {
            "success": False,
            "start_date": start_date,
            "end_date": end_date or start_date,
            "total_days": 0,
            "total_fetched": 0,
            "total_pushed": 0,
            "message": "全球新闻补全失败",
            "error": error_detail,
        }
