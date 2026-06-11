"""
models/indicator_models.py — 技术指标数据表（DDL，按年分表）+ 计算状态追踪表

表名: stock_indicators.stock_indicators_{YYYY}，跨库存储，按年分表。
采用懒建模式：首次写入时自动建表（参考 mootdx/table_helper.py）。
"""

import logging
import threading

from utils.db import get_conn
from models.base import TABLE_COMMON_SUFFIX

log = logging.getLogger("indicator_models")

# ─── 常量 ─────────────────────────────────────────────────────────

# 指标表目标数据库
INDICATOR_DB_NAME = "stock_indicators"

# 年份范围
INDICATOR_YEAR_MIN = 2023   # 最早有数据的年份
INDICATOR_YEAR_MAX = 2030   # 预留上限

# 进程内已建表缓存 + 线程锁
_ensured_indicator_years = set()
_ensure_indicator_lock = threading.Lock()


# ─── 工具函数 ─────────────────────────────────────────────────────

def get_indicator_table_name(year: int) -> str:
    """
    返回指标分年表的完整限定名（含库名）。

    例: 2026 -> "stock_indicators.stock_indicators_2026"
    """
    return f"{INDICATOR_DB_NAME}.stock_indicators_{year}"


def ensure_indicator_year_table(year: int) -> bool:
    """
    确保 stock_indicators.stock_indicators_{year} 表存在（按需懒建）。

    使用 CREATE_INDICATORS_TABLE_DDL_TPL 模板渲染 + CREATE TABLE IF NOT EXISTS。
    幂等，重复调用安全。首次执行时若 stock_indicators 库不存在，会先 CREATE DATABASE。

    Args:
        year: 年份，必须在 [INDICATOR_YEAR_MIN, INDICATOR_YEAR_MAX]

    Returns:
        True 建表成功/已存在；False 失败
    """
    if not isinstance(year, int):
        try:
            year = int(year)
        except (ValueError, TypeError):
            log.error(f"[indicator_models] year 不是整数: {year}")
            return False

    if year < INDICATOR_YEAR_MIN or year > INDICATOR_YEAR_MAX:
        log.error(f"[indicator_models] year 越界 [{INDICATOR_YEAR_MIN}, {INDICATOR_YEAR_MAX}]: {year}")
        return False

    # 进程内缓存命中
    if year in _ensured_indicator_years:
        return True

    with _ensure_indicator_lock:
        if year in _ensured_indicator_years:
            return True

        try:
            ddl = CREATE_INDICATORS_TABLE_DDL_TPL.format(
                year=year,
                table_comment=f'技术指标数据表（{year}年）',
            )
        except Exception as e:
            log.error(f"[indicator_models] DDL 渲染失败 year={year}: {e}")
            return False

        conn = get_conn()
        try:
            with conn.cursor() as cur:
                # 1. 先确保目标库存在
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{INDICATOR_DB_NAME}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                # 2. 建表（DDL 已含库名前缀）
                cur.execute(ddl)
            conn.commit()
            _ensured_indicator_years.add(year)
            log.info(f"[indicator_models] 表已就绪: {INDICATOR_DB_NAME}.stock_indicators_{year}")
            return True
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            log.error(f"[indicator_models] 建表失败 {INDICATOR_DB_NAME}.stock_indicators_{year}: {e}")
            return False
        finally:
            try:
                conn.close()
            except Exception:
                pass


# ─── DDL 模板 ─────────────────────────────────────────────────────



