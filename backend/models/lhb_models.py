from .base import TABLE_COMMON_SUFFIX

CREATE_STOCK_STOCK_DETAIL_DATE_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_stock_detail_date`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(50) DEFAULT NULL COMMENT '股票代码',
    `trade_date` DATE NOT NULL COMMENT '上榜日期',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date` (`symbol`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_name` (`name`),
    KEY `idx_serial_number` (`serial_number`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='个股龙虎榜日期')

# ═══════════════════════════════════════════════════════════════════
#  龙虎榜机构买卖每日统计
# ═══════════════════════════════════════════════════════════════════
CREATE_STOCK_INSTITUTION_TRADING_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_institution_trading`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(50) NOT NULL COMMENT '股票名称',
    `close_price` DECIMAL(10,3) DEFAULT NULL COMMENT '收盘价',
    `change_percent` DECIMAL(8,3) DEFAULT NULL COMMENT '涨跌幅（单位：%）',
    `buy_institution_count` INT DEFAULT NULL COMMENT '买方机构数',
    `sell_institution_count` INT DEFAULT NULL COMMENT '卖方机构数',
    `institution_buy_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '机构买入总额（元）',
    `institution_sell_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '机构卖出总额（元）',
    `institution_net_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '机构买入净额（元）',
    `total_trade_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '市场总成交额（元）',
    `institution_net_ratio` DECIMAL(10,6) DEFAULT NULL COMMENT '机构净买额占总成交额比（单位：%）',
    `turnover_rate` DECIMAL(8,3) DEFAULT NULL COMMENT '换手率（单位：%）',
    `circulating_market_cap` DECIMAL(15,3) DEFAULT NULL COMMENT '流通市值（亿元）',
    `reason` VARCHAR(200) DEFAULT NULL COMMENT '上榜原因',
    `trade_date` DATE NOT NULL COMMENT '上榜日期',
    `start_date` DATE NOT NULL COMMENT '开始时间',
    `end_date` DATE NOT NULL COMMENT '结束时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date` (`symbol`, `trade_date`, `start_date`, `end_date`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_name` (`name`),
    KEY `idx_serial_number` (`serial_number`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='龙虎榜机构买卖每日统计')


CREATE_LHB_BROKER_LEAGUE_STAT_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_broker_league_stat`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号',
    `broker_name` VARCHAR(100) NOT NULL COMMENT '营业部名称（含一线游资等标签）',
    `total_lhb_times` INT DEFAULT NULL COMMENT '上榜次数',
    `total_fund_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '合计动用资金（元）',
    `year_total_times` INT DEFAULT NULL COMMENT '年内上榜次数',
    `year_buy_stock_count` INT DEFAULT NULL COMMENT '年内买入股票只数',
    `year_3d_success_rate` DECIMAL(8,4) DEFAULT NULL COMMENT '年内3日跟买成功率（单位：%）',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_broker_date_type` (`broker_name`),
    KEY `idx_broker_name` (`broker_name`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='龙虎榜机上榜次数最多')



# ═══════════════════════════════════════════════════════════════════
#  龙虎榜详情查询接口
# ═══════════════════════════════════════════════════════════════════

CREATE_LHB_DETAIL_EM_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_detail_em`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(50) NOT NULL COMMENT '股票名称',
    `trade_date` DATE NOT NULL COMMENT '上榜日期',
    `interpretation` VARCHAR(300) DEFAULT NULL COMMENT '解读（包含机构数量、成功率等）',
    `close_price` DECIMAL(10,3) DEFAULT NULL COMMENT '收盘价',
    `change_percent` DECIMAL(8,4) DEFAULT NULL COMMENT '涨跌幅（单位：%）',
    `lhb_net_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '龙虎榜净买额（元）',
    `lhb_buy_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '龙虎榜买入额（元）',
    `lhb_sell_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '龙虎榜卖出额（元）',
    `lhb_turnover_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '龙虎榜成交额（元）',
    `total_trade_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '市场总成交额（元）',
    `net_amount_ratio` DECIMAL(10,6) DEFAULT NULL COMMENT '净买额占总成交比（单位：%）',
    `turnover_ratio` DECIMAL(10,6) DEFAULT NULL COMMENT '成交额占总成交比（单位：%）',
    `turnover_rate` DECIMAL(8,3) DEFAULT NULL COMMENT '换手率（单位：%）',
    `circulating_market_cap` DECIMAL(15,3) DEFAULT NULL COMMENT '流通市值（元）',
    `reason` VARCHAR(200) DEFAULT NULL COMMENT '上榜原因',
    `after_1d_pct_change` DECIMAL(8,4) DEFAULT NULL COMMENT '上榜后1日涨跌幅（单位：%）',
    `after_2d_pct_change` DECIMAL(8,4) DEFAULT NULL COMMENT '上榜后2日涨跌幅（单位：%）',
    `after_5d_pct_change` DECIMAL(8,4) DEFAULT NULL COMMENT '上榜后5日涨跌幅（单位：%）',
    `after_10d_pct_change` DECIMAL(8,4) DEFAULT NULL COMMENT '上榜后10日涨跌幅（单位：%）',
    `start_date` DATE NOT NULL COMMENT '开始时间',
    `end_date` DATE NOT NULL COMMENT '结束时间',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date` (`symbol`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_serial_number` (`serial_number`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='龙虎榜详情')

CREATE_LHB_DRAGON_TIGER_SUMMARY_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_dragon_tiger_summary`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(50) NOT NULL COMMENT '股票名称',
    `data_type` VARCHAR(50) NOT NULL COMMENT '：数据周期类型',
    `latest_trade_date` DATE NOT NULL COMMENT '最近上榜日',
    `close_price` DECIMAL(10,3) DEFAULT NULL COMMENT '收盘价',
    `change_percent` DECIMAL(8,4) DEFAULT NULL COMMENT '涨跌幅（单位：%）',
    `total_lhb_times` INT DEFAULT NULL COMMENT '上榜次数',
    `lhb_net_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '龙虎榜净买额（元）',
    `lhb_buy_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '龙虎榜买入额（元）',
    `lhb_sell_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '龙虎榜卖出额（元）',
    `lhb_total_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '龙虎榜总成交额（元）',
    `buy_institution_times` INT DEFAULT NULL COMMENT '买方机构次数',
    `sell_institution_times` INT DEFAULT NULL COMMENT '卖方机构次数',
    `institution_net_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '机构买入净额（元）',
    `institution_buy_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '机构买入总额（元）',
    `institution_sell_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '机构卖出总额（元）',
    `pct_change_1m` DECIMAL(12,4) DEFAULT NULL COMMENT '近1个月涨跌幅（单位：%）',
    `pct_change_3m` DECIMAL(12,4) DEFAULT NULL COMMENT '近3个月涨跌幅（单位：%）',
    `pct_change_6m` DECIMAL(12,4) DEFAULT NULL COMMENT '近6个月涨跌幅（单位：%）',
    `pct_change_1y` DECIMAL(12,4) DEFAULT NULL COMMENT '近1年涨跌幅（单位：%）',

    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date` (`symbol`, `latest_trade_date`, `data_type`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_data_type` (`data_type`),
    KEY `idx_latest_trade_date` (`latest_trade_date`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='个股上榜统计')

CREATE_LHB_BROKER_DAILY_STAT_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_broker_daily_stat`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号',
    `broker_name` VARCHAR(100) NOT NULL COMMENT '营业部名称',
    `trade_date` DATE NOT NULL COMMENT '上榜日',
    `buy_stock_count` INT DEFAULT NULL COMMENT '买入个股数',
    `sell_stock_count` INT DEFAULT NULL COMMENT '卖出个股数',
    `total_buy_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '买入总金额（元）',
    `total_sell_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '卖出总金额（元）',
    `net_buy_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '总买卖净额（元）',
    `buy_stocks` TEXT DEFAULT NULL COMMENT '买入股票列表（原始空格分隔）',
    `broker_code` VARCHAR(20) DEFAULT NULL COMMENT '营业部代码',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_broker_date` (`broker_name`, `trade_date`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_broker_name` (`broker_name`),
    KEY `idx_net_buy_amount` (`net_buy_amount`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='每日活跃营业部')




CREATE_LHB_BROKER_PERFORMANCE_STAT_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_broker_performance_stat`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号',
    `broker_name` VARCHAR(100) NOT NULL COMMENT '营业部名称',
    `data_type` VARCHAR(50) NOT NULL DEFAULT '综合统计' COMMENT '数据周期类型（预留扩展）',
    `buy_count_1d` INT DEFAULT NULL COMMENT '上榜后1天-买入次数',
    `avg_return_1d` DECIMAL(16,10) DEFAULT NULL COMMENT '上榜后1天-平均涨幅（单位：%）',
    `up_prob_1d` DECIMAL(16,10) DEFAULT NULL COMMENT '上榜后1天-上涨概率（单位：%）',
    `buy_count_2d` INT DEFAULT NULL COMMENT '上榜后2天-买入次数',
    `avg_return_2d` DECIMAL(16,10) DEFAULT NULL COMMENT '上榜后2天-平均涨幅（单位：%）',
    `up_prob_2d` DECIMAL(16,10) DEFAULT NULL COMMENT '上榜后2天-上涨概率（单位：%）',
    `buy_count_3d` INT DEFAULT NULL COMMENT '上榜后3天-买入次数',
    `avg_return_3d` DECIMAL(16,10) DEFAULT NULL COMMENT '上榜后3天-平均涨幅（单位：%）',
    `up_prob_3d` DECIMAL(16,10) DEFAULT NULL COMMENT '上榜后3天-上涨概率（单位：%）',
    `buy_count_5d` INT DEFAULT NULL COMMENT '上榜后5天-买入次数',
    `avg_return_5d` DECIMAL(16,10) DEFAULT NULL COMMENT '上榜后5天-平均涨幅（单位：%）',
    `up_prob_5d` DECIMAL(16,10) DEFAULT NULL COMMENT '上榜后5天-上涨概率（单位：%）',
    `buy_count_10d` INT DEFAULT NULL COMMENT '上榜后10天-买入次数',
    `avg_return_10d` DECIMAL(16,10) DEFAULT NULL COMMENT '上榜后10天-平均涨幅（单位：%）',
    `up_prob_10d` DECIMAL(16,10) DEFAULT NULL COMMENT '上榜后10天-上涨概率（单位：%）',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_broker_date_type` (`broker_name`, `data_type`),
    KEY `idx_broker_name` (`broker_name`),
    KEY `idx_data_type` (`data_type`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='龙虎榜单-营业部排行')


CREATE_LHB_BROKER_SUMMARY_STAT_DDL = """
CREATE TABLE IF NOT EXISTS `lhb_broker_summary_stat`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `serial_number` INT NOT NULL COMMENT '序号',
    `broker_name` VARCHAR(100) NOT NULL COMMENT '营业部名称',
    `data_type` VARCHAR(50) NOT NULL DEFAULT '综合统计' COMMENT '数据周期类型（如：综合统计/月度/季度）',
    `total_lhb_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '龙虎榜成交金额（元）',
    `total_lhb_times` INT DEFAULT NULL COMMENT '上榜次数',
    `total_buy_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '买入总额（元）',
    `total_buy_times` INT DEFAULT NULL COMMENT '买入次数',
    `total_sell_amount` DECIMAL(20,3) DEFAULT NULL COMMENT '卖出总额（元）',
    `total_sell_times` INT DEFAULT NULL COMMENT '卖出次数',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_broker_date_type` (`broker_name`, `data_type`),
    KEY `idx_broker_name` (`broker_name`),
    KEY `idx_total_lhb_amount` (`total_lhb_amount`),
    KEY `idx_total_lhb_times` (`total_lhb_times`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='营业部-龙虎榜综合统计')



# ═══════════════════════════════════════════════════════════════════
#  所有DDL语句集合
# ═══════════════════════════════════════════════════════════════════

ALL_LHB_DDL_STATEMENTS = [
    CREATE_STOCK_STOCK_DETAIL_DATE_DDL,
    CREATE_STOCK_INSTITUTION_TRADING_DDL,
    CREATE_LHB_DETAIL_EM_DDL,
    CREATE_LHB_DRAGON_TIGER_SUMMARY_DDL,
    CREATE_LHB_BROKER_DAILY_STAT_DDL,
    CREATE_LHB_BROKER_PERFORMANCE_STAT_DDL,
    CREATE_LHB_BROKER_SUMMARY_STAT_DDL,
    CREATE_LHB_BROKER_LEAGUE_STAT_DDL,
]