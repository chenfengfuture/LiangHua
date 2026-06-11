"""
models/board_models.py — 板块概念相关数据库模型 & DDL

管理板块概念相关数据表的结构定义：
  1. board_concept_index       — 概念板块指数日频率数据
  2. board_industry_index      — 行业板块指数日频率数据
  3. board_industry_summary    — 行业一览表
  4. board_concept_info        — 概念板块简介
  5. stock_hot_follow          — 雪球关注排行榜
  6. stock_hot_rank_detail     — 股票热度历史趋势及粉丝特征
  7. stock_hot_keyword         — 个股人气榜热门关键词
  8. stock_changes             — 盘口异动数据
  9. board_change              — 当日板块异动详情

所有表使用统一的创建时间和更新时间字段。
"""

from .base import TABLE_COMMON_SUFFIX

# ═══════════════════════════════════════════════════════════════════
#  1. board_concept_index — 概念板块指数日频率数据
# ═══════════════════════════════════════════════════════════════════

CREATE_BOARD_CONCEPT_INDEX_DDL = """
CREATE TABLE IF NOT EXISTS `board_concept_index` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `concept_name` VARCHAR(100) NOT NULL COMMENT '概念板块名称',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `open_price` DECIMAL(12,4) DEFAULT NULL COMMENT '开盘价',
    `high_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最高价',
    `low_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最低价',
    `close_price` DECIMAL(12,4) DEFAULT NULL COMMENT '收盘价',
    `volume` BIGINT DEFAULT NULL COMMENT '成交量(手)',
    `amount` DECIMAL(20,4) DEFAULT NULL COMMENT '成交额(万元)',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `change_amount` DECIMAL(12,4) DEFAULT NULL COMMENT '涨跌额',
    `amplitude` DECIMAL(10,4) DEFAULT NULL COMMENT '振幅(%)',
    `turnover_rate` DECIMAL(10,4) DEFAULT NULL COMMENT '换手率(%)',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_concept_date` (`concept_name`, `trade_date`),
    INDEX `idx_trade_date` (`trade_date`),
    INDEX `idx_concept_name` (`concept_name`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='概念板块指数日频率数据')

# ═══════════════════════════════════════════════════════════════════
#  2. board_industry_index — 行业板块指数日频率数据
# ═══════════════════════════════════════════════════════════════════

CREATE_BOARD_INDUSTRY_INDEX_DDL = """
CREATE TABLE IF NOT EXISTS `board_industry_index` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `industry_name` VARCHAR(100) NOT NULL COMMENT '行业板块名称',
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `open_price` DECIMAL(12,4) DEFAULT NULL COMMENT '开盘价',
    `high_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最高价',
    `low_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最低价',
    `close_price` DECIMAL(12,4) DEFAULT NULL COMMENT '收盘价',
    `volume` BIGINT DEFAULT NULL COMMENT '成交量(手)',
    `amount` DECIMAL(20,4) DEFAULT NULL COMMENT '成交额(万元)',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `change_amount` DECIMAL(12,4) DEFAULT NULL COMMENT '涨跌额',
    `amplitude` DECIMAL(10,4) DEFAULT NULL COMMENT '振幅(%)',
    `turnover_rate` DECIMAL(10,4) DEFAULT NULL COMMENT '换手率(%)',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_industry_date` (`industry_name`, `trade_date`),
    INDEX `idx_trade_date` (`trade_date`),
    INDEX `idx_industry_name` (`industry_name`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='行业板块指数日频率数据')

# ═══════════════════════════════════════════════════════════════════
#  3. board_industry_summary — 行业一览表
# ═══════════════════════════════════════════════════════════════════

CREATE_BOARD_INDUSTRY_SUMMARY_DDL = """
CREATE TABLE IF NOT EXISTS `board_industry_summary` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `serial_number` INT DEFAULT NULL COMMENT '序号',
    `board_name` VARCHAR(100) NOT NULL COMMENT '板块名称',
    `board_code` VARCHAR(20) DEFAULT NULL COMMENT '板块代码（同花顺内部代码）',
    `change_percent` VARCHAR(20) DEFAULT NULL COMMENT '涨跌幅(%)',
    `total_volume` DECIMAL(20,4) DEFAULT NULL COMMENT '总成交量(万手)',
    `total_amount` DECIMAL(20,4) DEFAULT NULL COMMENT '总成交额(亿元)',
    `net_inflow` DECIMAL(20,4) DEFAULT NULL COMMENT '净流入(亿元)',
    `rise_count` DECIMAL(12,4) DEFAULT NULL COMMENT '上涨家数',
    `fall_count` DECIMAL(12,4) DEFAULT NULL COMMENT '下跌家数',
    `avg_price` DECIMAL(12,4) DEFAULT NULL COMMENT '均价',
    `leading_stock` VARCHAR(20) DEFAULT NULL COMMENT '领涨股代码',
    `leading_stock_name` VARCHAR(100) DEFAULT NULL COMMENT '领涨股',
    `leading_stock_price` VARCHAR(20) DEFAULT NULL COMMENT '领涨股-最新价',
    `leading_stock_change` VARCHAR(20) DEFAULT NULL COMMENT '领涨股-涨跌幅(%)',
    
    `stat_date` DATE DEFAULT NULL COMMENT '统计日期',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_board_date` (`board_name`, `stat_date`, `board_code`),
    INDEX `idx_stat_date` (`stat_date`),
    INDEX `idx_board_name` (`board_name`),
    INDEX `idx_board_code` (`board_code`),
    INDEX `idx_serial_number` (`serial_number`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='行业板块数据')

