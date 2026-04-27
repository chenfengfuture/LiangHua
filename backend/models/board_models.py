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
    
    `stat_date` DATE NOT NULL COMMENT '统计日期',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_board_date` (`board_name`, `stat_date`),
    INDEX `idx_stat_date` (`stat_date`),
    INDEX `idx_board_name` (`board_name`),
    INDEX `idx_serial_number` (`serial_number`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='行业一览表数据')

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
    `rank_type` VARCHAR(20) NOT NULL COMMENT '排行榜类型: 本周新增/最热门',
    `hot_type` VARCHAR(20) DEFAULT NULL COMMENT '热度来源, 雪球',
    `rank_date` VARCHAR(20) DEFAULT NULL COMMENT '排名日期',
    `rank_position` INT NOT NULL COMMENT '排名位置',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(100) DEFAULT NULL COMMENT '股票名称',
    `follow_count` INT DEFAULT NULL COMMENT '关注人数',
    `follow_increase` INT DEFAULT NULL COMMENT '关注增长数',
    `discussion_count` INT DEFAULT NULL COMMENT '讨论数',
    `heat_score` DECIMAL(10,4) DEFAULT NULL COMMENT '热度得分',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_type_date_position` (`rank_type`, `rank_date`, `symbol`, `hot_type`),
    INDEX `idx_rank_date` (`rank_date`),
    INDEX `idx_symbol` (`symbol`),
    INDEX `idx_rank_type` (`rank_type`),
    INDEX `idx_hot_type` (`hot_type`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='雪球关注排行榜')



# ═══════════════════════════════════════════════════════════════════
#  6. stock_hot_rank_detail — 股票热度历史趋势及粉丝特征
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCK_HOT_RANK_DETAIL_DDL = """
CREATE TABLE IF NOT EXISTS `stock_hot_rank_detail` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `stat_date` DATE NOT NULL COMMENT '统计日期',
    `hot_rank` INT DEFAULT NULL COMMENT '热度排名',
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
    INDEX `idx_hot_rank` (`hot_rank`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='股票热度历史趋势及粉丝特征')

# ═══════════════════════════════════════════════════════════════════
#  7. stock_hot_keyword — 个股人气榜热门关键词
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCK_HOT_KEYWORD_DDL = """
CREATE TABLE IF NOT EXISTS `stock_hot_keyword` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `stat_date` DATE NOT NULL COMMENT '统计日期',
    `keyword` VARCHAR(100) NOT NULL COMMENT '热门关键词',
    `search_count` INT DEFAULT NULL COMMENT '搜索次数',
    `mention_count` INT DEFAULT NULL COMMENT '提及次数',
    `heat_score` DECIMAL(10,4) DEFAULT NULL COMMENT '热度得分',
    `rank_position` INT DEFAULT NULL COMMENT '排名位置',
    `trend` VARCHAR(20) DEFAULT NULL COMMENT '趋势: 上升/下降/持平',
    
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
    `occur_time` DATETIME NOT NULL COMMENT '发生时间',
    `symbol` VARCHAR(20) NOT NULL COMMENT '股票代码',
    `name` VARCHAR(100) DEFAULT NULL COMMENT '股票名称',
    `current_price` DECIMAL(12,4) DEFAULT NULL COMMENT '当前价格',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `volume` BIGINT DEFAULT NULL COMMENT '成交量(手)',
    `amount` DECIMAL(20,4) DEFAULT NULL COMMENT '成交额(万元)',
    `change_reason` VARCHAR(200) DEFAULT NULL COMMENT '异动原因',
    `strength_level` VARCHAR(20) DEFAULT NULL COMMENT '强度级别',
    
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
    `board_type` VARCHAR(20) NOT NULL COMMENT '板块类型: 概念/行业',
    `board_name` VARCHAR(100) NOT NULL COMMENT '板块名称',
    `change_direction` VARCHAR(20) NOT NULL COMMENT '异动方向: 上涨/下跌',
    `change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '涨跌幅(%)',
    `leader_stock` VARCHAR(20) DEFAULT NULL COMMENT '领涨/领跌股票',
    `leader_name` VARCHAR(100) DEFAULT NULL COMMENT '领涨/领跌股票名称',
    `leader_change_percent` DECIMAL(10,4) DEFAULT NULL COMMENT '领涨/领跌幅(%)',
    `total_volume` BIGINT DEFAULT NULL COMMENT '总成交量(手)',
    `total_amount` DECIMAL(20,4) DEFAULT NULL COMMENT '总成交额(万元)',
    `rise_count` INT DEFAULT NULL COMMENT '上涨家数',
    `fall_count` INT DEFAULT NULL COMMENT '下跌家数',
    `change_reason` TEXT COMMENT '异动原因分析',
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_date_type_name` (`change_date`, `board_type`, `board_name`),
    INDEX `idx_change_date` (`change_date`),
    INDEX `idx_board_type` (`board_type`),
    INDEX `idx_change_direction` (`change_direction`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='当日板块异动详情')

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
    CREATE_BOARD_CHANGE_DDL
]