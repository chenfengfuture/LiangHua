"""
models/transaction_models.py — 分笔成交数据 DDL

实时分笔表: stock_transactions
历史分笔表: stock_history_transactions_YYYYMM（按月分表）
"""

from .base import TABLE_COMMON_SUFFIX


CREATE_MINUTE_TICK_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS `stock_indicators`.`{table_name}` (
    id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY   COMMENT '自增主键',
    symbol         VARCHAR(10)   NOT NULL                       COMMENT '股票代码（6位纯数字）',
    trade_date     DATE          NOT NULL                       COMMENT '交易日期',
    minute_idx     SMALLINT UNSIGNED NOT NULL                   COMMENT '分钟序号 0~239（0=09:30, 119=11:29, 120=13:00, 239=14:59）',
    time_label     CHAR(5)       NOT NULL                       COMMENT '时间标识 HH:MM',
    price          DECIMAL(12,4) NOT NULL                       COMMENT '成交价格',
    vol            INT UNSIGNED  NOT NULL DEFAULT 0             COMMENT '成交量(手)',
    volume         INT UNSIGNED  NOT NULL DEFAULT 0             COMMENT '成交量(股)',
    market         TINYINT       DEFAULT NULL                   COMMENT '市场代码(0=深圳,1=上海)',

    UNIQUE KEY uk_symbol_date_idx (symbol, trade_date, minute_idx),
    INDEX idx_symbol (symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol_date (symbol, trade_date),
""" + TABLE_COMMON_SUFFIX.format(table_comment='历史分时tick数据（1分钟粒度，按月分表）')


CREATE_STOCK_TRANSACTION_DDL = """
CREATE TABLE IF NOT EXISTS `stock_indicators`.`stock_transactions` (
    id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY   COMMENT '自增主键',
    symbol         VARCHAR(10)   NOT NULL                       COMMENT '股票代码（6位纯数字）',
    trade_date     DATE          NOT NULL                       COMMENT '交易日期',
    seq            INT UNSIGNED  NOT NULL                       COMMENT '分笔序号，对应 mootdx start 偏移',
    time_label     CHAR(5)       NOT NULL                       COMMENT '成交时间 HH:MM',

    price          DECIMAL(12,4) NOT NULL                       COMMENT '成交价格',
    vol            INT UNSIGNED  NOT NULL DEFAULT 0             COMMENT '成交量(手/原始单位)',
    volume         INT UNSIGNED  NOT NULL DEFAULT 0             COMMENT '成交量',
    num            INT           DEFAULT NULL                   COMMENT '成交笔数，仅实时 transaction 可能返回',
    buyorsell      TINYINT       DEFAULT NULL                   COMMENT '买卖方向(0/1/2，按 mootdx 原始值)',
    market         TINYINT       DEFAULT NULL                   COMMENT '市场代码(0=深圳,1=上海)',
    data_type      VARCHAR(20)   NOT NULL DEFAULT 'realtime'    COMMENT '数据类型: realtime/history',

    UNIQUE KEY uk_symbol_date_seq (symbol, trade_date, seq),
    INDEX idx_symbol (symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol_date (symbol, trade_date),
""" + TABLE_COMMON_SUFFIX.format(table_comment='实时分笔成交数据')


CREATE_STOCK_HISTORY_TRANSACTION_DDL = """
CREATE TABLE IF NOT EXISTS `stock_indicators`.`{table_name}` (
    id             BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY   COMMENT '自增主键',
    symbol         VARCHAR(10)   NOT NULL                       COMMENT '股票代码（6位纯数字）',
    trade_date     DATE          NOT NULL                       COMMENT '交易日期',
    seq            INT UNSIGNED  NOT NULL                       COMMENT '分笔序号，对应 mootdx start 偏移',
    time_label     CHAR(5)       NOT NULL                       COMMENT '成交时间 HH:MM',

    price          DECIMAL(12,4) NOT NULL                       COMMENT '成交价格',
    vol            INT UNSIGNED  NOT NULL DEFAULT 0             COMMENT '成交量(手/原始单位)',
    volume         INT UNSIGNED  NOT NULL DEFAULT 0             COMMENT '成交量',
    num            INT           DEFAULT NULL                   COMMENT '成交笔数，历史 transactions 通常为空',
    buyorsell      TINYINT       DEFAULT NULL                   COMMENT '买卖方向(0/1/2，按 mootdx 原始值)',
    market         TINYINT       DEFAULT NULL                   COMMENT '市场代码(0=深圳,1=上海)',
    data_type      VARCHAR(20)   NOT NULL DEFAULT 'history'     COMMENT '数据类型: realtime/history',
    auto_clean     TINYINT(1)    NOT NULL DEFAULT 1             COMMENT '是否允许自动清理(1=允许,0=长期保留)',
    retention_days INT UNSIGNED  NOT NULL DEFAULT 30            COMMENT '保留天数，auto_clean=1 时用于清理策略',
    expire_date    DATE          DEFAULT NULL                   COMMENT '预计过期日期，由 trade_date + retention_days 计算',

    UNIQUE KEY uk_symbol_date_seq (symbol, trade_date, seq),
    INDEX idx_symbol (symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol_date (symbol, trade_date),
    INDEX idx_auto_clean_expire (auto_clean, expire_date),
""" + TABLE_COMMON_SUFFIX.format(table_comment='历史分笔成交数据（按月分表）')


def get_history_transaction_ddl(table_name: str) -> str:
    """根据实际表名生成历史分笔成交完整 DDL。"""
    return CREATE_STOCK_HISTORY_TRANSACTION_DDL.format(table_name=table_name)

def get_minute_tick_ddl(table_name: str) -> str:
    """根据实际表名生成历史分笔成交完整 DDL。"""
    return CREATE_MINUTE_TICK_TABLE_DDL.format(table_name=table_name)