# ═══════════════════════════════════════════════════════════════════
#  4. board_concept_info — 概念板块简介
# ═══════════════════════════════════════════════════════════════════

CREATE_BOARD_CONCEPT_INFO_DDL = """
CREATE TABLE IF NOT EXISTS `board_concept_info` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `concept_code` VARCHAR(20) NOT NULL COMMENT '概念代码',
    `concept_name` VARCHAR(100) NOT NULL COMMENT '概念名称',
    `introduction` TEXT COMMENT '概念简介',
    `related_stocks` TEXT COMMENT '相关股票(逗号分隔)',
    `stock_count` INT DEFAULT NULL COMMENT '相关股票数量',
    `total_market_cap` DECIMAL(20,4) DEFAULT NULL COMMENT '总市值(亿元)',
    `main_companies` TEXT COMMENT '主要公司',
    `hot_level` VARCHAR(20) DEFAULT NULL COMMENT '热度级别',
    `trend_direction` VARCHAR(20) DEFAULT NULL COMMENT '趋势方向', 
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_concept_code` (`concept_code`),
    UNIQUE KEY `uk_concept_name` (`concept_name`),
    INDEX `idx_hot_level` (`hot_level`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='概念板块简介')

# ═══════════════════════════════════════════════════════════════════
#  5. stock_hot_follow — 雪球关注排行榜
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCK_HOT_FOLLOW_DDL = """
CREATE TABLE IF NOT EXISTS `stock_hot_follow` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `hot_type` VARCHAR(20) NOT NULL DEFAULT '雪球' COMMENT '热度来源',
    `rank_date` VARCHAR(20) NOT NULL DEFAULT '' COMMENT '统计日期',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(100) DEFAULT NULL COMMENT '股票名称',
    `latest_price` DECIMAL(18,2) DEFAULT NULL COMMENT '最新价',

    -- 关注榜
    `follow_rank` INT DEFAULT NULL COMMENT '关注排名',
    `follow_count` DECIMAL(18,2) DEFAULT NULL COMMENT '关注人数',
    `follow_score` DECIMAL(10,4) DEFAULT NULL COMMENT '关注热度得分',

    -- 交易榜
    `trade_rank` INT DEFAULT NULL COMMENT '交易排名',
    `trade_count` DECIMAL(18,2) DEFAULT NULL COMMENT '交易关注人数',
    `trade_score` DECIMAL(10,4) DEFAULT NULL COMMENT '交易热度得分',

    -- 讨论榜
    `discuss_rank` INT DEFAULT NULL COMMENT '讨论排名',
    `discuss_count` DECIMAL(18,2) DEFAULT NULL COMMENT '讨论关注人数',
    `discuss_score` DECIMAL(10,4) DEFAULT NULL COMMENT '讨论热度得分',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date` (`rank_date`,`symbol`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_rank_date` (`rank_date`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='热度榜单')

