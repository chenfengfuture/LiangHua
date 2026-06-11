from .base import TABLE_COMMON_SUFFIX

CREATE_MARGIN_TRADING_DAILY_STAT_DDL = """
CREATE TABLE IF NOT EXISTS `margin_trading_daily_stat`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `margin_balance` DECIMAL(12,3) DEFAULT NULL COMMENT '融资余额（亿元）',
    `short_balance` DECIMAL(12,3) DEFAULT NULL COMMENT '融券余额（亿元）',
    `margin_buy_amount` DECIMAL(12,3) DEFAULT NULL COMMENT '融资买入额（亿元）',
    `short_sell_amount` DECIMAL(12,3) DEFAULT NULL COMMENT '融券卖出额（亿元）',
    `securities_company_count` INT DEFAULT NULL COMMENT '证券公司数量（家）',
    `branch_office_count` INT DEFAULT NULL COMMENT '营业部数量（个）',
    `individual_investor_count` DECIMAL(12,4) DEFAULT NULL COMMENT '个人投资者数量（万人）',
    `institution_investor_count` DECIMAL(12,4) DEFAULT NULL COMMENT '机构投资者数量（万人）',
    `active_trader_count` DECIMAL(12,4) DEFAULT NULL COMMENT '参与交易的投资者数量（万人）',
    `liability_investor_count` DECIMAL(12,4) DEFAULT NULL COMMENT '有融资融券负债的投资者数量（万人）',
    `collateral_value` DECIMAL(20,3) DEFAULT NULL COMMENT '担保物总价值（亿元）',
    `avg_maintenance_ratio` DECIMAL(8,2) DEFAULT NULL COMMENT '平均维持担保比例（单位：%）',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_trade_date` (`trade_date`),
    KEY `idx_trade_date` (`trade_date`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='融资融券每日统计')


CREATE_MARGIN_TRADING_DAILY_DETAIL_DDL = """
CREATE TABLE IF NOT EXISTS `margin_trading_daily_detail`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `trade_date` DATE NOT NULL COMMENT '信用交易日期',
    `margin_balance` DECIMAL(20,3) DEFAULT NULL COMMENT '融资余额（元）',
    `margin_buy_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '融资买入额（元）',
    `short_volume` DECIMAL(18,0) DEFAULT NULL COMMENT '融券余量（股）',
    `short_balance` DECIMAL(20,3) DEFAULT NULL COMMENT '融券余量金额（元）',
    `short_sell_volume` DECIMAL(18,0) DEFAULT NULL COMMENT '融券卖出量（股）',
    `margin_short_balance` DECIMAL(20,3) DEFAULT NULL COMMENT '融资融券余额（元）',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_trade_date` (`trade_date`),
    KEY `idx_trade_date` (`trade_date`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='上交所融资融券逐日明细')



CREATE_MARGIN_PLEDGE_DAILY_STAT_DDL = """
CREATE TABLE IF NOT EXISTS `market_pledge_daily_stat`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `total_pledge_ratio` DECIMAL(12,6) DEFAULT NULL COMMENT 'A股质押总比例（单位：%）',
    `pledge_company_count` INT DEFAULT NULL COMMENT '质押公司数量（家）',
    `pledge_record_count` INT DEFAULT NULL COMMENT '质押笔数',
    `total_pledge_shares` DECIMAL(20,4) DEFAULT NULL COMMENT '质押总股数（万股）',
    `total_pledge_market_value` DECIMAL(20,4) DEFAULT NULL COMMENT '质押总市值（万元）',
    `hs300_index` DECIMAL(12,4) DEFAULT NULL COMMENT '沪深300指数收盘价',
    `change_percent` DECIMAL(8,4) DEFAULT NULL COMMENT '涨跌幅（单位：%）',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_trade_date` (`trade_date`),
    KEY `idx_trade_date` (`trade_date`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='上交所融资融券逐日明细')


CREATE_STOCK_CONTINUOUS_STATS_DDL= """
CREATE TABLE IF NOT EXISTS `stock_continuous_stats`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号（排名）',
    `stats_type` VARCHAR(50) DEFAULT NULL  COMMENT '上涨/下跌',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(50) NOT NULL COMMENT '股票简称',
    `stat_date` DATE NOT NULL COMMENT '交易日期（快照日期）',
    `close_price` DECIMAL(10,3) DEFAULT NULL COMMENT '收盘价（元）',
    `high_price` DECIMAL(10,3) DEFAULT NULL COMMENT '最高价（元）',
    `low_price` DECIMAL(10,3) DEFAULT NULL COMMENT '最低价（元）',
    `consecutive_up_days` INT DEFAULT NULL COMMENT '连涨天数',
    `consecutive_up_pct` DECIMAL(10,4) DEFAULT NULL COMMENT '连续涨跌幅（单位：%）',
    `cumulative_turnover_rate` DECIMAL(12,4) DEFAULT NULL COMMENT '累计换手率（单位：%）',
    `industry` VARCHAR(50) DEFAULT NULL COMMENT '所属行业',
 
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date` (`symbol`, `stat_date`),
    KEY `idx_trade_date` (`stat_date`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_serial_number` (`serial_number`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='个股连续上涨/下跌统计（连涨排行）')

