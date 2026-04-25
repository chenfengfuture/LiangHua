"""
models/stock_models.py — 股票系统数据库模型 & CRUD 工具

管理股票相关全部数据表的结构定义和常用查询：
  1. stocks_info          — 股票完整信息（A股股票完整信息表）
  2. stock_klines_YYYY    — 日 K 线（按年分表，1990~2026）
  3. stock_klines_monthly — 月 K 线汇总
  4. kline_index          — K 线索引（快速定位分表）
  5. intraday_minutes     — 分时数据（5 分钟粒度）
  6. intraday_transactions_YYYYMMDD — 分笔成交（按天分表）

所有函数使用 utils.db.get_conn() 全局连接池。
"""

from datetime import date, datetime
from typing import Optional

from utils.db import get_conn, table_exists, batch_insert

# ═══════════════════════════════════════════════════════════════════
#  1. stocks_info — 股票基础信息
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCKS_INFO_DDL = """
CREATE TABLE IF NOT EXISTS `stocks_info` (
    -- 基础标识
    `symbol`      VARCHAR(20)   NOT NULL                      COMMENT '股票代码（如000001.SZ）',
    `name`        VARCHAR(100)  DEFAULT NULL                  COMMENT '股票简称',
    `market`      VARCHAR(10)   DEFAULT NULL                  COMMENT '市场: SH/SZ/BJ',
    `market_type`      VARCHAR(20)   DEFAULT NULL             COMMENT '板块类型：主板A股/主板B股...',
    `list_date`   DATE          DEFAULT NULL                  COMMENT '上市日期',
    
    -- 公司全称与概况
    `full_name`   VARCHAR(200)  DEFAULT NULL                  COMMENT '公司全称',
    `eng_name`    VARCHAR(200)  DEFAULT NULL                  COMMENT '公司英文名称',
    `main_business` TEXT                                       COMMENT '主营业务（经营范围摘要）',
    `industry`    VARCHAR(100)  DEFAULT NULL                  COMMENT '所属行业（申万一级/二级）',
    `concept`     TEXT                                         COMMENT '概念板块（逗号分隔）',

    -- 资本与股东信息
    `registered_capital` DECIMAL(20,4) DEFAULT NULL           COMMENT '注册资本（万元）',
    `employees`   INT           DEFAULT NULL                  COMMENT '员工总数',
    `actual_controller` VARCHAR(200) DEFAULT NULL             COMMENT '实际控制人',
    `is_state_owned` TINYINT(1)  DEFAULT 0                    COMMENT '是否国企（1=是，0=否）',
    `state_share_ratio` DECIMAL(10,4) DEFAULT NULL            COMMENT '国资持股比例（%）',

    -- 财务概览（最新年报）
    `revenue`     DECIMAL(20,4) DEFAULT NULL                  COMMENT '最新年报营收（亿元）',
    `net_profit`  DECIMAL(20,4) DEFAULT NULL                  COMMENT '最新年报净利润（亿元）',
    `pe_ttm`      DECIMAL(12,4) DEFAULT NULL                  COMMENT '滚动市盈率（PE-TTM）',
    `pb`          DECIMAL(12,4) DEFAULT NULL                  COMMENT '市净率（PB）',
    `roe`         DECIMAL(10,4) DEFAULT NULL                  COMMENT '净资产收益率（%）',
    `debt_ratio`  DECIMAL(10,4) DEFAULT NULL                  COMMENT '资产负债率（%）',

    -- 其他补充
    `website`     VARCHAR(200)  DEFAULT NULL                  COMMENT '公司官网',
    `region`      VARCHAR(50)   DEFAULT NULL                  COMMENT '注册地（省/市）',
    `introduction` TEXT                                       COMMENT '公司简介（300字以内）',

    -- 状态
    `is_active`  TINYINT(1)   NOT NULL DEFAULT 1              COMMENT '是否在市（1=在市，0=退市/摘牌）',
    -- ai分析
    `ai_analyzed`  TINYINT(1)   NOT NULL DEFAULT 0            COMMENT '是否经过ai分析（1=经过，0=未经过）',
    -- ai分析时间 (作为过期缓存查询)
    `ai_analyzed_time`   DATE          DEFAULT NULL                COMMENT 'ai分析时间',
    -- 缓存字段key
    `cache_key`      VARCHAR(60)   DEFAULT NULL               COMMENT '缓存字段key',
    -- 元数据
    `update_time` DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',

    PRIMARY KEY (`symbol`),
    INDEX idx_name (`name`(20)),
    INDEX idx_market (`market`),
    INDEX idx_industry (`industry`),
    INDEX idx_list_date (`list_date`),
    INDEX idx_is_active (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='A股股票完整信息表';
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
    `year_month`  TEXT         NOT NULL         COMMENT '年月 YYYY-MM',
    open        DOUBLE       DEFAULT NULL     COMMENT '开盘价',
    high        DOUBLE       DEFAULT NULL     COMMENT '最高价',
    low         DOUBLE       DEFAULT NULL     COMMENT '最低利',
    close       DOUBLE       DEFAULT NULL     COMMENT '收盘价',
    vol         DOUBLE       DEFAULT NULL     COMMENT '成交量',
    amount      DOUBLE       DEFAULT NULL     COMMENT '成交额',
    month_date  DATETIME     DEFAULT NULL     COMMENT '月份日期',
    change_pct  DOUBLE       DEFAULT NULL     COMMENT '涨跌幅(%)',
    INDEX idx_symbol_month (symbol(10), `year_month`)
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
#  7. lhb_detail — 龙虎榜详情数据表
# ═══════════════════════════════════════════════════════════════════

CREATE_LHB_DETAIL_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_detail` (
    -- 主键与元数据
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    
    -- 核心标识字段
    `seq` INT COMMENT '序号',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码（标准化为 000793.SZ）',
    `name` VARCHAR(100) COMMENT '股票名称',
    `trade_date` DATE NOT NULL COMMENT '上榜日',
    
    -- 解读与价格信息
    `interpretation` VARCHAR(200) COMMENT '解读',
    `close` DECIMAL(10,4) COMMENT '收盘价',
    `pct_chg` DECIMAL(10,4) COMMENT '涨跌幅',
    
    -- 龙虎榜金额数据
    `net_buy_amount` DECIMAL(20,2) COMMENT '龙虎榜净买额',
    `buy_amount` DECIMAL(20,2) COMMENT '龙虎榜买入额',
    `sell_amount` DECIMAL(20,2) COMMENT '龙虎榜卖出额',
    `turnover_amount` DECIMAL(20,2) COMMENT '龙虎榜成交额',
    `total_market_amount` DECIMAL(20,2) COMMENT '市场总成交额',
    
    -- 比例数据
    `net_buy_ratio` DECIMAL(10,6) COMMENT '净买额占总成交比',
    `turnover_ratio` DECIMAL(10,6) COMMENT '成交额占总成交比',
    `turnover_rate` DECIMAL(10,6) COMMENT '换手率',
    `free_cap` DECIMAL(20,2) COMMENT '流通市值',
    
    -- 上榜原因
    `reason` TEXT COMMENT '上榜原因',
    
    -- 上榜后表现
    `after_1d_pct` DECIMAL(10,4) COMMENT '上榜后1日涨跌幅',
    `after_2d_pct` DECIMAL(10,4) COMMENT '上榜后2日涨跌幅',
    `after_5d_pct` DECIMAL(10,4) COMMENT '上榜后5日涨跌幅（可NULL）',
    `after_10d_pct` DECIMAL(10,4) COMMENT '上榜后10日涨跌幅（可NULL）',
    
    -- 附加字段
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `source` VARCHAR(20) DEFAULT 'akshare' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_trade_date_symbol (trade_date, symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol (symbol),
    INDEX idx_name (name(20))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='龙虎榜详情数据表';
"""


