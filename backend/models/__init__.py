"""
models/ — 量华平台数据库模型包

统一管理所有业务表的结构定义（DDL）、表名映射和 CRUD 工具。

    from models.news_models import insert_news, fetch_news_by_date
    from models.stock_models import fetch_klines, fetch_stocks_info
"""

import logging
from typing import List

from .base import TABLE_COMMON_SUFFIX, COMMON_FIELDS, TABLE_FOOTER_TEMPLATE
from models.news_models import (
    batch_update_ai_case,
    CREATE_NEWS_TABLE_DDL,
)
from models.stock_models import (
    CREATE_STOCKS_INFO_DDL,
    CREATE_LHB_DETAIL_DDL,
    CREATE_LHB_INSTITUTION_DDL,
    CREATE_LHB_ACTIVE_BROKER_DDL,
    CREATE_LHB_STOCK_STATISTIC_DDL,
    CREATE_LHB_BROKER_DETAIL_DDL,
    # holder模块DDL
    CREATE_STOCK_ACCOUNT_STATISTICS_DDL,
    CREATE_STOCK_COMMENT_DDL,
    CREATE_STOCK_COMMENT_FOCUS_DDL,
    CREATE_STOCK_COMMENT_DESIRE_DDL,
    CREATE_STOCK_GDHS_ALL_DDL,
    CREATE_STOCK_GDHS_DETAIL_DDL,
    # basic模块DDL
    CREATE_XQ_STOCK_INFO_DDL,
    CREATE_STOCK_INFO_JSON_DDL,
    # 其他DDL
    CREATE_KLINES_MONTHLY_DDL,
    CREATE_KLINE_INDEX_DDL,
    CREATE_INTRADAY_MINUTES_DDL,
    get_conn,
)

# 尝试导入board_models，如果存在则包含

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

__all__ = [
    # base 模块
    "TABLE_COMMON_SUFFIX",
    "COMMON_FIELDS",
    "TABLE_FOOTER_TEMPLATE",
    # news_models
    "batch_update_ai_case",
    "CREATE_NEWS_TABLE_DDL",
    # stock_models
    "CREATE_STOCKS_INFO_DDL",
    "CREATE_LHB_DETAIL_DDL",
    "CREATE_LHB_INSTITUTION_DDL",
    "CREATE_LHB_ACTIVE_BROKER_DDL",
    "CREATE_LHB_STOCK_STATISTIC_DDL",
    "CREATE_LHB_BROKER_DETAIL_DDL",
    # holder模块DDL
    "CREATE_STOCK_ACCOUNT_STATISTICS_DDL",
    "CREATE_STOCK_COMMENT_DDL",
    "CREATE_STOCK_COMMENT_FOCUS_DDL",
    "CREATE_STOCK_COMMENT_DESIRE_DDL",
    "CREATE_STOCK_GDHS_ALL_DDL",
    "CREATE_STOCK_GDHS_DETAIL_DDL",
    # basic模块DDL
    "CREATE_XQ_STOCK_INFO_DDL",
    "CREATE_STOCK_INFO_JSON_DDL",
    # 其他DDL
    "CREATE_KLINES_MONTHLY_DDL",
    "CREATE_KLINE_INDEX_DDL",
    "CREATE_INTRADAY_MINUTES_DDL",
    # board_models DDL（如果可用）
    "CREATE_BOARD_CONCEPT_INDEX_DDL",
    "CREATE_BOARD_INDUSTRY_INDEX_DDL",
    "CREATE_BOARD_INDUSTRY_SUMMARY_DDL",
    "CREATE_BOARD_CONCEPT_INFO_DDL",
    "CREATE_STOCK_HOT_FOLLOW_DDL",
    "CREATE_STOCK_HOT_RANK_DETAIL_DDL",
    "CREATE_STOCK_HOT_KEYWORD_DDL",
    "CREATE_STOCK_CHANGES_DDL",
    "CREATE_BOARD_CHANGE_DDL",
    "ALL_BOARD_DDL_STATEMENTS",
    # 统一初始化函数
    "ensure_all_tables",
]


# ═══════════════════════════════════════════════════════════════════
#  统一表创建函数
# ═══════════════════════════════════════════════════════════════════

def ensure_all_tables():
    """
    统一创建所有数据库表（项目启动时自动调用）
    
    包含：
    1. 股票基础表（stocks_info等）
    2. holder模块表
    3. basic模块表
    4. 新闻表（按月分表）
    5. 板块概念表（如果board_models存在）
    
    返回：创建成功的表数量
    """
    logger = logging.getLogger("models.init")
    
    # 收集所有DDL语句
    all_ddls: List[str] = []
    
    # 1. 股票基础表
    stock_base_ddls = [
        CREATE_STOCKS_INFO_DDL,
        CREATE_KLINES_MONTHLY_DDL,
        CREATE_KLINE_INDEX_DDL,
        CREATE_INTRADAY_MINUTES_DDL,
        CREATE_LHB_DETAIL_DDL,
    ]
    all_ddls.extend(stock_base_ddls)
    
    # 2. holder模块表
    holder_ddls = [
        CREATE_STOCK_ACCOUNT_STATISTICS_DDL,
        CREATE_STOCK_COMMENT_DDL,
        CREATE_STOCK_COMMENT_FOCUS_DDL,
        CREATE_STOCK_COMMENT_DESIRE_DDL,
        CREATE_STOCK_GDHS_ALL_DDL,
        CREATE_STOCK_GDHS_DETAIL_DDL,
    ]
    all_ddls.extend(holder_ddls)
    
    # 3. basic模块表
    basic_ddls = [
        CREATE_XQ_STOCK_INFO_DDL,
        CREATE_STOCK_INFO_JSON_DDL,
    ]
    all_ddls.extend(basic_ddls)
    
    # 4. 板块概念表（如果可用）
    all_ddls.extend(ALL_BOARD_DDL_STATEMENTS)

    
    # 5. 新闻表（按月分表，需要特殊处理）
    # 新闻表在首次插入数据时会自动创建，这里不包含在批量创建中
    
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        
        success_count = 0
        error_count = 0
        
        logger.info(f"开始创建数据库表，共 {len(all_ddls)} 个DDL语句")
        
        for i, ddl in enumerate(all_ddls, 1):
            try:
                cursor.execute(ddl)
                success_count += 1
                logger.debug(f"[{i}/{len(all_ddls)}] 表创建成功")
            except Exception as e:
                error_count += 1
                # 如果是表已存在的错误，忽略
                if "already exists" in str(e).lower() or "table already exists" in str(e).lower():
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
            "message": f"数据库表创建完成: 成功 {success_count} 个, 失败 {error_count} 个"
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
            "message": f"数据库表创建失败: {e}"
        }
    finally:
        if conn:
            conn.close()


