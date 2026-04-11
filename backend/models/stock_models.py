"""
models/stock_models.py — 股票系统数据库模型 & CRUD 工具

管理股票相关全部数据表的结构定义和常用查询：
  1. stocks_info          — 股票基础信息（3908 只）
  2. stock_klines_YYYY    — 日 K 线（按年分表，1990~2026）
  3. stock_klines_monthly — 月 K 线汇总
  4. kline_index          — K 线索引（快速定位分表）
  5. intraday_minutes     — 分时数据（5 分钟粒度）
  6. intraday_transactions_YYYYMMDD — 分笔成交（按天分表）

所有函数使用 utils.db.get_conn() 全局连接池。
"""

from datetime import date, datetime
from typing import Optional

from utils.db import get_conn, table_exists


# ═══════════════════════════════════════════════════════════════════
#  1. stocks_info — 股票基础信息
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCKS_INFO_DDL = """
CREATE TABLE IF NOT EXISTS `stocks_info` (
    symbol     TEXT         NOT NULL         COMMENT '股票代码',
    name       TEXT         DEFAULT NULL     COMMENT '股票名称',
    market     TEXT         DEFAULT NULL     COMMENT '市场: SH/SZ',
    list_date  DATE         DEFAULT NULL     COMMENT '上市日期',
    INDEX idx_symbol ((symbol(10)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='A股股票基础信息'
"""


# ─── CRUD ────────────────────────────────────────────────────────

def fetch_all_stocks() -> list[dict]:
    """获取全部股票列表 [{symbol, name, market, list_date}, ...]"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol, name, market, list_date FROM stocks_info ORDER BY symbol")
            return cur.fetchall()
    finally:
        conn.close()


def fetch_stocks_info(symbol: str) -> Optional[dict]:
    """获取单只股票的基础信息"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol, name, market, list_date FROM stocks_info WHERE symbol = %s", (symbol,))
            return cur.fetchone()
    finally:
        conn.close()


def search_stocks(keyword: str, limit: int = 20) -> list[dict]:
    """模糊搜索股票（代码或名称）"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT symbol, name, market FROM stocks_info "
                "WHERE symbol LIKE %s OR name LIKE %s ORDER BY symbol LIMIT %s",
                (f"%{keyword}%", f"%{keyword}%", limit)
            )
            return cur.fetchall()
    finally:
        conn.close()


def get_stocks_count() -> int:
    """获取股票总数"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM stocks_info")
            row = cur.fetchone()
            return row['cnt'] if row else 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
#  2. stock_klines_YYYY — 日 K 线（按年分表）
# ═══════════════════════════════════════════════════════════════════