CREATE_STOCK_VOLUME_STATS_DDL= """
CREATE TABLE IF NOT EXISTS `stock_volume_stats`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号',
    `volume_type` VARCHAR(50) DEFAULT NULL COMMENT '分类参数（如：放量/缩量）',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(50) NOT NULL COMMENT '股票简称',
    `stat_date` DATE NOT NULL COMMENT '交易日期（快照日期）',
    `change_percent` DECIMAL(8,3) DEFAULT NULL COMMENT '涨跌幅（单位：%）',
    `latest_price` DECIMAL(10,3) DEFAULT NULL COMMENT '最新价（元）',
    `volume` BIGINT DEFAULT NULL COMMENT '成交量（股）',
    `base_volume` BIGINT DEFAULT NULL COMMENT '基准日成交量（股）',
    `surge_days` INT DEFAULT NULL COMMENT '放量天数',
    `shrink_days` INT DEFAULT NULL COMMENT '缩量天数',
    `phase_change` DECIMAL(10,4) DEFAULT NULL COMMENT '阶段涨跌幅（单位：%）',
    `industry` VARCHAR(50) DEFAULT NULL COMMENT '所属行业',
  
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date` (`symbol`, `stat_date`, `volume_type`),
    KEY `idx_trade_date` (`stat_date`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_serial_number` (`serial_number`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='个股放量/缩量统计')


CREATE_STOCK_BREAKTHROUGH_STATS_DDL = """
CREATE TABLE IF NOT EXISTS `stock_breakthrough_stats`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(50) NOT NULL COMMENT '股票简称',
    `stat_date` DATE NOT NULL COMMENT '交易日期（快照日期）',
    `latest_price` DECIMAL(10,3) DEFAULT NULL COMMENT '最新价（元）',
    `amount` DECIMAL(20,3) DEFAULT NULL COMMENT '成交额（元）',
    `volume` BIGINT DEFAULT NULL COMMENT '成交量（股）',
    `change_percent` DECIMAL(8,3) DEFAULT NULL COMMENT '涨跌幅（单位：%）',
    `breakthrough_type` VARCHAR(10) DEFAULT NULL COMMENT '突破类型（向上突破/向下突破）',
    `turnover_rate` DECIMAL(8,3) DEFAULT NULL COMMENT '换手率（单位：%）',
    `ma_period_type` VARCHAR(20) DEFAULT NULL COMMENT '均线周期类型（5日均线/10日均线/20日均线/30日均线/60日均线/90日均线/250日均线/500日均线）',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date` (`symbol`, `stat_date`, `ma_period_type`),
    KEY `idx_stat_date` (`stat_date`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_serial_number` (`serial_number`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='个股突破监测（按均线周期分类的突破信号）')


CREATE_STOCK_VOLUME_PRICE_TREND_STATS_DDL = """
CREATE TABLE IF NOT EXISTS `stock_volume_price_trend_stats`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(50) NOT NULL COMMENT '股票简称',
    `stat_date` DATE NOT NULL COMMENT '交易日期（快照日期）',
    `latest_price` DECIMAL(10,3) DEFAULT NULL COMMENT '最新价（元）',
    `volume_price_up_days` INT DEFAULT NULL COMMENT '量价齐升天数',
    `volume_price_down_days` INT DEFAULT NULL COMMENT '量价齐跌天数',
    `stage_pct_change` DECIMAL(12,4) DEFAULT NULL COMMENT '阶段涨幅（单位：%）',
    `cumulative_turnover_rate` DECIMAL(12,4) DEFAULT NULL COMMENT '累计换手率（单位：%）',
    `industry` VARCHAR(50) DEFAULT NULL COMMENT '所属行业',
    `trend_type` VARCHAR(20) DEFAULT NULL COMMENT '涨跌类型（如：量价齐升、量价齐跌、其他）',


    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date` (`symbol`, `stat_date`, `trend_type`),
    KEY `idx_trade_date` (`stat_date`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_serial_number` (`serial_number`),
    KEY `idx_trend_type` (`trend_type`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='个股量价齐升/齐跌统计')


CREATE_STOCK_ANNOUNCEMENT_HOLDING_DDL = """
CREATE TABLE IF NOT EXISTS `stock_announcement_holding`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号',
    `announce_date` DATE NOT NULL COMMENT '举牌公告日',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(50) NOT NULL COMMENT '股票简称',
    `current_price` DECIMAL(10,3) DEFAULT NULL COMMENT '现价（元）',
    `change_percent` DECIMAL(8,3) DEFAULT NULL COMMENT '涨跌幅（单位：%）',
    `raider_name` VARCHAR(100) DEFAULT NULL COMMENT '举牌方',
    `increase_volume` BIGINT DEFAULT NULL COMMENT '增持数量（股）',
    `avg_price` DECIMAL(10,3) DEFAULT NULL COMMENT '交易均价（元）',
    `increase_ratio` DECIMAL(12,6) DEFAULT NULL COMMENT '增持数量占总股本比例（单位：%）',
    `total_holding` BIGINT DEFAULT NULL COMMENT '变动后持股总数（股）',
    `holding_ratio` DECIMAL(12,6) DEFAULT NULL COMMENT '变动后持股比例（单位：%）',


    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_announce_date` (`symbol`, `announce_date`),
    KEY `idx_announce_date` (`announce_date`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_serial_number` (`serial_number`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='险资举牌')


ALL_MARGIN_DDL_STATEMENTS = [
    CREATE_MARGIN_TRADING_DAILY_STAT_DDL,
    CREATE_MARGIN_TRADING_DAILY_DETAIL_DDL,
    CREATE_MARGIN_PLEDGE_DAILY_STAT_DDL,
    CREATE_STOCK_CONTINUOUS_STATS_DDL,
    CREATE_STOCK_VOLUME_STATS_DDL,
    CREATE_STOCK_BREAKTHROUGH_STATS_DDL,
    CREATE_STOCK_VOLUME_PRICE_TREND_STATS_DDL,
    CREATE_STOCK_ANNOUNCEMENT_HOLDING_DDL,
]