"""
utils/collector.py — 高性能采集器

封装采集核心能力：
  1. mootdx 行情客户端管理（单例 + 线程本地池）
  2. 交易日判断（chinese_calendar + 降级逻辑）
  3. 批量 UPSERT（VALUES 拼接，1 次 INSERT 600 条）
  4. 高并发拉取（线程池 + 重试）

设计原则：
  - 不含命令行入口和定时调度（那是 daily_collector.py 的事）
  - 纯工具函数，可被 routes.py 和 daily_collector.py 共同调用
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta

# 动态导入config.settings
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    COLLECT_BARS,
    COLLECT_BATCH,
    COLLECT_RETRY,
    COLLECT_RETRY_SLEEP,
    COLLECT_WORKERS,
)
from utils.db import _init_pool, batch_insert, get_conn

log = logging.getLogger("collector")


# ═══════════════════════════════════════════════════════════════════
#  mootdx 行情客户端
# ═══════════════════════════════════════════════════════════════════

# 单例客户端（API 路由使用）
_mootdx_client = None


def get_mootdx_client():
    """懒加载 mootdx StdQuotes 连接（单例，适合 API 请求），失败返回 None"""
    global _mootdx_client
    if _mootdx_client is not None:
        return _mootdx_client
    try:
        from mootdx import config as mdx_config
        from mootdx.quotes import Quotes
        mdx_config.setup()
        hq_list = mdx_config.get('SERVER').get('HQ', [])
        for srv in hq_list[:5]:
            try:
                c = Quotes.factory(market='std', server=(srv[1], srv[2]), timeout=8)
                cnt = c.stock_count(market=1)
                if cnt and cnt > 0:
                    _mootdx_client = c
                    return _mootdx_client
            except Exception:
                continue
    except Exception:
        pass
    return None


# 线程本地客户端池（采集器并发使用，每线程独立连接）
_client_tls = threading.local()


def get_thread_client():
    """每个线程维护自己的 mootdx 连接（适合多线程采集）"""
    if getattr(_client_tls, 'client', None) is None:
        from mootdx import config as mdx_config
        from mootdx.quotes import Quotes
        mdx_config.setup()
        hq_list = mdx_config.get('SERVER').get('HQ', [])
        for srv in hq_list[:5]:
            try:
                c = Quotes.factory(market='std', server=(srv[1], srv[2]), timeout=10)
                cnt = c.stock_count(market=1)
                if cnt and cnt > 0:
                    _client_tls.client = c
                    break
            except Exception:
                continue
    return getattr(_client_tls, 'client', None)


# ═══════════════════════════════════════════════════════════════════
#  交易日判断
# ═══════════════════════════════════════════════════════════════════

def is_trading_day(d: date) -> bool:
    """判断 d 是否为 A 股交易日（排除周末 + 中国法定节假日）"""
    try:
        import chinese_calendar as cc
        return cc.is_workday(d)
    except Exception:
        return d.weekday() < 5


def get_trading_days(year: int) -> list[date]:
    """返回指定年份所有交易日列表"""
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    result = []
    d = start
    while d <= end:
        if is_trading_day(d):
            result.append(d)
        d += timedelta(days=1)
    return result


# ═══════════════════════════════════════════════════════════════════
#  高性能批量 UPSERT
# ═══════════════════════════════════════════════════════════════════

def batch_upsert_klines(records: list[dict], year: int) -> int:
    """
    高性能批量 UPSERT 到 stock_klines_YYYY

    使用 VALUES 拼接，1 次 INSERT 可写入数百条记录。
    ON DUPLICATE KEY UPDATE 保证幂等。

    Args:
        records: [{symbol, name, dt, open, high, low, close, vol, amount, year, month, day}, ...]
        year:    目标分表年份

    Returns:
        成功写入行数
    """
    if not records:
        return 0

    table = f"stock_klines_{year}"

    # VALUES 拼接：(%s,%s,...),(%s,%s,...),...
    # 每组 14 个占位符，按 COLLECT_BATCH 切分
    batch_size = min(COLLECT_BATCH, 600)  # 单次 INSERT 不超过 600 条
    total_written = 0

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]

        # 构建 VALUES 占位符
        placeholders_per_row = "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,15,0)"
        all_placeholders = ",".join([placeholders_per_row] * len(batch))

        sql = f"""
            INSERT INTO `{table}`
                (symbol, name, datetime, open, high, low, close, vol, amount, volume,
                 year, month, day, hour, minute)
            VALUES {all_placeholders}
            ON DUPLICATE KEY UPDATE
                open   = VALUES(open),
                high   = VALUES(high),
                low    = VALUES(low),
                close  = VALUES(close),
                vol    = VALUES(vol),
                amount = VALUES(amount),
                volume = VALUES(volume),
                name   = VALUES(name)
        """

        params = []
        for r in batch:
            params.extend([
                r['symbol'], r['name'],
                datetime(r['year'], r['month'], r['day'], 15, 0, 0),
                r['open'], r['high'], r['low'], r['close'],
                r['vol'], r['amount'], r['vol'],
                r['year'], r['month'], r['day'],
            ])

        # 直接用 get_conn() 执行（不走 batch_insert，因为自定义了 VALUES 拼接）
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                total_written += cur.rowcount
            conn.commit()
        except Exception as e:
            conn.rollback()
            log.error(f'[upsert] 批量写入失败: {e}')
        finally:
            conn.close()

    return total_written


# ═══════════════════════════════════════════════════════════════════
#  单股票拉取
# ═══════════════════════════════════════════════════════════════════

def fetch_one_kline(symbol: str, name: str, target_date: date) -> dict | None:
    """
    拉取单只股票日K（使用线程本地客户端）

    Args:
        symbol:      股票代码
        name:        股票名称
        target_date: 目标日期

    Returns:
        dict 或 None（无数据/异常）
    """
    date_str = target_date.strftime('%Y-%m-%d')
    client = get_thread_client()
    if not client:
        return None

    for attempt in range(COLLECT_RETRY):
        try:
            df = client.bars(symbol=symbol, frequency=9, start=0, offset=COLLECT_BARS)
            if df is None or (hasattr(df, 'empty') and df.empty):
                return None
            for _, row in df.iterrows():
                dt_str = str(row.get('datetime', ''))
                if dt_str.startswith(date_str):
                    return {
                        'symbol': symbol,
                        'name':   name,
                        'dt':     target_date,
                        'open':   float(row['open']),
                        'high':   float(row['high']),
                        'low':    float(row['low']),
                        'close':  float(row['close']),
                        'vol':    float(row.get('vol', 0) or row.get('volume', 0) or 0),
                        'amount': float(row.get('amount', 0) or 0),
                        'year':   target_date.year,
                        'month':  target_date.month,
                        'day':    target_date.day,
                    }
            return None
        except Exception as e:
            if attempt < COLLECT_RETRY - 1:
                time.sleep(COLLECT_RETRY_SLEEP * (attempt + 1))
            else:
                log.warning(f'[fetch] {symbol} 重试 {COLLECT_RETRY} 次仍失败: {e}')
    return None


# ═══════════════════════════════════════════════════════════════════
#  全量采集流程
# ═══════════════════════════════════════════════════════════════════

def run_collect(
    target_date: date | None = None,
    symbols_filter: list[str] | None = None,
) -> dict:
    """
    主采集函数（高性能并发 + 批量写入）

    Args:
        target_date:    采集日期（默认 today）
        symbols_filter: 只采集这些 symbol（默认全量）

    Returns:
        {'date', 'total', 'success', 'written', 'failed', 'elapsed_s', 'failed_list'}
    """
    if target_date is None:
        target_date = date.today()

    # 确保使用采集器模式的连接池
    _init_pool("collector")

    log.info(f"{'='*60}")
    log.info(f"[collect] 开始采集 {target_date}  (weekday={target_date.weekday()})")

    if not is_trading_day(target_date):
        log.info(f"[collect] {target_date} 非交易日，跳过")
        return {'date': str(target_date), 'skipped': True}

    # 加载股票列表
    from utils.db import get_conn
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol, name FROM stocks_info ORDER BY symbol")
            rows = cur.fetchall()
    finally:
        conn.close()

    all_symbols = [(r['symbol'], r['name']) for r in rows]
    if symbols_filter:
        sym_set = set(symbols_filter)
        all_symbols = [(s, n) for s, n in all_symbols if s in sym_set]

    total = len(all_symbols)
    log.info(f"[collect] 共 {total} 只股票待采集，线程数={COLLECT_WORKERS}")

    t0 = time.time()
    success_records = []
    failed_list = []
    lock = threading.Lock()

    def worker(sym_name):
        symbol, name = sym_name
        rec = fetch_one_kline(symbol, name, target_date)
        with lock:
            if rec:
                success_records.append(rec)
            else:
                failed_list.append(symbol)

    with ThreadPoolExecutor(max_workers=COLLECT_WORKERS) as executor:
        futures = {executor.submit(worker, sn): sn for sn in all_symbols}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 100 == 0 or done == total:
                elapsed = time.time() - t0
                log.info(f"[collect] 进度 {done}/{total}  成功={len(success_records)}  "
                         f"失败={len(failed_list)}  耗时={elapsed:.1f}s")
                print(f"[PROGRESS] done={done} total={total} failed={len(failed_list)}",
                      flush=True)

    # 批量写库
    year = target_date.year
    written = batch_upsert_klines(success_records, year)

    elapsed = time.time() - t0
    log.info(f"[collect] 完成！日期={target_date}  总计={total}  "
             f"成功={len(success_records)}  写库={written}  "
             f"失败={len(failed_list)}  耗时={elapsed:.1f}s")

    if failed_list:
        log.warning(f"[collect] 失败列表({len(failed_list)}): "
                     f"{failed_list[:20]}{'...' if len(failed_list) > 20 else ''}")

    return {
        'date':        str(target_date),
        'total':       total,
        'success':     len(success_records),
        'written':     written,
        'failed':      len(failed_list),
        'failed_list': failed_list,
        'elapsed_s':   round(elapsed, 2),
    }


# ═══════════════════════════════════════════════════════════════════
#  启动预热
# ═══════════════════════════════════════════════════════════════════

def warmup():
    """预热 mootdx 连接"""
    def _connect():
        try:
            get_mootdx_client()
            print("[collector] mootdx warmup OK")
        except Exception as e:
            print(f"[collector] mootdx warmup failed: {e}")
    threading.Thread(target=_connect, daemon=True).start()