CREATE_KLINES_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS `{table_name}` (
    id         BIGINT        AUTO_INCREMENT PRIMARY KEY,
    symbol     VARCHAR(10)   NOT NULL                COMMENT '股票代码',
    name       VARCHAR(50)   DEFAULT NULL             COMMENT '股票名称',
    datetime   DATETIME      NOT NULL                COMMENT 'K线时间',
    open       DECIMAL(12,2) DEFAULT NULL             COMMENT '开盘价',
    high       DECIMAL(12,2) DEFAULT NULL             COMMENT '最高价',
    low        DECIMAL(12,2) DEFAULT NULL             COMMENT '最低价',
    close      DECIMAL(12,2) DEFAULT NULL             COMMENT '收盘价',
    vol        DECIMAL(20,2) DEFAULT NULL             COMMENT '成交量(手)',
    amount     DECIMAL(20,2) DEFAULT NULL             COMMENT '成交额',
    volume     DECIMAL(20,2) DEFAULT NULL             COMMENT '成交量(股)',
    year       INT           DEFAULT NULL             COMMENT '年',
    month      INT           DEFAULT NULL             COMMENT '月',
    day        INT           DEFAULT NULL             COMMENT '日',
    hour       INT           DEFAULT NULL             COMMENT '时',
    minute     INT           DEFAULT NULL             COMMENT '分',
    created_at TIMESTAMP     DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
    UNIQUE KEY uk_symbol_datetime (symbol, datetime),
    INDEX idx_symbol (symbol),
    INDEX idx_close (close),
    INDEX idx_year (year),
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{comment}'
"""

KLINE_YEAR_MIN = 1990
KLINE_YEAR_MAX = 2030


def get_kline_table_name(year: int) -> str:
    """获取日 K 分表名"""
    return f"stock_klines_{year}"


def create_kline_table(year: int) -> str:
    """创建指定年份的 K 线分表（幂等）"""
    table_name = get_kline_table_name(year)
    if table_exists(table_name):
        return table_name
    ddl = CREATE_KLINES_TABLE_DDL.format(
        table_name=table_name,
        comment=f'{year}年日K线数据'
    )
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    finally:
        conn.close()
    return table_name


def ensure_kline_tables_for_range(year_start: int, year_end: int):
    """批量确保指定年份范围的所有 K 线分表存在"""
    for y in range(year_start, year_end + 1):
        create_kline_table(y)


# ─── K 线 CRUD ───────────────────────────────────────────────────

def fetch_klines(symbol: str, year: int, start_date: str = None, end_date: str = None) -> list[dict]:
    """
    查询单只股票指定年份的日 K 线。

    Args:
        symbol:     股票代码
        year:       年份
        start_date: 起始日期 (YYYY-MM-DD)，可选
        end_date:   截止日期 (YYYY-MM-DD)，可选

    Returns:
        [{symbol, name, datetime, open, high, low, close, vol, amount, ...}, ...]
    """
    table = get_kline_table_name(year)
    sql = f"SELECT * FROM `{table}` WHERE symbol = %s"
    params = [symbol]

    if start_date:
        sql += " AND datetime >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND datetime <= %s"
        params.append(end_date)

    sql += " ORDER BY datetime ASC"

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            return cur.fetchall()
    finally:
        conn.close()


def fetch_klines_multi_year(symbol: str, start_date: str, end_date: str) -> list[dict]:
    """
    跨年查询 K 线（自动拆分到各年份分表后合并排序）。

    Args:
        symbol:     股票代码
        start_date: 起始日期 (YYYY-MM-DD)
        end_date:   截止日期 (YYYY-MM-DD)

    Returns:
        按时间升序排列的 K 线列表
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    all_rows = []
    for year in range(start_dt.year, end_dt.year + 1):
        yd_start = start_date if year == start_dt.year else f"{year}-01-01"
        yd_end = end_date if year == end_dt.year else f"{year}-12-31"
        rows = fetch_klines(symbol, year, yd_start, yd_end)
        all_rows.extend(rows)
    # 按时间排序
    all_rows.sort(key=lambda r: r.get('datetime', ''))
    return all_rows


def fetch_latest_kline(symbol: str) -> Optional[dict]:
    """获取某只股票最新一根日 K"""
    # 先查今年
    year = date.today().year
    table = get_kline_table_name(year)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM `{table}` WHERE symbol = %s ORDER BY datetime DESC LIMIT 1",
                (symbol,)
            )
            row = cur.fetchone()
            if row:
                return row
    finally:
        conn.close()
    # 今年没数据，逐年往前找（最多找 3 年）
    for y in range(year - 1, year - 4, -1):
        table = get_kline_table_name(y)
        if not table_exists(table):
            continue
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT * FROM `{table}` WHERE symbol = %s ORDER BY datetime DESC LIMIT 1",
                    (symbol,)
                )
                row = cur.fetchone()
                if row:
                    return row
        finally:
            conn.close()
    return None


def fetch_kline_by_date(symbol: str, trade_date: str) -> Optional[dict]:
    """获取某只股票指定日期的日 K"""
    year = int(trade_date[:4])
    table = get_kline_table_name(year)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM `{table}` WHERE symbol = %s AND DATE(datetime) = %s LIMIT 1",
                (symbol, trade_date)
            )
            return cur.fetchone()
    finally:
        conn.close()