def fetch_lhb_detail_by_date(trade_date: str) -> list[dict]:
    """
    查询指定日期的龙虎榜详情数据
    
    Args:
        trade_date: 交易日期 (YYYY-MM-DD)
    
    Returns:
        龙虎榜详情数据列表
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM lhb_detail WHERE trade_date = %s ORDER BY seq ASC",
                (trade_date,)
            )
            return cur.fetchall()
    finally:
        conn.close()


def fetch_lhb_detail_by_date_range(start_date: str, end_date: str) -> list[dict]:
    """
    查询指定日期范围内的龙虎榜详情数据
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
    
    Returns:
        龙虎榜详情数据列表
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM lhb_detail WHERE trade_date BETWEEN %s AND %s ORDER BY trade_date ASC, seq ASC",
                (start_date, end_date)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_lhb_detail_batch(data_list: list[dict]) -> int:
    """
    批量保存龙虎榜详情数据
    
    Args:
        data_list: 龙虎榜数据列表
        
    Returns:
        插入/更新的记录数
    """
    if not data_list:
        return 0
    
    sql = """
    INSERT INTO lhb_detail (
        seq, symbol, name, trade_date, interpretation, close, pct_chg,
        net_buy_amount, buy_amount, sell_amount, turnover_amount, total_market_amount,
        net_buy_ratio, turnover_ratio, turnover_rate, free_cap, reason,
        after_1d_pct, after_2d_pct, after_5d_pct, after_10d_pct, source
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        seq = VALUES(seq),
        name = VALUES(name),
        interpretation = VALUES(interpretation),
        close = VALUES(close),
        pct_chg = VALUES(pct_chg),
        net_buy_amount = VALUES(net_buy_amount),
        buy_amount = VALUES(buy_amount),
        sell_amount = VALUES(sell_amount),
        turnover_amount = VALUES(turnover_amount),
        total_market_amount = VALUES(total_market_amount),
        net_buy_ratio = VALUES(net_buy_ratio),
        turnover_ratio = VALUES(turnover_ratio),
        turnover_rate = VALUES(turnover_rate),
        free_cap = VALUES(free_cap),
        reason = VALUES(reason),
        after_1d_pct = VALUES(after_1d_pct),
        after_2d_pct = VALUES(after_2d_pct),
        after_5d_pct = VALUES(after_5d_pct),
        after_10d_pct = VALUES(after_10d_pct),
        source = VALUES(source),
        updated_at = CURRENT_TIMESTAMP
    """
    
    params = []
    for item in data_list:
        params.append((
            item.get('seq'),
            item.get('symbol'),
            item.get('name'),
            item.get('trade_date'),
            item.get('interpretation'),
            item.get('close'),
            item.get('pct_chg'),
            item.get('net_buy_amount'),
            item.get('buy_amount'),
            item.get('sell_amount'),
            item.get('turnover_amount'),
            item.get('total_market_amount'),
            item.get('net_buy_ratio'),
            item.get('turnover_ratio'),
            item.get('turnover_rate'),
            item.get('free_cap'),
            item.get('reason'),
            item.get('after_1d_pct'),
            item.get('after_2d_pct'),
            item.get('after_5d_pct'),
            item.get('after_10d_pct'),
            item.get('source', 'akshare')
        ))
    
    return batch_insert(sql, params)


# ═══════════════════════════════════════════════════════════════════
#  龙虎榜 — 机构买卖每日统计 (lhb_institution)
# ═══════════════════════════════════════════════════════════════════