# ═══════════════════════════════════════════════════════════════════
#  6. stock_hot_rank_detail — 股票热度历史趋势及粉丝特征
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCK_HOT_RANK_DETAIL_DDL = """
CREATE TABLE IF NOT EXISTS `stock_hot_rank_detail` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `stat_date` DATE NOT NULL COMMENT '统计日期',
    `hot_score` DECIMAL(10,4) DEFAULT NULL COMMENT '热度得分',
    `search_count` INT DEFAULT NULL COMMENT '搜索次数',
    `discussion_count` INT DEFAULT NULL COMMENT '讨论次数',
    `read_count` INT DEFAULT NULL COMMENT '阅读次数',
    `follower_count` INT DEFAULT NULL COMMENT '粉丝数量',
    `follower_increase` INT DEFAULT NULL COMMENT '粉丝增长',
    `male_ratio` DECIMAL(5,2) DEFAULT NULL COMMENT '男性比例(%)',
    `female_ratio` DECIMAL(5,2) DEFAULT NULL COMMENT '女性比例(%)',
    `age_distribution` VARCHAR(200) DEFAULT NULL COMMENT '年龄分布',
    `region_distribution` TEXT COMMENT '地区分布',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date` (`symbol`, `stat_date`),
    INDEX `idx_stat_date` (`stat_date`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_hot_score` (`hot_score`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='股票热度历史趋势及粉丝特征')

# ═══════════════════════════════════════════════════════════════════
#  7. stock_hot_keyword — 个股人气榜热门关键词
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCK_HOT_KEYWORD_DDL = """
CREATE TABLE IF NOT EXISTS `stock_hot_keyword` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `stat_date` DATE NOT NULL COMMENT '统计日期',
    `keyword` VARCHAR(100) DEFAULT NULL COMMENT '热门关键词',
    `search_count` INT DEFAULT NULL COMMENT '搜索次数',
    `mention_count` INT DEFAULT NULL COMMENT '提及次数',
    `heat_score` DECIMAL(10,4) DEFAULT NULL COMMENT '热度得分',
    `rank_position` INT DEFAULT NULL COMMENT '排名位置',
    `trend` VARCHAR(20) DEFAULT NULL COMMENT '趋势: 上升/下降/持平',
    `concept_name` VARCHAR(100) DEFAULT NULL COMMENT '概念名称',
    `concept_code` VARCHAR(20) DEFAULT NULL COMMENT '概念代码',
    `heat` INT DEFAULT NULL COMMENT '热度（整型，与heat_score可并存）',
    
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date_keyword` (`symbol`, `stat_date`, `keyword`),
    INDEX `idx_stat_date` (`stat_date`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_keyword` (`keyword`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='个股人气榜热门关键词')

# ═══════════════════════════════════════════════════════════════════
#  8. stock_changes — 盘口异动数据
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCK_CHANGES_DDL = """
CREATE TABLE IF NOT EXISTS `stock_changes` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `change_type` VARCHAR(50) NOT NULL COMMENT '异动类型: 火箭发射/快速反弹/大笔买入等',
    `stat_date` DATETIME DEFAULT NULL COMMENT '发生日期',
    `occur_time` DATETIME NOT NULL COMMENT '发生时间',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(100) DEFAULT NULL COMMENT '股票名称',
    `price` DECIMAL(12,4) DEFAULT NULL COMMENT '当前价格',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `volume` BIGINT DEFAULT NULL COMMENT '成交量(手)',
    `amount` DECIMAL(20,4) DEFAULT NULL COMMENT '成交额(万元)',
    `change_reason` VARCHAR(200) DEFAULT NULL COMMENT '异动原因',
    `strength_level` VARCHAR(20) DEFAULT NULL COMMENT '强度级别',
    `raw_info` VARCHAR(200) DEFAULT NULL COMMENT '字段原始数据',
    `description` VARCHAR(200) DEFAULT NULL COMMENT '异常说明',
    
    
    PRIMARY KEY (`id`),
    INDEX `idx_occur_time` (`occur_time`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_change_type` (`change_type`),
    INDEX `idx_change_type_time` (`change_type`, `occur_time`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='盘口异动数据')

# ═══════════════════════════════════════════════════════════════════
#  9. board_change — 当日板块异动详情
# ═══════════════════════════════════════════════════════════════════

CREATE_BOARD_CHANGE_DDL = """
CREATE TABLE IF NOT EXISTS `board_change` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `change_date` DATE NOT NULL COMMENT '异动日期',
    `board_name` VARCHAR(100) NOT NULL COMMENT '板块名称',
    `change_direction` VARCHAR(20) DEFAULT NULL COMMENT '异动方向: 上涨/下跌',
    `main_net_inflow` DECIMAL(20,4) DEFAULT NULL COMMENT '主力净流入(万元)',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `leader_stock` VARCHAR(20) DEFAULT NULL COMMENT '领涨/领跌股票',
    `leader_name` VARCHAR(100) DEFAULT NULL COMMENT '领涨/领跌股票名称',
    `leader_change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '领涨/领跌幅(%)',
    `total_change_count` INT DEFAULT NULL COMMENT '板块异动总次数',
    `most_frequent_stock_code` VARCHAR(20) DEFAULT NULL COMMENT '板块异动最频繁个股代码',
    `most_frequent_stock_name` VARCHAR(100) DEFAULT NULL COMMENT '板块异动最频繁个股名称',
    `most_frequent_trade_direction` VARCHAR(20) DEFAULT NULL COMMENT '买卖方向',
    `change_type_list` TEXT COMMENT '板块具体异动类型列表及出现次数(JSON)',
    `total_volume` BIGINT DEFAULT NULL COMMENT '总成交量(手)',
    `total_amount` DECIMAL(20,4) DEFAULT NULL COMMENT '总成交额(万元)',
    `rise_count` INT DEFAULT NULL COMMENT '上涨家数',
    `fall_count` INT DEFAULT NULL COMMENT '下跌家数',
    `change_reason` TEXT COMMENT '异动原因分析',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date_type_name` (`change_date`, `board_name`),
    INDEX `idx_change_date` (`change_date`),
    INDEX `idx_board_name` (`board_name`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='当日板块异动详情')