def count_klines(symbol: str, year: int) -> int:
    """统计某只股票某年的 K 线数量"""
    table = get_kline_table_name(year)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM `{table}` WHERE symbol = %s", (symbol,))
            row = cur.fetchone()
            return row['cnt'] if row else 0
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
#  3. stock_klines_monthly — 月 K 线汇总
# ═══════════════════════════════════════════════════════════════════

CREATE_KLINES_MONTHLY_DDL = """
CREATE TABLE IF NOT EXISTS `stock_klines_monthly` (
    symbol      TEXT         NOT NULL         COMMENT '股票代码',
    name        TEXT         DEFAULT NULL     COMMENT '股票名称',
    year_month  TEXT         NOT NULL         COMMENT '年月 YYYY-MM',
    open        DOUBLE       DEFAULT NULL     COMMENT '开盘价',
    high        DOUBLE       DEFAULT NULL     COMMENT '最高价',
    low         DOUBLE       DEFAULT NULL     COMMENT '最低价',
    close       DOUBLE       DEFAULT NULL     COMMENT '收盘价',
    vol         DOUBLE       DEFAULT NULL     COMMENT '成交量',
    amount      DOUBLE       DEFAULT NULL     COMMENT '成交额',
    month_date  DATETIME     DEFAULT NULL     COMMENT '月份日期',
    change_pct  DOUBLE       DEFAULT NULL     COMMENT '涨跌幅(%)',
    INDEX idx_symbol_month (symbol(10), year_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='月K线汇总'
"""


def fetch_monthly_klines(symbol: str, limit: int = 12) -> list[dict]:
    """获取某只股票的月 K 线（最近 N 个月）"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM stock_klines_monthly WHERE symbol = %s "
                "ORDER BY year_month DESC LIMIT %s",
                (symbol, limit)
            )
            return cur.fetchall()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
#  4. kline_index — K 线索引（快速定位分表）
# ═══════════════════════════════════════════════════════════════════

CREATE_KLINE_INDEX_DDL = """
CREATE TABLE IF NOT EXISTS `kline_index` (
    id             BIGINT       AUTO_INCREMENT PRIMARY KEY,
    symbol         VARCHAR(10)  NOT NULL            COMMENT '股票代码',
    trade_date     DATE         NOT NULL            COMMENT '交易日期',
    table_name     VARCHAR(30)  NOT NULL            COMMENT '所在分表名',
    record_offset  BIGINT       DEFAULT NULL         COMMENT '记录偏移',
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_symbol_date (symbol, trade_date),
    INDEX idx_table_name (table_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='K线分表索引'
"""


def fetch_kline_index(symbol: str, trade_date: str) -> Optional[dict]:
    """通过索引快速定位 K 线所在的分表"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM kline_index WHERE symbol = %s AND trade_date = %s",
                (symbol, trade_date)
            )
            return cur.fetchone()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
#  5. intraday_minutes — 分时数据（5 分钟粒度）
# ═══════════════════════════════════════════════════════════════════

CREATE_INTRADAY_MINUTES_DDL = """
CREATE TABLE IF NOT EXISTS `intraday_minutes` (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    symbol      VARCHAR(10)   NOT NULL            COMMENT '股票代码',
    trade_date  DATE          NOT NULL            COMMENT '交易日期',
    time_label  CHAR(5)       NOT NULL            COMMENT '时间 HH:MM',
    minute_idx  SMALLINT      NOT NULL            COMMENT '分钟序号 0~47',
    price       DECIMAL(10,4) NOT NULL            COMMENT '价格',
    vol         INT UNSIGNED  NOT NULL            COMMENT '成交量',
    avg_price   DECIMAL(10,4) NOT NULL            COMMENT '均价',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
    UNIQUE KEY uk_symbol_date_time (symbol, trade_date, time_label),
    INDEX idx_symbol_date (symbol, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='分时数据（5分钟）'
"""


def fetch_intraday_minutes(symbol: str, trade_date: str) -> list[dict]:
    """获取某只股票指定日期的分时数据"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT time_label, price, vol, avg_price FROM intraday_minutes "
                "WHERE symbol = %s AND trade_date = %s ORDER BY minute_idx ASC",
                (symbol, trade_date)
            )
            return cur.fetchall()
    finally:
        conn.close()


def fetch_latest_intraday_date(symbol: str) -> Optional[str]:
    """获取某只股票最新的分时数据日期"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT trade_date FROM intraday_minutes WHERE symbol = %s "
                "ORDER BY trade_date DESC LIMIT 1",
                (symbol,)
            )
            row = cur.fetchone()
            return str(row['trade_date']) if row else None
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
#  6. intraday_transactions_YYYYMMDD — 分笔成交（按天分表）
# ═══════════════════════════════════════════════════════════════════