CREATE_WATCHLIST_DYNAMIC_DDL = """
CREATE TABLE IF NOT EXISTS `stock_indicators`.`watchlist_dynamic` (
    `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    `serial_number` INT NOT NULL COMMENT '自选股自定义排序序号',
    `symbol` VARCHAR(10) NOT NULL COMMENT '股票代码（如 600519）',
    `name` VARCHAR(50) DEFAULT NULL COMMENT '股票名称',

    -- ========== 板块归属字段（按同花顺口径）==========
    `industry_sector` VARCHAR(100) DEFAULT NULL COMMENT '所属同花顺行业板块（一级行业分类，如"银行"）',
    `concept_sectors` VARCHAR(500) DEFAULT NULL COMMENT '所属概念板块（多值逗号分隔，如"新能源车,人工智能"）',
    `region_sector` VARCHAR(100) DEFAULT NULL COMMENT '所属地域板块（如"广东"）',
    `style_sector` VARCHAR(200) DEFAULT NULL COMMENT '所属风格板块（多值逗号分隔，如同花顺风格指数板块，如"大盘股,绩优股"）',
    `custom_sectors` VARCHAR(500) DEFAULT NULL COMMENT '用户自定义板块归属（多值逗号分隔）',
    `main_sector_tag` VARCHAR(50) DEFAULT NULL COMMENT '当前主导板块（用于策略判断的核心板块）',

    -- ========== 量化选股核心字段 ==========
    `trade_date` DATE NOT NULL COMMENT '入选日期',
    `expire_date` DATE DEFAULT NULL COMMENT '失效日期（到期自动移出）',
    `strategy_name` VARCHAR(50) DEFAULT NULL COMMENT '策略名称（如 dll_l2_momentum）',
    `factor_score` DECIMAL(10,4) DEFAULT NULL COMMENT '综合因子得分（加权后）',
    `factor_rank` SMALLINT DEFAULT NULL COMMENT '当日全市场排名（1~N）',
    `in_reason` VARCHAR(200) DEFAULT NULL COMMENT '入选理由（突破/金叉/事件触发等）',

    -- ========== 备注字段 ==========
    `remarks` TEXT COMMENT '综合备注（Free-Text，记录基本面分析、操作计划、特殊事件等）',

    -- ========== 同花顺特色扩展字段 ==========
    `major_business` VARCHAR(500) DEFAULT NULL COMMENT '主营业务（从同花顺F10提取）',
    `shareholder_features` VARCHAR(200) DEFAULT NULL COMMENT '股东特征（如"社保重仓""QFII持股""机构扎堆"）',
    `performance_summary` VARCHAR(200) DEFAULT NULL COMMENT '业绩概况（如"预增""扭亏为盈"）',
    `price_strength` VARCHAR(50) DEFAULT NULL COMMENT '股价强度（如"强势股""弱势股""盘整中"）',
    `liquidity_level` VARCHAR(50) DEFAULT NULL COMMENT '流动性评级（如"高流动性""低换手"）',
    `tags` VARCHAR(100) DEFAULT NULL COMMENT '快捷标签（涨停/放量/机构净买/连板）',
    `market_cap` DECIMAL(20,4) DEFAULT NULL COMMENT '总市值（亿元）',
    `pe_ttm` DECIMAL(12,4) DEFAULT NULL COMMENT '滚动市盈率',
    `turnover_rate` DECIMAL(10,4) DEFAULT NULL COMMENT '换手率（%）',

    -- ========== 风控与状态字段 ==========
    `status` TINYINT DEFAULT 1 COMMENT '状态：0-已移出，1-持有观察，2-重点关注',
    `last_check_date` DATE DEFAULT NULL COMMENT '最近一次符合条件校验日期',

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_symbol_date_strategy` (`symbol`, `trade_date`, `strategy_name`),
    KEY `idx_trade_date` (`trade_date`),
    KEY `idx_symbol` (`symbol`),
    KEY `idx_strategy_name` (`strategy_name`),
    KEY `idx_status` (`status`),
    KEY `idx_expire_date` (`expire_date`),
    KEY `idx_factor_rank` (`factor_rank`),
    KEY `idx_industry_sector` (`industry_sector`),
    KEY `idx_region_sector` (`region_sector`),
    KEY `idx_main_sector_tag` (`main_sector_tag`),
""" + TABLE_COMMON_SUFFIX.format(table_comment='动态自选股池')


