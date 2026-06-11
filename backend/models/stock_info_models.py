"""
models/stock_info_models.py — 个股信息数据表 DDL

表: stock_individual_info — 东方财富个股详细信息缓存
"""

from .base import TABLE_COMMON_SUFFIX

# ═══════════════════════════════════════════════════════════════════
#  个股信息表（东方财富 stock_individual_info_em 接口缓存）
# ═══════════════════════════════════════════════════════════════════

CREATE_STOCK_INDIVIDUAL_INFO_DDL = """
CREATE TABLE IF NOT EXISTS `stock_individual_info` (
    `symbol`            VARCHAR(10)   NOT NULL                COMMENT '股票代码',
    `name`              VARCHAR(100)  DEFAULT NULL            COMMENT '股票简称',
    `total_shares`      DECIMAL(30,2) DEFAULT NULL            COMMENT '总股本',
    `float_shares`      DECIMAL(30,2) DEFAULT NULL            COMMENT '流通股',
    `industry`          VARCHAR(100)  DEFAULT NULL            COMMENT '行业',
    `total_market_cap`  DECIMAL(30,2) DEFAULT NULL            COMMENT '总市值',
    `float_market_cap`  DECIMAL(30,2) DEFAULT NULL            COMMENT '流通市值',
    `listing_date`      VARCHAR(20)   DEFAULT NULL            COMMENT '上市日期',
    `latest_price`      DECIMAL(20,4) DEFAULT NULL            COMMENT '最新价',
    PRIMARY KEY (`symbol`),
    KEY `idx_industry` (`industry`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='东方财富个股详细信息')