CREATE_INTRADAY_TXN_DDL = """
CREATE TABLE IF NOT EXISTS `{table_name}` (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    symbol      VARCHAR(10)   NOT NULL            COMMENT '股票代码',
    trade_time  CHAR(8)       NOT NULL            COMMENT '成交时间 HH:MM:SS',
    seq         SMALLINT UNSIGNED NOT NULL         COMMENT '成交序号',
    price       DECIMAL(10,4) NOT NULL            COMMENT '成交价格',
    vol         INT UNSIGNED  NOT NULL            COMMENT '成交量(手)',
    side        CHAR(1)       NOT NULL            COMMENT '方向: B=买 S=卖',
    created_at  DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
    UNIQUE KEY uk_symbol_time_seq (symbol, trade_time, seq),
    INDEX idx_symbol (symbol)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{comment}'
"""


def get_txn_table_name(trade_date: str) -> str:
    """
    获取分笔成交分表名。
    trade_date 格式: YYYYMMDD 或 YYYY-MM-DD
    """
    return f"intraday_transactions_{trade_date.replace('-', '')}"


def create_txn_table(trade_date: str) -> str:
    """创建指定日期的分笔成交分表（幂等）"""
    table_name = get_txn_table_name(trade_date)
    if table_exists(table_name):
        return table_name
    date_str = trade_date.replace('-', '')
    ddl = CREATE_INTRADAY_TXN_DDL.format(
        table_name=table_name,
        comment=f'分笔成交 {date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}'
    )
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    finally:
        conn.close()
    return table_name


def fetch_transactions(symbol: str, trade_date: str, limit: int = 500) -> list[dict]:
    """
    查询某只股票指定日期的分笔成交。

    Args:
        symbol:     股票代码
        trade_date: 交易日期 (YYYY-MM-DD 或 YYYYMMDD)
        limit:      返回条数上限
    """
    table_name = get_txn_table_name(trade_date)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT trade_time, price, vol, side FROM `{table_name}` "
                f"WHERE symbol = %s ORDER BY seq ASC LIMIT %s",
                (symbol, limit)
            )
            return cur.fetchall()
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
#  批量建表（初始化用）
# ═══════════════════════════════════════════════════════════════════

def ensure_all_base_tables():
    """确保所有基础表存在（stocks_info / monthly / index / minutes）"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for ddl in [CREATE_STOCKS_INFO_DDL, CREATE_KLINES_MONTHLY_DDL,
                        CREATE_KLINE_INDEX_DDL, CREATE_INTRADAY_MINUTES_DDL]:
                cur.execute(ddl)
        conn.commit()
        print("[stock_models] 基础表检查完成")
    finally:
        conn.close()


# ─── 直接运行：初始化 ───────────────────────────────────────────

if __name__ == "__main__":
    print("正在检查并创建股票基础表...")
    ensure_all_base_tables()

    from datetime import datetime
    year = datetime.now().year
    print(f"正在确保 {year} 年 K 线分表存在...")
    create_kline_table(year)

    print("完成。")