# ═══════════════════════════════════════════════════════════════════
#  9. stock_zt_pool — 涨停板行情
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCK_ZT_POOL_DDL = """
CREATE TABLE IF NOT EXISTS `stock_zt_pool`(
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `stat_date` DATE NOT NULL COMMENT '交易日期（查询日期）',
    `serial_number` INT DEFAULT NULL COMMENT '序号',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(100) DEFAULT NULL COMMENT '股票名称',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅（%）',
    `latest_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最新价',
    `amount` DECIMAL(20,4) DEFAULT NULL COMMENT '成交额（元）',
    `circulating_market_cap` DECIMAL(20,4) DEFAULT NULL COMMENT '流通市值（元）',
    `total_market_cap` DECIMAL(20,4) DEFAULT NULL COMMENT '总市值（元）',
    `turnover_rate` DECIMAL(12,4) DEFAULT NULL COMMENT '换手率（%）',
    `limit_fund` DECIMAL(20,4) DEFAULT NULL COMMENT '封板资金（元）',
    `first_limit_time` VARCHAR(10) DEFAULT NULL COMMENT '首次封板时间（HHMMSS）',
    `last_limit_time` VARCHAR(10) DEFAULT NULL COMMENT '最后封板时间（HHMMSS）',
    `open_count` INT DEFAULT NULL COMMENT '炸板次数',
    `limit_statistic` VARCHAR(20) DEFAULT NULL COMMENT '涨停统计（如1/1）',
    `limit_times` INT DEFAULT NULL COMMENT '连板数',
    `industry` VARCHAR(100) DEFAULT NULL COMMENT '所属行业',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date_code` (`stat_date`, `symbol`, `name`),
    INDEX `idx_trade_date` (`stat_date`),
    INDEX `idx_stock_symbol` (`symbol`),
    INDEX `idx_stock_name` (`name`),
    INDEX `idx_limit_times` (`limit_times`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='涨停板行情')


# ═══════════════════════════════════════════════════════════════════
#  9. stock_zt_pool_previous — 昨日涨停板行情
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCK_ZT_POOL_PREVIOUS_DDL = """
CREATE TABLE IF NOT EXISTS `stock_zt_pool_previous` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `stat_date` DATE NOT NULL COMMENT '观察日（即接口传入的date，T日）',
    `serial_number` INT DEFAULT NULL COMMENT '序号',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(100) DEFAULT NULL COMMENT '股票名称',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '今日涨跌幅（%）',
    `latest_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最新价',
    `limit_up_price` DECIMAL(12,4) DEFAULT NULL COMMENT '涨停价',
    `amount` DECIMAL(20,4) DEFAULT NULL COMMENT '成交额（元）',
    `circulating_market_cap` DECIMAL(20,4) DEFAULT NULL COMMENT '流通市值（元）',
    `total_market_cap` DECIMAL(20,4) DEFAULT NULL COMMENT '总市值（元）',
    `turnover_rate` DECIMAL(12,4) DEFAULT NULL COMMENT '换手率（%）',
    `speed` DECIMAL(8,4) DEFAULT NULL COMMENT '涨速（%）',
    `amplitude` DECIMAL(10,4) DEFAULT NULL COMMENT '振幅（%）',
    `prev_limit_time` TIME DEFAULT NULL COMMENT '昨日封板时间（格式 HH:MM:SS）',
    `prev_limit_times` INT DEFAULT NULL COMMENT '昨日连板数（1为首板）',
    `limit_statistic` VARCHAR(20) DEFAULT NULL COMMENT '涨停统计（如1/1）',
    `industry` VARCHAR(100) DEFAULT NULL COMMENT '所属行业',
  
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_obs_date_code` (`stat_date`, `symbol`, `name`),
    INDEX `idx_stat_date` (`stat_date`),
    INDEX `idx_stock_symbol` (`symbol`),
    INDEX `idx_prev_limit_times` (`prev_limit_times`),
    INDEX `idx_stock_name` (`name`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='昨日涨停股池（T-1日涨停股在T日的表现数据）')