CREATE_LHB_INSTITUTION_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_institution` (
    `id`                        BIGINT        NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
    `trade_date`                DATE          NOT NULL                 COMMENT '上榜日期',
    `symbol`                    VARCHAR(20)   NOT NULL                 COMMENT '股票代码（含后缀，如000001.SZ）',
    `name`                      VARCHAR(100)  DEFAULT NULL             COMMENT '股票名称',
    `close`                     DECIMAL(12,4) DEFAULT NULL             COMMENT '收盘价',
    `pct_chg`                   DECIMAL(10,4) DEFAULT NULL             COMMENT '涨跌幅（%）',
    `buy_inst_cnt`              INT           DEFAULT NULL             COMMENT '买方机构数',
    `sell_inst_cnt`             INT           DEFAULT NULL             COMMENT '卖方机构数',
    `inst_buy_amount`           DECIMAL(20,4) DEFAULT NULL             COMMENT '机构买入总额（元）',
    `inst_sell_amount`          DECIMAL(20,4) DEFAULT NULL             COMMENT '机构卖出总额（元）',
    `inst_net_buy_amount`       DECIMAL(20,4) DEFAULT NULL             COMMENT '机构买入净额（元）',
    `total_market_amount`       DECIMAL(20,4) DEFAULT NULL             COMMENT '市场总成交额（元）',
    `inst_net_buy_ratio`        DECIMAL(12,6) DEFAULT NULL             COMMENT '机构净买额占总成交额比（%）',
    `turnover_rate`             DECIMAL(10,4) DEFAULT NULL             COMMENT '换手率（%）',
    `free_cap`                  DECIMAL(20,4) DEFAULT NULL             COMMENT '流通市值（亿元）',
    `reason`                    VARCHAR(500)  DEFAULT NULL             COMMENT '上榜原因',
    `seq`                       INT           DEFAULT NULL             COMMENT '序号',
    `created_at`                DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
    `updated_at`                DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date_symbol` (`trade_date`, `symbol`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_symbol` (`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='龙虎榜-机构买卖每日统计';
"""


def fetch_lhb_institution_by_date_range(start_date: str, end_date: str) -> list:
    """查询指定日期范围内的机构买卖统计数据（start_date/end_date 为 YYYY-MM-DD）"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM lhb_institution WHERE trade_date BETWEEN %s AND %s ORDER BY trade_date ASC, seq ASC",
                (start_date, end_date)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_lhb_institution_batch(data_list: list) -> int:
    """批量保存机构买卖统计数据（ON DUPLICATE KEY UPDATE 幂等写入）"""
    if not data_list:
        return 0

    sql = """
    INSERT INTO lhb_institution (
        trade_date, symbol, name, close, pct_chg,
        buy_inst_cnt, sell_inst_cnt, inst_buy_amount, inst_sell_amount, inst_net_buy_amount,
        total_market_amount, inst_net_buy_ratio, turnover_rate, free_cap, reason, seq
    ) VALUES (
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        name                 = VALUES(name),
        close                = VALUES(close),
        pct_chg              = VALUES(pct_chg),
        buy_inst_cnt         = VALUES(buy_inst_cnt),
        sell_inst_cnt        = VALUES(sell_inst_cnt),
        inst_buy_amount      = VALUES(inst_buy_amount),
        inst_sell_amount     = VALUES(inst_sell_amount),
        inst_net_buy_amount  = VALUES(inst_net_buy_amount),
        total_market_amount  = VALUES(total_market_amount),
        inst_net_buy_ratio   = VALUES(inst_net_buy_ratio),
        turnover_rate        = VALUES(turnover_rate),
        free_cap             = VALUES(free_cap),
        reason               = VALUES(reason),
        seq                  = VALUES(seq),
        updated_at           = CURRENT_TIMESTAMP
    """

    params = []
    for item in data_list:
        params.append((
            item.get('trade_date'),
            item.get('symbol'),
            item.get('name'),
            item.get('close'),
            item.get('pct_chg'),
            item.get('buy_inst_cnt'),
            item.get('sell_inst_cnt'),
            item.get('inst_buy_amount'),
            item.get('inst_sell_amount'),
            item.get('inst_net_buy_amount'),
            item.get('total_market_amount'),
            item.get('inst_net_buy_ratio'),
            item.get('turnover_rate'),
            item.get('free_cap'),
            item.get('reason'),
            item.get('seq'),
        ))
    return batch_insert(sql, params)


# ═══════════════════════════════════════════════════════════════════
#  龙虎榜 — 每日活跃营业部 (lhb_active_broker)
# ═══════════════════════════════════════════════════════════════════

CREATE_LHB_ACTIVE_BROKER_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_active_broker` (
    `id`                BIGINT        NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
    `trade_date`        DATE          NOT NULL                 COMMENT '上榜日期',
    `broker_code`       VARCHAR(50)   NOT NULL                 COMMENT '营业部代码',
    `broker_name`       VARCHAR(200)  DEFAULT NULL             COMMENT '营业部名称',
    `buy_stock_cnt`     INT           DEFAULT NULL             COMMENT '买入个股数',
    `sell_stock_cnt`    INT           DEFAULT NULL             COMMENT '卖出个股数',
    `buy_amount`        DECIMAL(20,4) DEFAULT NULL             COMMENT '买入总金额（元）',
    `sell_amount`       DECIMAL(20,4) DEFAULT NULL             COMMENT '卖出总金额（元）',
    `net_amount`        DECIMAL(20,4) DEFAULT NULL             COMMENT '总买卖净额（元）',
    `buy_stocks`        TEXT          DEFAULT NULL             COMMENT '买入股票列表（空格分隔）',
    `seq`               INT           DEFAULT NULL             COMMENT '序号',
    `created_at`        DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
    `updated_at`        DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date_broker` (`trade_date`, `broker_code`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_broker_code` (`broker_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='龙虎榜-每日活跃营业部';
"""


def fetch_lhb_active_broker_by_date_range(start_date: str, end_date: str) -> list:
    """查询指定日期范围内的活跃营业部数据（start_date/end_date 为 YYYY-MM-DD）"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM lhb_active_broker WHERE trade_date BETWEEN %s AND %s ORDER BY trade_date ASC, seq ASC",
                (start_date, end_date)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_lhb_active_broker_batch(data_list: list) -> int:
    """批量保存每日活跃营业部数据（ON DUPLICATE KEY UPDATE 幂等写入）"""
    if not data_list:
        return 0

    sql = """
    INSERT INTO lhb_active_broker (
        trade_date, broker_code, broker_name,
        buy_stock_cnt, sell_stock_cnt,
        buy_amount, sell_amount, net_amount,
        buy_stocks, seq
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        broker_name     = VALUES(broker_name),
        buy_stock_cnt   = VALUES(buy_stock_cnt),
        sell_stock_cnt  = VALUES(sell_stock_cnt),
        buy_amount      = VALUES(buy_amount),
        sell_amount     = VALUES(sell_amount),
        net_amount      = VALUES(net_amount),
        buy_stocks      = VALUES(buy_stocks),
        seq             = VALUES(seq),
        updated_at      = CURRENT_TIMESTAMP
    """

    params = []
    for item in data_list:
        params.append((
            item.get('trade_date'),
            item.get('broker_code'),
            item.get('broker_name'),
            item.get('buy_stock_cnt'),
            item.get('sell_stock_cnt'),
            item.get('buy_amount'),
            item.get('sell_amount'),
            item.get('net_amount'),
            item.get('buy_stocks'),
            item.get('seq'),
        ))
    return batch_insert(sql, params)


# ═══════════════════════════════════════════════════════════════════
#  龙虎榜 — 个股上榜统计 (lhb_stock_statistic)
# ═══════════════════════════════════════════════════════════════════

CREATE_LHB_STOCK_STATISTIC_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_stock_statistic` (
    `id`                    BIGINT        NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
    `symbol`                VARCHAR(20)   NOT NULL                 COMMENT '股票代码（含后缀）',
    `time_range`            VARCHAR(20)   NOT NULL                 COMMENT '统计周期：近一月/近三月/近六月/近一年',
    `name`                  VARCHAR(100)  DEFAULT NULL             COMMENT '股票名称',
    `latest_date`           DATE          DEFAULT NULL             COMMENT '最近上榜日',
    `close`                 DECIMAL(12,4) DEFAULT NULL             COMMENT '收盘价',
    `pct_chg`               DECIMAL(10,4) DEFAULT NULL             COMMENT '涨跌幅（%）',
    `on_board_cnt`          INT           DEFAULT NULL             COMMENT '上榜次数',
    `lhb_net_buy_amount`    DECIMAL(20,4) DEFAULT NULL             COMMENT '龙虎榜净买额（元）',
    `lhb_buy_amount`        DECIMAL(20,4) DEFAULT NULL             COMMENT '龙虎榜买入额（元）',
    `lhb_sell_amount`       DECIMAL(20,4) DEFAULT NULL             COMMENT '龙虎榜卖出额（元）',
    `lhb_total_amount`      DECIMAL(20,4) DEFAULT NULL             COMMENT '龙虎榜总成交额（元）',
    `buy_inst_cnt`          INT           DEFAULT NULL             COMMENT '买方机构次数',
    `sell_inst_cnt`         INT           DEFAULT NULL             COMMENT '卖方机构次数',
    `inst_net_buy_amount`   DECIMAL(20,4) DEFAULT NULL             COMMENT '机构买入净额（元）',
    `inst_buy_amount`       DECIMAL(20,4) DEFAULT NULL             COMMENT '机构买入总额（元）',
    `inst_sell_amount`      DECIMAL(20,4) DEFAULT NULL             COMMENT '机构卖出总额（元）',
    `pct_chg_1m`            DECIMAL(12,6) DEFAULT NULL             COMMENT '近1个月涨跌幅（%）',
    `pct_chg_3m`            DECIMAL(12,6) DEFAULT NULL             COMMENT '近3个月涨跌幅（%）',
    `pct_chg_6m`            DECIMAL(12,6) DEFAULT NULL             COMMENT '近6个月涨跌幅（%）',
    `pct_chg_1y`            DECIMAL(12,6) DEFAULT NULL             COMMENT '近1年涨跌幅（%）',
    `seq`                   INT           DEFAULT NULL             COMMENT '序号',
    `fetched_at`            DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '数据拉取时间',
    `updated_at`            DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_range` (`symbol`, `time_range`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_time_range` (`time_range`),
    KEY `idx_latest_date` (`latest_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='龙虎榜-个股上榜统计';
"""


def fetch_lhb_stock_statistic_by_range(time_range: str) -> list:
    """查询指定统计周期的个股上榜统计数据"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM lhb_stock_statistic WHERE time_range = %s ORDER BY seq ASC",
                (time_range,)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_lhb_stock_statistic_batch(data_list: list) -> int:
    """批量保存个股上榜统计数据（ON DUPLICATE KEY UPDATE 幂等写入）"""
    if not data_list:
        return 0

    sql = """
    INSERT INTO lhb_stock_statistic (
        symbol, time_range, name, latest_date, close, pct_chg,
        on_board_cnt, lhb_net_buy_amount, lhb_buy_amount, lhb_sell_amount, lhb_total_amount,
        buy_inst_cnt, sell_inst_cnt, inst_net_buy_amount, inst_buy_amount, inst_sell_amount,
        pct_chg_1m, pct_chg_3m, pct_chg_6m, pct_chg_1y, seq, fetched_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        name                  = VALUES(name),
        latest_date           = VALUES(latest_date),
        close                 = VALUES(close),
        pct_chg               = VALUES(pct_chg),
        on_board_cnt          = VALUES(on_board_cnt),
        lhb_net_buy_amount    = VALUES(lhb_net_buy_amount),
        lhb_buy_amount        = VALUES(lhb_buy_amount),
        lhb_sell_amount       = VALUES(lhb_sell_amount),
        lhb_total_amount      = VALUES(lhb_total_amount),
        buy_inst_cnt          = VALUES(buy_inst_cnt),
        sell_inst_cnt         = VALUES(sell_inst_cnt),
        inst_net_buy_amount   = VALUES(inst_net_buy_amount),
        inst_buy_amount       = VALUES(inst_buy_amount),
        inst_sell_amount      = VALUES(inst_sell_amount),
        pct_chg_1m            = VALUES(pct_chg_1m),
        pct_chg_3m            = VALUES(pct_chg_3m),
        pct_chg_6m            = VALUES(pct_chg_6m),
        pct_chg_1y            = VALUES(pct_chg_1y),
        seq                   = VALUES(seq),
        fetched_at            = VALUES(fetched_at),
        updated_at            = CURRENT_TIMESTAMP
    """

    params = []
    for item in data_list:
        params.append((
            item.get('symbol'),
            item.get('time_range'),
            item.get('name'),
            item.get('latest_date'),
            item.get('close'),
            item.get('pct_chg'),
            item.get('on_board_cnt'),
            item.get('lhb_net_buy_amount'),
            item.get('lhb_buy_amount'),
            item.get('lhb_sell_amount'),
            item.get('lhb_total_amount'),
            item.get('buy_inst_cnt'),
            item.get('sell_inst_cnt'),
            item.get('inst_net_buy_amount'),
            item.get('inst_buy_amount'),
            item.get('inst_sell_amount'),
            item.get('pct_chg_1m'),
            item.get('pct_chg_3m'),
            item.get('pct_chg_6m'),
            item.get('pct_chg_1y'),
            item.get('seq'),
            item.get('fetched_at'),
        ))
    return batch_insert(sql, params)


# ═══════════════════════════════════════════════════════════════════
#  龙虎榜 — 营业部历史交易明细 (lhb_broker_detail)
# ═══════════════════════════════════════════════════════════════════

CREATE_LHB_BROKER_DETAIL_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_broker_detail` (
    `id`                BIGINT        NOT NULL AUTO_INCREMENT  COMMENT '自增主键',
    `broker_code`       VARCHAR(50)   NOT NULL                 COMMENT '营业部代码',
    `broker_name`       VARCHAR(200)  DEFAULT NULL             COMMENT '营业部名称',
    `broker_short`      VARCHAR(200)  DEFAULT NULL             COMMENT '营业部简称',
    `trade_date`        DATE          NOT NULL                 COMMENT '交易日期',
    `symbol`            VARCHAR(20)   NOT NULL                 COMMENT '股票代码（含后缀）',
    `stock_name`        VARCHAR(100)  DEFAULT NULL             COMMENT '股票名称',
    `pct_chg`           DECIMAL(10,4) DEFAULT NULL             COMMENT '涨跌幅（%）',
    `buy_amount`        DECIMAL(20,4) DEFAULT NULL             COMMENT '买入金额（元）',
    `sell_amount`       DECIMAL(20,4) DEFAULT NULL             COMMENT '卖出金额（元）',
    `net_amount`        DECIMAL(20,4) DEFAULT NULL             COMMENT '净额（元）',
    `reason`            VARCHAR(500)  DEFAULT NULL             COMMENT '上榜原因',
    `after_1d_pct`      DECIMAL(12,6) DEFAULT NULL             COMMENT '1日后涨跌幅（%）',
    `after_2d_pct`      DECIMAL(12,6) DEFAULT NULL             COMMENT '2日后涨跌幅（%）',
    `after_3d_pct`      DECIMAL(12,6) DEFAULT NULL             COMMENT '3日后涨跌幅（%）',
    `after_5d_pct`      DECIMAL(12,6) DEFAULT NULL             COMMENT '5日后涨跌幅（%）',
    `after_10d_pct`     DECIMAL(12,6) DEFAULT NULL             COMMENT '10日后涨跌幅（%）',
    `after_20d_pct`     DECIMAL(12,6) DEFAULT NULL             COMMENT '20日后涨跌幅（%）',
    `after_30d_pct`     DECIMAL(12,6) DEFAULT NULL             COMMENT '30日后涨跌幅（%）',
    `seq`               INT           DEFAULT NULL             COMMENT '序号',
    `created_at`        DATETIME      DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',
    `updated_at`        DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_broker_date_symbol` (`broker_code`, `trade_date`, `symbol`),
    KEY `idx_broker_code` (`broker_code`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_symbol` (`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='龙虎榜-营业部历史交易明细';
"""


def fetch_lhb_broker_detail_by_code(broker_code: str) -> list:
    """查询指定营业部的历史交易明细"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM lhb_broker_detail WHERE broker_code = %s ORDER BY trade_date DESC, seq ASC",
                (broker_code,)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_lhb_broker_detail_batch(data_list: list) -> int:
    """批量保存营业部历史交易明细（ON DUPLICATE KEY UPDATE 幂等写入）"""
    if not data_list:
        return 0

    sql = """
    INSERT INTO lhb_broker_detail (
        broker_code, broker_name, broker_short,
        trade_date, symbol, stock_name,
        pct_chg, buy_amount, sell_amount, net_amount, reason,
        after_1d_pct, after_2d_pct, after_3d_pct,
        after_5d_pct, after_10d_pct, after_20d_pct, after_30d_pct, seq
    ) VALUES (
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        broker_name   = VALUES(broker_name),
        broker_short  = VALUES(broker_short),
        stock_name    = VALUES(stock_name),
        pct_chg       = VALUES(pct_chg),
        buy_amount    = VALUES(buy_amount),
        sell_amount   = VALUES(sell_amount),
        net_amount    = VALUES(net_amount),
        reason        = VALUES(reason),
        after_1d_pct  = VALUES(after_1d_pct),
        after_2d_pct  = VALUES(after_2d_pct),
        after_3d_pct  = VALUES(after_3d_pct),
        after_5d_pct  = VALUES(after_5d_pct),
        after_10d_pct = VALUES(after_10d_pct),
        after_20d_pct = VALUES(after_20d_pct),
        after_30d_pct = VALUES(after_30d_pct),
        seq           = VALUES(seq),
        updated_at    = CURRENT_TIMESTAMP
    """

    params = []
    for item in data_list:
        params.append((
            item.get('broker_code'),
            item.get('broker_name'),
            item.get('broker_short'),
            item.get('trade_date'),
            item.get('symbol'),
            item.get('stock_name'),
            item.get('pct_chg'),
            item.get('buy_amount'),
            item.get('sell_amount'),
            item.get('net_amount'),
            item.get('reason'),
            item.get('after_1d_pct'),
            item.get('after_2d_pct'),
            item.get('after_3d_pct'),
            item.get('after_5d_pct'),
            item.get('after_10d_pct'),
            item.get('after_20d_pct'),
            item.get('after_30d_pct'),
            item.get('seq'),
        ))
    return batch_insert(sql, params)


# ═══════════════════════════════════════════════════════════════════
#  8. holder模块 — 股东相关数据表
# ═══════════════════════════════════════════════════════════════════

# 8.1 月度股票账户统计表
CREATE_STOCK_ACCOUNT_STATISTICS_DDL = """
CREATE TABLE IF NOT EXISTS `stock_account_statistics` (
    -- 主键与元数据
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    
    -- 核心标识字段
    `data_date` DATE NOT NULL COMMENT '数据日期（月度）',
    
    -- 投资者数量统计
    `new_investors_count` INT COMMENT '新增投资者-数量',
    `new_investors_ratio_mom` DECIMAL(10,4) COMMENT '新增投资者-环比',
    `new_investors_ratio_yoy` DECIMAL(10,4) COMMENT '新增投资者-同比',
    `total_investors` BIGINT COMMENT '期末投资者-总量',
    `total_a_accounts` BIGINT COMMENT '期末投资者-A股账户',
    `total_b_accounts` BIGINT COMMENT '期末投资者-B股账户',
    
    -- 市值统计
    `total_market_cap` DECIMAL(20,2) COMMENT '沪深总市值（亿元）',
    `avg_household_cap` DECIMAL(20,2) COMMENT '沪深户均市值（万元）',
    
    -- 指数信息
    `sh_close` DECIMAL(10,4) COMMENT '上证指数-收盘',
    `sh_pct_chg` DECIMAL(10,4) COMMENT '上证指数-涨跌幅',
    
    -- 附加字段
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `source` VARCHAR(20) DEFAULT 'em' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_data_date (data_date),
    INDEX idx_data_date (data_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='月度股票账户统计表';
"""

# 8.2 千股千评数据表
CREATE_STOCK_COMMENT_DDL = """
CREATE TABLE IF NOT EXISTS `stock_comment` (
    -- 主键与元数据
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    
    -- 核心标识字段
    `trade_date` DATE NOT NULL COMMENT '交易日',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码（标准化）',
    `name` VARCHAR(100) COMMENT '股票名称',
    
    -- 基础信息
    `latest_price` DECIMAL(10,4) COMMENT '最新价',
    `pct_chg` DECIMAL(10,4) COMMENT '涨跌幅',
    `turnover_rate` DECIMAL(10,4) COMMENT '换手率',
    `pe_ratio` DECIMAL(12,4) COMMENT '市盈率',
    
    -- 评分数据
    `main_cost` DECIMAL(10,4) COMMENT '主力成本',
    `institution_participation` DECIMAL(10,4) COMMENT '机构参与度',
    `comprehensive_score` DECIMAL(10,4) COMMENT '综合得分',
    `rising_score` DECIMAL(10,4) COMMENT '上升',
    `current_rank` INT COMMENT '目前排名',
    `focus_index` DECIMAL(10,4) COMMENT '关注指数',
    
    -- 附加字段
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `source` VARCHAR(20) DEFAULT 'em' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_trade_date_symbol (trade_date, symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol (symbol),
    INDEX idx_comprehensive_score (comprehensive_score DESC),
    INDEX idx_focus_index (focus_index DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='千股千评数据表';
"""

# 8.3 用户关注指数表
CREATE_STOCK_COMMENT_FOCUS_DDL = """
CREATE TABLE IF NOT EXISTS `stock_comment_focus` (
    -- 主键与元数据
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    
    -- 核心标识字段
    `trade_date` DATE NOT NULL COMMENT '交易日',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码（标准化）',
    
    -- 关注指数
    `user_focus_index` DECIMAL(10,4) COMMENT '用户关注指数',
    
    -- 附加字段
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `source` VARCHAR(20) DEFAULT 'em' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_trade_date_symbol (trade_date, symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol (symbol),
    INDEX idx_user_focus_index (user_focus_index DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户关注指数表';
"""

# 8.4 市场参与意愿表
CREATE_STOCK_COMMENT_DESIRE_DDL = """
CREATE TABLE IF NOT EXISTS `stock_comment_desire` (
    -- 主键与元数据
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    
    -- 核心标识字段
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码（标准化）',
    
    -- 参与意愿数据
    `participation_desire` DECIMAL(10,4) COMMENT '参与意愿',
    `avg_5d_desire` DECIMAL(10,4) COMMENT '5日平均参与意愿',
    `desire_change` DECIMAL(10,4) COMMENT '参与意愿变化',
    `avg_5d_change` DECIMAL(10,4) COMMENT '5日平均变化',
    
    -- 附加字段
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `source` VARCHAR(20) DEFAULT 'em' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_trade_date_symbol (trade_date, symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol (symbol),
    INDEX idx_participation_desire (participation_desire DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='市场参与意愿表';
"""

# 8.5 全市场股东户数表
CREATE_STOCK_GDHS_ALL_DDL = """
CREATE TABLE IF NOT EXISTS `stock_gdhs_all` (
    -- 主键与元数据
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    
    -- 核心标识字段
    `stat_date` DATE NOT NULL COMMENT '股东户数统计截止日',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码（标准化）',
    `name` VARCHAR(100) COMMENT '股票名称',
    
    -- 价格信息
    `latest_price` DECIMAL(10,4) COMMENT '最新价',
    `pct_chg` DECIMAL(10,4) COMMENT '涨跌幅',
    `interval_pct_chg` DECIMAL(10,4) COMMENT '区间涨跌幅',
    
    -- 股东户数数据
    `current_holders` BIGINT COMMENT '股东户数-本次',
    `previous_holders` BIGINT COMMENT '股东户数-上次',
    `holders_change` BIGINT COMMENT '股东户数-增减',
    `holders_change_ratio` DECIMAL(10,4) COMMENT '股东户数-增减比例',
    
    -- 户均数据
    `avg_holding_value` DECIMAL(20,2) COMMENT '户均持股市值',
    `avg_holding_quantity` DECIMAL(20,2) COMMENT '户均持股数量',
    
    -- 市值与股本
    `total_market_cap` DECIMAL(20,2) COMMENT '总市值',
    `total_shares` DECIMAL(20,2) COMMENT '总股本',
    
    -- 公告信息
    `announce_date` DATE COMMENT '公告日期',
    
    -- 附加字段
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `source` VARCHAR(20) DEFAULT 'em' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_stat_date_symbol (stat_date, symbol),
    INDEX idx_stat_date (stat_date),
    INDEX idx_symbol (symbol),
    INDEX idx_holders_change_ratio (holders_change_ratio DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='全市场股东户数表';
"""

# 8.6 个股股东户数详情表
CREATE_STOCK_GDHS_DETAIL_DDL = """
CREATE TABLE IF NOT EXISTS `stock_gdhs_detail` (
    -- 主键与元数据
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    
    -- 核心标识字段
    `stat_date` DATE NOT NULL COMMENT '股东户数统计截止日',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码（标准化）',
    `name` VARCHAR(100) COMMENT '股票名称',
    
    -- 区间表现
    `interval_pct_chg` DECIMAL(10,4) COMMENT '区间涨跌幅',
    
    -- 股东户数数据
    `current_holders` BIGINT COMMENT '股东户数-本次',
    `previous_holders` BIGINT COMMENT '股东户数-上次',
    `holders_change` BIGINT COMMENT '股东户数-增减',
    `holders_change_ratio` DECIMAL(10,4) COMMENT '股东户数-增减比例',
    
    -- 户均数据
    `avg_holding_value` DECIMAL(20,2) COMMENT '户均持股市值',
    `avg_holding_quantity` DECIMAL(20,2) COMMENT '户均持股数量',
    
    -- 市值与股本
    `total_market_cap` DECIMAL(20,2) COMMENT '总市值',
    `total_shares` DECIMAL(20,2) COMMENT '总股本',
    
    -- 股本变动
    `shares_change` VARCHAR(200) COMMENT '股本变动',
    `shares_change_reason` VARCHAR(500) COMMENT '股本变动原因',
    
    -- 公告信息
    `announce_date` DATE COMMENT '股东户数公告日期',
    
    -- 附加字段
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `source` VARCHAR(20) DEFAULT 'em' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_stat_date_symbol (stat_date, symbol),
    INDEX idx_stat_date (stat_date),
    INDEX idx_symbol (symbol),
    INDEX idx_holders_change_ratio (holders_change_ratio DESC),
    INDEX idx_interval_pct_chg (interval_pct_chg DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='个股股东户数详情表';
"""


# ═══════════════════════════════════════════════════════════════════
#  holder模块CRUD函数
# ═══════════════════════════════════════════════════════════════════

# 1. 月度股票账户统计查询函数
def fetch_stock_account_statistics_by_date_range(start_date: str, end_date: str) -> list[dict]:
    """
    查询指定日期范围内的月度股票账户统计数据
    
    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
    
    Returns:
        月度股票账户统计数据列表
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM stock_account_statistics WHERE data_date BETWEEN %s AND %s ORDER BY data_date ASC",
                (start_date, end_date)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_stock_account_statistics_batch(data: list[dict]) -> int:
    """
    批量保存月度股票账户统计数据
    
    Args:
        data: 数据列表，每个元素为字典格式
    
    Returns:
        成功插入的记录数
    """
    sql = """
    INSERT INTO stock_account_statistics (
        data_date, new_investors_count, new_investors_ratio_mom, new_investors_ratio_yoy,
        total_investors, total_a_accounts, total_b_accounts, total_market_cap,
        avg_household_cap, sh_close, sh_pct_chg, source
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        new_investors_count = VALUES(new_investors_count),
        new_investors_ratio_mom = VALUES(new_investors_ratio_mom),
        new_investors_ratio_yoy = VALUES(new_investors_ratio_yoy),
        total_investors = VALUES(total_investors),
        total_a_accounts = VALUES(total_a_accounts),
        total_b_accounts = VALUES(total_b_accounts),
        total_market_cap = VALUES(total_market_cap),
        avg_household_cap = VALUES(avg_household_cap),
        sh_close = VALUES(sh_close),
        sh_pct_chg = VALUES(sh_pct_chg),
        updated_at = CURRENT_TIMESTAMP
    """
    
    params = []
    for item in data:
        params.append((
            item.get('data_date'),
            item.get('new_investors_count'),
            item.get('new_investors_ratio_mom'),
            item.get('new_investors_ratio_yoy'),
            item.get('total_investors'),
            item.get('total_a_accounts'),
            item.get('total_b_accounts'),
            item.get('total_market_cap'),
            item.get('avg_household_cap'),
            item.get('sh_close'),
            item.get('sh_pct_chg'),
            item.get('source', 'em')
        ))
    return batch_insert(sql, params)


# 2. 千股千评数据查询函数
def fetch_stock_comment_by_date(trade_date: str) -> list[dict]:
    """
    查询指定交易日的千股千评数据
    
    Args:
        trade_date: 交易日期 (YYYY-MM-DD)
    
    Returns:
        千股千评数据列表
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM stock_comment WHERE trade_date = %s ORDER BY comprehensive_score DESC",
                (trade_date,)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_stock_comment_batch(data: list[dict]) -> int:
    """
    批量保存千股千评数据
    
    Args:
        data: 数据列表，每个元素为字典格式
    
    Returns:
        成功插入的记录数
    """
    sql = """
    INSERT INTO stock_comment (
        trade_date, symbol, name, latest_price, pct_chg, turnover_rate,
        pe_ratio, main_cost, institution_participation, comprehensive_score,
        rising_score, current_rank, focus_index, source
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        latest_price = VALUES(latest_price),
        pct_chg = VALUES(pct_chg),
        turnover_rate = VALUES(turnover_rate),
        pe_ratio = VALUES(pe_ratio),
        main_cost = VALUES(main_cost),
        institution_participation = VALUES(institution_participation),
        comprehensive_score = VALUES(comprehensive_score),
        rising_score = VALUES(rising_score),
        current_rank = VALUES(current_rank),
        focus_index = VALUES(focus_index),
        updated_at = CURRENT_TIMESTAMP
    """
    
    params = []
    for item in data:
        params.append((
            item.get('trade_date'),
            item.get('symbol'),
            item.get('name'),
            item.get('latest_price'),
            item.get('pct_chg'),
            item.get('turnover_rate'),
            item.get('pe_ratio'),
            item.get('main_cost'),
            item.get('institution_participation'),
            item.get('comprehensive_score'),
            item.get('rising_score'),
            item.get('current_rank'),
            item.get('focus_index'),
            item.get('source', 'em')
        ))
    return batch_insert(sql, params)


# 3. 用户关注指数查询函数
def fetch_stock_comment_focus_by_symbol(symbol: str, limit: int = 30) -> list[dict]:
    """
    查询指定股票的用户关注指数数据
    
    Args:
        symbol: 股票代码
        limit: 返回记录数限制，默认30条
    
    Returns:
        用户关注指数数据列表
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM stock_comment_focus WHERE symbol = %s ORDER BY trade_date DESC LIMIT %s",
                (symbol, limit)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_stock_comment_focus_batch(data: list[dict]) -> int:
    """
    批量保存用户关注指数数据
    
    Args:
        data: 数据列表，每个元素为字典格式
    
    Returns:
        成功插入的记录数
    """
    sql = """
    INSERT INTO stock_comment_focus (
        trade_date, symbol, user_focus_index, source
    ) VALUES (
        %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        user_focus_index = VALUES(user_focus_index),
        updated_at = CURRENT_TIMESTAMP
    """
    
    params = []
    for item in data:
        params.append((
            item.get('trade_date'),
            item.get('symbol'),
            item.get('user_focus_index'),
            item.get('source', 'em')
        ))
    return batch_insert(sql, params)


# 4. 市场参与意愿查询函数
def fetch_stock_comment_desire_by_symbol(symbol: str, limit: int = 5) -> list[dict]:
    """
    查询指定股票的市场参与意愿数据
    
    Args:
        symbol: 股票代码
        limit: 返回记录数限制，默认5条
    
    Returns:
        市场参与意愿数据列表
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM stock_comment_desire WHERE symbol = %s ORDER BY trade_date DESC LIMIT %s",
                (symbol, limit)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_stock_comment_desire_batch(data: list[dict]) -> int:
    """
    批量保存市场参与意愿数据
    
    Args:
        data: 数据列表，每个元素为字典格式
    
    Returns:
        成功插入的记录数
    """
    sql = """
    INSERT INTO stock_comment_desire (
        trade_date, symbol, participation_desire, avg_5d_desire,
        desire_change, avg_5d_change, source
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        participation_desire = VALUES(participation_desire),
        avg_5d_desire = VALUES(avg_5d_desire),
        desire_change = VALUES(desire_change),
        avg_5d_change = VALUES(avg_5d_change),
        updated_at = CURRENT_TIMESTAMP
    """
    
    params = []
    for item in data:
        params.append((
            item.get('trade_date'),
            item.get('symbol'),
            item.get('participation_desire'),
            item.get('avg_5d_desire'),
            item.get('desire_change'),
            item.get('avg_5d_change'),
            item.get('source', 'em')
        ))
    return batch_insert(sql, params)


# 5. 全市场股东户数查询函数
def fetch_stock_gdhs_all_by_date(stat_date: str) -> list[dict]:
    """
    查询指定统计日期的全市场股东户数数据
    
    Args:
        stat_date: 统计截止日 (YYYY-MM-DD)
    
    Returns:
        全市场股东户数数据列表
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM stock_gdhs_all WHERE stat_date = %s ORDER BY holders_change_ratio DESC",
                (stat_date,)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_stock_gdhs_all_batch(data: list[dict]) -> int:
    """
    批量保存全市场股东户数数据
    
    Args:
        data: 数据列表，每个元素为字典格式
    
    Returns:
        成功插入的记录数
    """
    sql = """
    INSERT INTO stock_gdhs_all (
        stat_date, symbol, name, latest_price, pct_chg, interval_pct_chg,
        current_holders, previous_holders, holders_change, holders_change_ratio,
        avg_holding_value, avg_holding_quantity, total_market_cap, total_shares,
        announce_date, source
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        latest_price = VALUES(latest_price),
        pct_chg = VALUES(pct_chg),
        interval_pct_chg = VALUES(interval_pct_chg),
        current_holders = VALUES(current_holders),
        previous_holders = VALUES(previous_holders),
        holders_change = VALUES(holders_change),
        holders_change_ratio = VALUES(holders_change_ratio),
        avg_holding_value = VALUES(avg_holding_value),
        avg_holding_quantity = VALUES(avg_holding_quantity),
        total_market_cap = VALUES(total_market_cap),
        total_shares = VALUES(total_shares),
        announce_date = VALUES(announce_date),
        updated_at = CURRENT_TIMESTAMP
    """
    
    params = []
    for item in data:
        params.append((
            item.get('stat_date'),
            item.get('symbol'),
            item.get('name'),
            item.get('latest_price'),
            item.get('pct_chg'),
            item.get('interval_pct_chg'),
            item.get('current_holders'),
            item.get('previous_holders'),
            item.get('holders_change'),
            item.get('holders_change_ratio'),
            item.get('avg_holding_value'),
            item.get('avg_holding_quantity'),
            item.get('total_market_cap'),
            item.get('total_shares'),
            item.get('announce_date'),
            item.get('source', 'em')
        ))
    return batch_insert(sql, params)


# 6. 个股股东户数详情查询函数
def fetch_stock_gdhs_detail_by_symbol(symbol: str, limit: int = 66) -> list[dict]:
    """
    查询指定股票的股东户数详情数据
    
    Args:
        symbol: 股票代码
        limit: 返回记录数限制，默认66条
    
    Returns:
        个股股东户数详情数据列表
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM stock_gdhs_detail WHERE symbol = %s ORDER BY stat_date DESC LIMIT %s",
                (symbol, limit)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_stock_gdhs_detail_batch(data: list[dict]) -> int:
    """
    批量保存个股股东户数详情数据
    
    Args:
        data: 数据列表，每个元素为字典格式
    
    Returns:
        成功插入的记录数
    """
    sql = """
    INSERT INTO stock_gdhs_detail (
        stat_date, symbol, name, interval_pct_chg, current_holders,
        previous_holders, holders_change, holders_change_ratio,
        avg_holding_value, avg_holding_quantity, total_market_cap,
        total_shares, shares_change, shares_change_reason, announce_date, source
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    ) ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        interval_pct_chg = VALUES(interval_pct_chg),
        current_holders = VALUES(current_holders),
        previous_holders = VALUES(previous_holders),
        holders_change = VALUES(holders_change),
        holders_change_ratio = VALUES(holders_change_ratio),
        avg_holding_value = VALUES(avg_holding_value),
        avg_holding_quantity = VALUES(avg_holding_quantity),
        total_market_cap = VALUES(total_market_cap),
        total_shares = VALUES(total_shares),
        shares_change = VALUES(shares_change),
        shares_change_reason = VALUES(shares_change_reason),
        announce_date = VALUES(announce_date),
        updated_at = CURRENT_TIMESTAMP
    """
    
    params = []
    for item in data:
        params.append((
            item.get('stat_date'),
            item.get('symbol'),
            item.get('name'),
            item.get('interval_pct_chg'),
            item.get('current_holders'),
            item.get('previous_holders'),
            item.get('holders_change'),
            item.get('holders_change_ratio'),
            item.get('avg_holding_value'),
            item.get('avg_holding_quantity'),
            item.get('total_market_cap'),
            item.get('total_shares'),
            item.get('shares_change'),
            item.get('shares_change_reason'),
            item.get('announce_date'),
            item.get('source', 'em')
        ))
    return batch_insert(sql, params)


# ═══════════════════════════════════════════════════════════════════
#  批量建表（初始化用）
# ═══════════════════════════════════════════════════════════════════

def ensure_all_base_tables():
    """确保所有基础表存在（stocks_info / monthly / index / minutes / lhb_detail / holder模块）"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # 原有基础表
            for ddl in [CREATE_STOCKS_INFO_DDL, CREATE_KLINES_MONTHLY_DDL,
                        CREATE_KLINE_INDEX_DDL, CREATE_INTRADAY_MINUTES_DDL,
                        CREATE_LHB_DETAIL_DDL]:
                cur.execute(ddl)
            
            # holder模块表
            for ddl in [CREATE_STOCK_ACCOUNT_STATISTICS_DDL, CREATE_STOCK_COMMENT_DDL,
                        CREATE_STOCK_COMMENT_FOCUS_DDL, CREATE_STOCK_COMMENT_DESIRE_DDL,
                        CREATE_STOCK_GDHS_ALL_DDL, CREATE_STOCK_GDHS_DETAIL_DDL]:
                cur.execute(ddl)
                
        conn.commit()
        print("[stock_models] 基础表检查完成（包含holder模块）")
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
#  9. 雪球个股信息表 (xq_stock_info)
# ═══════════════════════════════════════════════════════════════════

CREATE_XQ_STOCK_INFO_DDL = """
CREATE TABLE IF NOT EXISTS `xq_stock_info` (
    `id` BIGINT AUTO_INCREMENT COMMENT '自增主键',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码（如000001.SZ）',
    `data` JSON COMMENT '雪球个股信息JSON数据',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol` (`symbol`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_update_time` (`update_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='雪球个股信息表';
"""


def fetch_xq_stock_info_by_symbol(symbol: str) -> list[dict]:
    """查询指定股票的雪球个股信息"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT symbol, data, update_time FROM xq_stock_info WHERE symbol = %s ORDER BY update_time DESC LIMIT 1",
                (symbol,)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_xq_stock_info_batch(data: list[dict]) -> int:
    """批量保存雪球个股信息"""
    sql = """
    INSERT INTO xq_stock_info (symbol, data, update_time)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE
        data = VALUES(data),
        update_time = VALUES(update_time)
    """
    
    params = []
    for item in data:
        params.append((
            item.get('symbol'),
            item.get('data'),
            item.get('update_time')
        ))
    return batch_insert(sql, params)


# ═══════════════════════════════════════════════════════════════════
#  10. 股票信息JSON表 (stock_info_json)
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCK_INFO_JSON_DDL = """
CREATE TABLE IF NOT EXISTS `stock_info_json` (
    `id` BIGINT AUTO_INCREMENT COMMENT '自增主键',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码（如000001.SZ）',
    `data` JSON COMMENT '股票信息JSON数据',
    `update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol` (`symbol`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_update_time` (`update_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票信息JSON表';
"""


def fetch_stock_info_json_by_symbol(symbol: str) -> list[dict]:
    """查询指定股票的股票信息JSON"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT symbol, data, update_time FROM stock_info_json WHERE symbol = %s ORDER BY update_time DESC LIMIT 1",
                (symbol,)
            )
            return cur.fetchall()
    finally:
        conn.close()


def save_stock_info_json_batch(data: list[dict]) -> int:
    """批量保存股票信息JSON"""
    sql = """
    INSERT INTO stock_info_json (symbol, data, update_time)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE
        data = VALUES(data),
        update_time = VALUES(update_time)
    """
    
    params = []
    for item in data:
        params.append((
            item.get('symbol'),
            item.get('data'),
            item.get('update_time')
        ))
    return batch_insert(sql, params)


# ═══════════════════════════════════════════════════════════════════
#  批量建表（初始化用） - 更新版本
# ═══════════════════════════════════════════════════════════════════

def ensure_all_base_tables():
    """确保所有基础表存在（stocks_info / monthly / index / minutes / lhb_detail / holder模块 / basic模块）"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            # 原有基础表
            for ddl in [CREATE_STOCKS_INFO_DDL, CREATE_KLINES_MONTHLY_DDL,
                       CREATE_KLINE_INDEX_DDL, CREATE_INTRADAY_MINUTES_DDL,
                       CREATE_LHB_DETAIL_DDL]:
                cur.execute(ddl)
            
            # holder模块表
            for ddl in [CREATE_STOCK_ACCOUNT_STATISTICS_DDL, CREATE_STOCK_COMMENT_DDL,
                       CREATE_STOCK_COMMENT_FOCUS_DDL, CREATE_STOCK_COMMENT_DESIRE_DDL,
                       CREATE_STOCK_GDHS_ALL_DDL, CREATE_STOCK_GDHS_DETAIL_DDL]:
                cur.execute(ddl)
            
            # basic模块表
            for ddl in [CREATE_XQ_STOCK_INFO_DDL, CREATE_STOCK_INFO_JSON_DDL]:
                cur.execute(ddl)
                
        conn.commit()
        print("[stock_models] 基础表检查完成（包含holder模块和basic模块）")
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
