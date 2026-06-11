"""
models/ — 量华平台数据库模型包

统一管理所有业务表的结构定义（DDL）、表名映射和 CRUD 工具。

    from models.news_models import insert_news, fetch_news_by_date
    from models.stock_models import fetch_klines, fetch_stocks_info
"""

import logging
import re
from typing import List

from .base import TABLE_COMMON_SUFFIX, COMMON_FIELDS, TABLE_FOOTER_TEMPLATE

# ── stock_models ──────────────────────────────────────────────────
from models.stock_models import (
    CREATE_STOCKS_INFO_DDL,
    CREATE_KLINES_MONTHLY_DDL,
    CREATE_KLINE_INDEX_DDL,
    CREATE_INTRADAY_MINUTES_DDL,
    CREATE_STOCK_DAILY_HISTORY_DDL,
    CREATE_STOCK_ACCOUNT_STATISTICS_DDL,
    CREATE_STOCK_COMMENT_DDL,
    CREATE_STOCK_COMMENT_FOCUS_DDL,
    CREATE_STOCK_COMMENT_DESIRE_DDL,
    CREATE_STOCK_GDHS_ALL_DDL,
    CREATE_STOCK_GDHS_DETAIL_DDL,
    CREATE_XQ_STOCK_INFO_DDL,
    get_conn,
)

# ── stock_info_models ─────────────────────────────────────────────
from models.stock_info_models import CREATE_STOCK_INDIVIDUAL_INFO_DDL

# ── board_models ──────────────────────────────────────────────────
from models.board_models import (
    CREATE_BOARD_CONCEPT_INDEX_DDL,
    CREATE_BOARD_INDUSTRY_INDEX_DDL,
    CREATE_BOARD_INDUSTRY_SUMMARY_DDL,
    CREATE_BOARD_CONCEPT_INFO_DDL,
    CREATE_STOCK_HOT_FOLLOW_DDL,
    CREATE_STOCK_HOT_RANK_DETAIL_DDL,
    CREATE_STOCK_HOT_KEYWORD_DDL,
    CREATE_STOCK_CHANGES_DDL,
    CREATE_BOARD_CHANGE_DDL,
    ALL_BOARD_DDL_STATEMENTS,
)

# ── financial_models ──────────────────────────────────────────────
from models.financial_models import ALL_FINANCIAL_DDL_STATEMENTS

# ── lhb_models ────────────────────────────────────────────────────
from models.lhb_models import ALL_LHB_DDL_STATEMENTS

# ── margin_model ──────────────────────────────────────────────────
from models.margin_model import ALL_MARGIN_DDL_STATEMENTS

# ── indicator_models ──────────────────────────────────────────────
from models.indicator_models import (
    ALL_INDICATOR_DDL_STATEMENTS,
    CREATE_INDICATOR_COMPUTE_LOG_DDL,
)

# ── transaction_models ────────────────────────────────────────────
from models.transaction_models import (
    CREATE_STOCK_TRANSACTION_DDL,
    CREATE_STOCK_HISTORY_TRANSACTION_DDL,
    CREATE_MINUTE_TICK_TABLE_DDL,
    get_minute_tick_ddl,
    get_history_transaction_ddl,
)

# ── news_models ───────────────────────────────────────────────────
from models.news_models import (
    CREATE_NEWS_TABLE_DDL,
    get_news_table_ddl,
)


__all__ = [
    # base 模块
    "TABLE_COMMON_SUFFIX",
    "COMMON_FIELDS",
    "TABLE_FOOTER_TEMPLATE",
    # 统一初始化函数
    "ensure_all_tables",
    # DDL 查询
    "get_ddl_by_table_name",
]


# ═══════════════════════════════════════════════════════════════════
#  统一 DDL 收集
# ═══════════════════════════════════════════════════════════════════

def _collect_all_ddls() -> List[str]:
    """
    收集项目中所有 DDL 语句，供建表和注册表共用。
    消除 ensure_all_tables() 与 build_ddl_registry() 之间的重复。
    """
    all_ddls: List[str] = []

    # 1. 股票基础表
    all_ddls.extend([
        CREATE_STOCKS_INFO_DDL,
        CREATE_KLINES_MONTHLY_DDL,
        CREATE_KLINE_INDEX_DDL,
        CREATE_INTRADAY_MINUTES_DDL,
        CREATE_STOCK_DAILY_HISTORY_DDL,
        CREATE_STOCK_INDIVIDUAL_INFO_DDL,
    ])

    # 2. holder 模块表
    all_ddls.extend([
        CREATE_STOCK_ACCOUNT_STATISTICS_DDL,
        CREATE_STOCK_COMMENT_DDL,
        CREATE_STOCK_COMMENT_FOCUS_DDL,
        CREATE_STOCK_COMMENT_DESIRE_DDL,
        CREATE_STOCK_GDHS_ALL_DDL,
        CREATE_STOCK_GDHS_DETAIL_DDL,
    ])

    # 3. basic 模块表
    all_ddls.append(CREATE_XQ_STOCK_INFO_DDL)

    # 4. 板块表
    all_ddls.extend(ALL_BOARD_DDL_STATEMENTS)

    # 5. 财务表
    all_ddls.extend(ALL_FINANCIAL_DDL_STATEMENTS)

    # 6. 龙虎榜表
    all_ddls.extend(ALL_LHB_DDL_STATEMENTS)

    # 7. 融资融券表
    all_ddls.extend(ALL_MARGIN_DDL_STATEMENTS)

    # 8. 实时分笔成交表
    all_ddls.append(CREATE_STOCK_TRANSACTION_DDL)

    # 9. 技术指标表（含计算状态追踪表）
    all_ddls.extend(ALL_INDICATOR_DDL_STATEMENTS)

    # 10. 新闻表（按月分表模板）
    all_ddls.append(CREATE_NEWS_TABLE_DDL)

    # 11. 分钟 TICK 表（按月分表模板）
    all_ddls.append(CREATE_MINUTE_TICK_TABLE_DDL)

    # 12. 历史分笔成交表（按月分表模板）
    all_ddls.append(CREATE_STOCK_HISTORY_TRANSACTION_DDL)

    return all_ddls


