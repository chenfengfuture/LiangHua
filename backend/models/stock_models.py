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
from .base import TABLE_COMMON_SUFFIX

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
   

    PRIMARY KEY (`symbol`),
    INDEX idx_name (`name`(20)),
    INDEX idx_market (`market`),
    INDEX idx_industry (`industry`),
    INDEX idx_list_date (`list_date`),
    INDEX idx_is_active (`is_active`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='A股股票完整信息表')

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
    UNIQUE KEY uk_symbol_datetime (symbol, datetime),
    INDEX idx_symbol (symbol),
    INDEX idx_close (close),
    INDEX idx_year (year),
    INDEX idx_name (name),
""" + TABLE_COMMON_SUFFIX.format(table_comment='{comment}')

KLINE_YEAR_MIN = 1990
KLINE_YEAR_MAX = 2030


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
    INDEX idx_symbol_month (symbol(10), `year_month`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='月K线汇总')


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
    UNIQUE KEY uk_symbol_date (symbol, trade_date),
    INDEX idx_table_name (table_name),
""" + TABLE_COMMON_SUFFIX.format(table_comment='K线分表索引')

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
    UNIQUE KEY uk_symbol_date_time (symbol, trade_date, time_label),
    INDEX idx_symbol_date (symbol, trade_date),
""" + TABLE_COMMON_SUFFIX.format(table_comment='分时数据（5分钟）')

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
    UNIQUE KEY uk_symbol_time_seq (symbol, trade_time, seq),
    INDEX idx_symbol (symbol),
""" + TABLE_COMMON_SUFFIX.format(table_comment='{comment}')

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
    `source` VARCHAR(20) DEFAULT 'akshare' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_trade_date_symbol (trade_date, symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol (symbol),
    INDEX idx_name (name(20)),
""" + TABLE_COMMON_SUFFIX.format(table_comment='龙虎榜详情数据表')

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
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date_symbol` (`trade_date`, `symbol`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_symbol` (`symbol`)
""" + TABLE_COMMON_SUFFIX.format(table_comment='龙虎榜-机构买卖每日统计')

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
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date_broker` (`trade_date`, `broker_code`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_broker_code` (`broker_code`)
""" + TABLE_COMMON_SUFFIX.format(table_comment='龙虎榜-每日活跃营业部')


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
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_range` (`symbol`, `time_range`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_time_range` (`time_range`),
    KEY `idx_latest_date` (`latest_date`)
""" + TABLE_COMMON_SUFFIX.format(table_comment='龙虎榜-个股上榜统计')

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
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_broker_date_symbol` (`broker_code`, `trade_date`, `symbol`),
    KEY `idx_broker_code` (`broker_code`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_symbol` (`symbol`)
""" + TABLE_COMMON_SUFFIX.format(table_comment='龙虎榜-营业部历史交易明细')


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
    `source` VARCHAR(20) DEFAULT 'em' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_data_date (data_date),
    INDEX idx_data_date (data_date),
""" + TABLE_COMMON_SUFFIX.format(table_comment='月度股票账户统计表')

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
    `source` VARCHAR(20) DEFAULT 'em' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_trade_date_symbol (trade_date, symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol (symbol),
    INDEX idx_comprehensive_score (comprehensive_score DESC),
    INDEX idx_focus_index (focus_index DESC),
""" + TABLE_COMMON_SUFFIX.format(table_comment='千股千评数据表')

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
    `source` VARCHAR(20) DEFAULT 'em' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_trade_date_symbol (trade_date, symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol (symbol),
    INDEX idx_user_focus_index (user_focus_index DESC),
""" + TABLE_COMMON_SUFFIX.format(table_comment='用户关注指数表')

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
    `source` VARCHAR(20) DEFAULT 'em' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_trade_date_symbol (trade_date, symbol),
    INDEX idx_trade_date (trade_date),
    INDEX idx_symbol (symbol),
    INDEX idx_participation_desire (participation_desire DESC),
""" + TABLE_COMMON_SUFFIX.format(table_comment='市场参与意愿表')

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
    `source` VARCHAR(20) DEFAULT 'em' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_stat_date_symbol (stat_date, symbol),
    INDEX idx_stat_date (stat_date),
    INDEX idx_symbol (symbol),
    INDEX idx_holders_change_ratio (holders_change_ratio DESC),
""" + TABLE_COMMON_SUFFIX.format(table_comment='全市场股东户数表')

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
    `source` VARCHAR(20) DEFAULT 'em' COMMENT '数据来源',
    
    -- 唯一约束与索引
    UNIQUE KEY uk_stat_date_symbol (stat_date, symbol),
    INDEX idx_stat_date (stat_date),
    INDEX idx_symbol (symbol),
    INDEX idx_holders_change_ratio (holders_change_ratio DESC),
    INDEX idx_interval_pct_chg (interval_pct_chg DESC),
""" + TABLE_COMMON_SUFFIX.format(table_comment='个股股东户数详情表')





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