# 分表DDL模板（{year} 和 {table_comment} 由 ensure_indicator_year_table 代入）
CREATE_INDICATORS_TABLE_DDL_TPL = """
CREATE TABLE IF NOT EXISTS `stock_indicators`.`stock_indicators_{year}` (
    symbol        VARCHAR(10)    NOT NULL  COMMENT '股票代码',
    trade_date    DATE           NOT NULL  COMMENT '交易日',

    -- 移动均线
    ma_5          DECIMAL(12,4)  DEFAULT NULL COMMENT '5日均线',
    ma_10         DECIMAL(12,4)  DEFAULT NULL COMMENT '10日均线',
    ma_20         DECIMAL(12,4)  DEFAULT NULL COMMENT '20日均线',
    ma_60         DECIMAL(12,4)  DEFAULT NULL COMMENT '60日均线',
    ma_120        DECIMAL(12,4)  DEFAULT NULL COMMENT '120日均线',
    ma_250        DECIMAL(12,4)  DEFAULT NULL COMMENT '250日均线',

    -- 布林带
    boll_ma       DECIMAL(12,4)  DEFAULT NULL COMMENT '布林中轨(MA20)',
    boll_upper    DECIMAL(12,4)  DEFAULT NULL COMMENT '布林上轨',
    boll_lower    DECIMAL(12,4)  DEFAULT NULL COMMENT '布林下轨',
    boll_width    DECIMAL(10,4)  DEFAULT NULL COMMENT '布林带宽%',

    -- SAR
    sar           DECIMAL(12,4)  DEFAULT NULL COMMENT '抛物线转向SAR',

    -- 成交量均线
    vol           DECIMAL(20,2)  DEFAULT NULL COMMENT '成交量(手)',
    vol_ma_5      DECIMAL(20,2)  DEFAULT NULL COMMENT '5日均量',
    vol_ma_10     DECIMAL(20,2)  DEFAULT NULL COMMENT '10日均量',
    vol_ma_20     DECIMAL(20,2)  DEFAULT NULL COMMENT '20日均量',

    -- MACD
    macd_dif      DECIMAL(10,4)  DEFAULT NULL COMMENT 'DIF快线',
    macd_dea      DECIMAL(10,4)  DEFAULT NULL COMMENT 'DEA慢线',
    macd_bar      DECIMAL(10,4)  DEFAULT NULL COMMENT 'MACD柱',

    -- KDJ
    kdj_k         DECIMAL(10,4)  DEFAULT NULL COMMENT 'K值',
    kdj_d         DECIMAL(10,4)  DEFAULT NULL COMMENT 'D值',
    kdj_j         DECIMAL(10,4)  DEFAULT NULL COMMENT 'J值',

    -- RSI
    rsi_6         DECIMAL(10,4)  DEFAULT NULL COMMENT 'RSI(6)',
    rsi_12        DECIMAL(10,4)  DEFAULT NULL COMMENT 'RSI(12)',
    rsi_24        DECIMAL(10,4)  DEFAULT NULL COMMENT 'RSI(24)',

    -- 威廉指标
    wr_6          DECIMAL(10,4)  DEFAULT NULL COMMENT 'WR(6)',
    wr_10         DECIMAL(10,4)  DEFAULT NULL COMMENT 'WR(10)',
    wr_14         DECIMAL(10,4)  DEFAULT NULL COMMENT 'WR(14)',

    -- CCI
    cci           DECIMAL(12,4)  DEFAULT NULL COMMENT 'CCI(14)',

    -- 乖离率
    bias_6        DECIMAL(10,4)  DEFAULT NULL COMMENT 'BIAS(6)%',
    bias_12       DECIMAL(10,4)  DEFAULT NULL COMMENT 'BIAS(12)%',
    bias_24       DECIMAL(10,4)  DEFAULT NULL COMMENT 'BIAS(24)%',

    -- 心理线
    psy_12        DECIMAL(10,4)  DEFAULT NULL COMMENT 'PSY(12)',
    psy_24        DECIMAL(10,4)  DEFAULT NULL COMMENT 'PSY(24)',
    psy_ma_12     DECIMAL(10,4)  DEFAULT NULL COMMENT 'PSYMA(12)',
    psy_ma_24     DECIMAL(10,4)  DEFAULT NULL COMMENT 'PSYMA(24)',

    -- OBV
    obv           DECIMAL(30,2)  DEFAULT NULL COMMENT '能量潮OBV',
    obv_ma        DECIMAL(30,2)  DEFAULT NULL COMMENT 'OBV均线MA20',

    -- DMI
    pdi           DECIMAL(10,4)  DEFAULT NULL COMMENT 'PDI(+DI)',
    mdi           DECIMAL(10,4)  DEFAULT NULL COMMENT 'MDI(-DI)',
    adx           DECIMAL(10,4)  DEFAULT NULL COMMENT 'ADX',
    adxr          DECIMAL(10,4)  DEFAULT NULL COMMENT 'ADXR',

    -- ROC
    roc           DECIMAL(12,4)  DEFAULT NULL COMMENT 'ROC(12)%',
    roc_ma        DECIMAL(12,4)  DEFAULT NULL COMMENT 'ROCMA(6)%',

    -- 版本号
    indicator_version VARCHAR(10) DEFAULT 'v1' COMMENT '指标参数版本号',

    -- 唯一索引
    UNIQUE KEY uk_symbol_date (symbol, trade_date),
    KEY idx_symbol (symbol),
    KEY idx_trade_date (trade_date),
""" + TABLE_COMMON_SUFFIX


# ── 指标计算状态追踪表 ─────────────────────────────────────────────

CREATE_INDICATOR_COMPUTE_LOG_DDL = """
CREATE TABLE IF NOT EXISTS `stock_indicators`.`indicator_compute_log` (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    symbol        VARCHAR(10)    NOT NULL  COMMENT '股票代码',
    trade_date    DATE           NOT NULL  COMMENT '交易日',
    status        ENUM('pending','done','failed') NOT NULL DEFAULT 'pending' COMMENT '计算状态',
    error_msg     TEXT           DEFAULT NULL COMMENT '失败原因',
    computed_at   DATETIME       DEFAULT NULL COMMENT '计算完成时间',
    UNIQUE KEY uk_symbol_date (symbol, trade_date),
    KEY idx_status (status),
    KEY idx_trade_date (trade_date),
""" + TABLE_COMMON_SUFFIX.format(table_comment='指标计算状态追踪表')


ALL_INDICATOR_DDL_STATEMENTS = [
    CREATE_INDICATOR_COMPUTE_LOG_DDL,
    CREATE_INDICATORS_TABLE_DDL_TPL,
    CREATE_WATCHLIST_DYNAMIC_DDL
]