# ═══════════════════════════════════════════════════════════════════
#  9. stock_zt_pool_strong — 昨日涨停板行情
# ═══════════════════════════════════════════════════════════════════


CREATE_STOCK_ZT_POOL_STRONG_DDL = """
CREATE TABLE IF NOT EXISTS `stock_zt_pool_strong` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `stat_date` DATE NOT NULL COMMENT '观察日期（接口传入的date，T日）',
    `serial_number` INT DEFAULT NULL COMMENT '序号',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(100) DEFAULT NULL COMMENT '股票名称',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅（%）',
    `latest_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最新价',
    `limit_up_price` DECIMAL(12,4) DEFAULT NULL COMMENT '涨停价',
    `amount` DECIMAL(20,4) DEFAULT NULL COMMENT '成交额（元）',
    `circulating_market_cap` DECIMAL(20,4) DEFAULT NULL COMMENT '流通市值（元）',
    `total_market_cap` DECIMAL(20,4) DEFAULT NULL COMMENT '总市值（元）',
    `turnover_rate` DECIMAL(12,4) DEFAULT NULL COMMENT '换手率（%）',
    `speed` DECIMAL(8,4) DEFAULT NULL COMMENT '涨速（%）',
    `is_new_high` VARCHAR(4) DEFAULT NULL COMMENT '是否新高（是/否）',
    `volume_ratio` DECIMAL(10,4) DEFAULT NULL COMMENT '量比',
    `limit_statistic` VARCHAR(20) DEFAULT NULL COMMENT '涨停统计（如1/1）',
    `selection_reason` VARCHAR(200) DEFAULT NULL COMMENT '入选理由（如60日新高）',
    `industry` VARCHAR(100) DEFAULT NULL COMMENT '所属行业',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stat_date_symbol` (`stat_date`, `symbol`),
    INDEX `idx_stat_date` (`stat_date`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_is_new_high` (`is_new_high`),
    INDEX `idx_change_percent` (`change_percent`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='强势股池每日数据')


# ═══════════════════════════════════════════════════════════════════
#  9. stock_zt_pool_zbgc — 炸板股池
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCK_ZT_POOL_ZBGC_DDL = """
CREATE TABLE IF NOT EXISTS `stock_zt_pool_zbgc` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `stat_date` DATE NOT NULL COMMENT '交易日期（接口传入的date，T日）',
    `serial_number` INT DEFAULT NULL COMMENT '序号',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(100) DEFAULT NULL COMMENT '股票名称',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅（%）',
    `latest_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最新价',
    `limit_up_price` DECIMAL(12,4) DEFAULT NULL COMMENT '涨停价',
    `amount` DECIMAL(20,4) DEFAULT NULL COMMENT '成交额（元）',
    `circulating_market_cap` DECIMAL(20,4) DEFAULT NULL COMMENT '流通市值（元）',
    `total_market_cap` DECIMAL(20,4) DEFAULT NULL COMMENT '总市值（元）',
    `turnover_rate` DECIMAL(12,4) DEFAULT NULL COMMENT '换手率（%）',
    `speed` DECIMAL(8,4) DEFAULT NULL COMMENT '涨速（%）',
    `first_limit_time` TIME DEFAULT NULL COMMENT '首次封板时间',
    `open_count` INT DEFAULT NULL COMMENT '炸板次数',
    `limit_statistic` VARCHAR(20) DEFAULT NULL COMMENT '涨停统计（如1/1）',
    `amplitude` DECIMAL(10,4) DEFAULT NULL COMMENT '振幅（%）',
    `industry` VARCHAR(100) DEFAULT NULL COMMENT '所属行业',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stat_date_symbol` (`stat_date`, `symbol`),
    INDEX `idx_stat_date` (`stat_date`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_change_percent` (`change_percent`),
    INDEX `idx_first_limit_time` (`first_limit_time`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='涨停板行情-炸板股池')

# ═══════════════════════════════════════════════════════════════════
#  stock_zt_pool_dtgc_em 跌停股池每日数据
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCK_ZT_POOL_DTGC_DDL = """
CREATE TABLE IF NOT EXISTS `stock_zt_pool_dtgc` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `stat_date` DATE NOT NULL COMMENT '交易日期（接口传入的date，T日）',
    `serial_number` INT DEFAULT NULL COMMENT '序号',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(100) DEFAULT NULL COMMENT '股票名称',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅（%，负值表示跌停）',
    `latest_price` DECIMAL(12,4) DEFAULT NULL COMMENT '最新价',
    `turnover` DECIMAL(20,4) DEFAULT NULL COMMENT '成交额（元）',
    `circulating_market_cap` DECIMAL(20,4) DEFAULT NULL COMMENT '流通市值（元）',
    `total_market_cap` DECIMAL(20,4) DEFAULT NULL COMMENT '总市值（元）',
    `pe_ttm` DECIMAL(12,4) DEFAULT NULL COMMENT '动态市盈率',
    `turnover_rate` DECIMAL(12,4) DEFAULT NULL COMMENT '换手率（%）',
    `limit_fund` DECIMAL(20,4) DEFAULT NULL COMMENT '封单资金（元）',
    `last_limit_time` TIME DEFAULT NULL COMMENT '最后封板时间',
    `limit_turnover` DECIMAL(20,4) DEFAULT NULL COMMENT '板上成交额（元）',
    `continuous_limit_down` INT DEFAULT NULL COMMENT '连续跌停天数',
    `open_count` INT DEFAULT NULL COMMENT '开板次数',
    `industry` VARCHAR(100) DEFAULT NULL COMMENT '所属行业',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stat_date_symbol` (`stat_date`, `symbol`),
    INDEX `idx_stat_date` (`stat_date`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_continuous_limit_down` (`continuous_limit_down`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='跌停股池每日数据')


# ═══════════════════════════════════════════════════════════════════
#  板块成份股表（board_cons — 东方财富成份股数据）
# ═══════════════════════════════════════════════════════════════════

CREATE_BOARD_INDUSTRY_CONS_DDL = """
CREATE TABLE IF NOT EXISTS `board_industry_cons` (
    `symbol`              VARCHAR(20)   NOT NULL                   COMMENT '股票代码',
    `name`                VARCHAR(100)  DEFAULT NULL               COMMENT '股票名称',
    `latest_price`        DECIMAL(20,4) DEFAULT NULL               COMMENT '最新价',
    `change_percent`      DECIMAL(10,4) DEFAULT NULL               COMMENT '涨跌幅',
    `main_net_inflow`     DECIMAL(30,2) DEFAULT NULL               COMMENT '主力净流入',
    `main_net_inflow_pct` DECIMAL(10,4) DEFAULT NULL               COMMENT '主力净流入占比',
    `super_large_net_inflow`     DECIMAL(30,2) DEFAULT NULL        COMMENT '超大单净流入',
    `super_large_net_inflow_pct` DECIMAL(10,4) DEFAULT NULL        COMMENT '超大单净流入占比',
    `large_net_inflow`          DECIMAL(30,2) DEFAULT NULL        COMMENT '大单净流入',
    `large_net_inflow_pct`      DECIMAL(10,4) DEFAULT NULL        COMMENT '大单净流入占比',
    `medium_net_inflow`         DECIMAL(30,2) DEFAULT NULL        COMMENT '中单净流入',
    `medium_net_inflow_pct`     DECIMAL(10,4) DEFAULT NULL        COMMENT '中单净流入占比',
    `small_net_inflow`          DECIMAL(30,2) DEFAULT NULL        COMMENT '小单净流入',
    `small_net_inflow_pct`      DECIMAL(10,4) DEFAULT NULL        COMMENT '小单净流入占比',
    `board_name`          VARCHAR(50)   NOT NULL                   COMMENT '板块名称',
    `board_type`          VARCHAR(20)   DEFAULT '行业'             COMMENT '板块类型(行业/概念)',
    PRIMARY KEY (`symbol`, `board_name`),
    INDEX idx_board_name (`board_name`),
    INDEX idx_board_type (`board_type`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='行业板块成份股表')

CREATE_BOARD_CONCEPT_CONS_DDL = """
CREATE TABLE IF NOT EXISTS `board_concept_cons` (
    `symbol`              VARCHAR(20)   NOT NULL                   COMMENT '股票代码',
    `name`                VARCHAR(100)  DEFAULT NULL               COMMENT '股票名称',
    `latest_price`        DECIMAL(20,4) DEFAULT NULL               COMMENT '最新价',
    `change_percent`      DECIMAL(10,4) DEFAULT NULL               COMMENT '涨跌幅',
    `main_net_inflow`     DECIMAL(30,2) DEFAULT NULL               COMMENT '主力净流入',
    `main_net_inflow_pct` DECIMAL(10,4) DEFAULT NULL               COMMENT '主力净流入占比',
    `super_large_net_inflow`     DECIMAL(30,2) DEFAULT NULL        COMMENT '超大单净流入',
    `super_large_net_inflow_pct` DECIMAL(10,4) DEFAULT NULL        COMMENT '超大单净流入占比',
    `large_net_inflow`          DECIMAL(30,2) DEFAULT NULL        COMMENT '大单净流入',
    `large_net_inflow_pct`      DECIMAL(10,4) DEFAULT NULL        COMMENT '大单净流入占比',
    `medium_net_inflow`         DECIMAL(30,2) DEFAULT NULL        COMMENT '中单净流入',
    `medium_net_inflow_pct`     DECIMAL(10,4) DEFAULT NULL        COMMENT '中单净流入占比',
    `small_net_inflow`          DECIMAL(30,2) DEFAULT NULL        COMMENT '小单净流入',
    `small_net_inflow_pct`      DECIMAL(10,4) DEFAULT NULL        COMMENT '小单净流入占比',
    `board_name`          VARCHAR(50)   NOT NULL                   COMMENT '板块名称',
    `board_type`          VARCHAR(20)   DEFAULT '概念'             COMMENT '板块类型(行业/概念)',
    PRIMARY KEY (`symbol`, `board_name`),
    INDEX idx_board_name (`board_name`),
    INDEX idx_board_type (`board_type`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='概念板块成份股表')


# ═══════════════════════════════════════════════════════════════════
#  所有DDL语句集合
# ═══════════════════════════════════════════════════════════════════

ALL_BOARD_DDL_STATEMENTS = [
    CREATE_BOARD_CONCEPT_INDEX_DDL,
    CREATE_BOARD_INDUSTRY_INDEX_DDL,
    CREATE_BOARD_INDUSTRY_SUMMARY_DDL,
    CREATE_BOARD_CONCEPT_INFO_DDL,
    CREATE_STOCK_HOT_FOLLOW_DDL,
    CREATE_STOCK_HOT_RANK_DETAIL_DDL,
    CREATE_STOCK_HOT_KEYWORD_DDL,
    CREATE_STOCK_CHANGES_DDL,
    CREATE_BOARD_CHANGE_DDL,
    CREATE_STOCK_ZT_POOL_DDL,
    CREATE_STOCK_ZT_POOL_PREVIOUS_DDL,
    CREATE_STOCK_ZT_POOL_STRONG_DDL,
    CREATE_STOCK_ZT_POOL_ZBGC_DDL,
    CREATE_STOCK_ZT_POOL_DTGC_DDL,
    CREATE_BOARD_INDUSTRY_CONS_DDL,
    CREATE_BOARD_CONCEPT_CONS_DDL,
]