# ═══════════════════════════════════════════════════════════════════
#  统一表创建函数
# ═══════════════════════════════════════════════════════════════════

def ensure_all_tables():
    """
    统一创建所有数据库表（项目启动时自动调用）。

    包含：
    1. 股票基础表（stocks_info 等）
    2. holder 模块表
    3. basic 模块表
    4. 板块概念表
    5. 财务数据表
    6. 龙虎榜表
    7. 融资融券表
    8. 实时分笔成交表
    9. 技术指标表
    10. 新闻表（按月分表模板）
    11. 分钟 TICK 表（按月分表模板）
    12. 历史分笔成交表（按月分表模板）

    返回：创建成功的表数量
    """
    logger = logging.getLogger("models.init")
    all_ddls = _collect_all_ddls()

    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()

        success_count = 0
        error_count = 0

        logger.info(f"开始创建数据库表，共 {len(all_ddls)} 个DDL语句")

        for i, ddl in enumerate(all_ddls, 1):
            # 跳过含模板占位符 { 的 DDL（如 stock_indicators_{year}）
            # 这些分表采用懒建模式，首次写入时自动建表
            if "{" in ddl:
                logger.debug(f"[{i}/{len(all_ddls)}] 跳过模板DDL（含占位符）")
                continue
            try:
                cursor.execute(ddl)
                success_count += 1
                logger.debug(f"[{i}/{len(all_ddls)}] 表创建成功")
            except Exception as e:
                error_count += 1
                if "already exists" in str(e).lower():
                    logger.debug(f"[{i}/{len(all_ddls)}] 表已存在，跳过")
                else:
                    logger.warning(f"[{i}/{len(all_ddls)}] 表创建失败: {e}")

        conn.commit()

        logger.info(
            f"数据库表创建完成: 成功 {success_count} 个, "
            f"失败 {error_count} 个, 总计 {len(all_ddls)} 个"
        )

        return {
            "success": True,
            "total": len(all_ddls),
            "created": success_count,
            "errors": error_count,
            "message": f"数据库表创建完成: 成功 {success_count} 个, 失败 {error_count} 个",
        }

    except Exception as e:
        logger.error(f"数据库表创建过程中发生异常: {e}")
        if conn:
            conn.rollback()
        return {
            "success": False,
            "total": len(all_ddls),
            "created": 0,
            "errors": len(all_ddls),
            "message": f"数据库表创建失败: {e}",
        }
    finally:
        if conn:
            conn.close()


# ═══════════════════════════════════════════════════════════════════
#  全局 DDL 注册表（table_name → DDL）
# ═══════════════════════════════════════════════════════════════════

_DDL_REGISTRY: dict = {}
_DDL_REGISTRY_BUILT = False


def build_ddl_registry() -> dict:
    """
    从所有 DDL 语句中提取表名并构建 {table_name: ddl} 注册表。
    结果被缓存，仅在模块重载时重新构建。
    """
    global _DDL_REGISTRY, _DDL_REGISTRY_BUILT
    if _DDL_REGISTRY_BUILT:
        return _DDL_REGISTRY

    all_ddls = _collect_all_ddls()

    # 解析 DDL 提取表名
    _DDL_REGISTRY = {}
    for ddl in all_ddls:
        m = re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?(\w+)`?", ddl, re.IGNORECASE)
        if m:
            tbl = m.group(1)
            # 跳过以 { 结尾的模板（如 stock_indicators_{year}）
            if "{" in tbl:
                continue
            _DDL_REGISTRY[tbl] = ddl

    _DDL_REGISTRY_BUILT = True
    return _DDL_REGISTRY


def get_ddl_by_table_name(table_name: str) -> str | None:
    """
    根据表名查找对应的 DDL 语句。
    先查精确匹配，再查前缀匹配（用于 news_xxx_YYMM 分表）。
    """
    registry = build_ddl_registry()

    # 1. 精确匹配
    if table_name in registry:
        return registry[table_name]

    # 2. 前缀匹配：news_ 表按 news_xxx 前缀查找
    if table_name.startswith("news_"):
        return get_news_table_ddl(table_name)

    # 3. 前缀匹配：minute_ticks_ 表（按月分表）
    if table_name.startswith("minute_ticks_"):
        return get_minute_tick_ddl(table_name)

    # 4. 前缀匹配：stock_history_transactions_ 表（按月分表）
    if table_name.startswith("stock_history_transactions_"):
        return get_history_transaction_ddl(table_name)

    return None
