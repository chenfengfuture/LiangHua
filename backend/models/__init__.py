"""
models/ — 量华平台数据库模型包

统一管理所有业务表的结构定义（DDL）、表名映射和 CRUD 工具。

    from models.news_models import insert_news, fetch_news_by_date
    from models.stock_models import fetch_klines, fetch_stocks_info
"""

from models.news_models import (
    batch_update_ai_case,
    fetch_news_by_date,
    insert_news,
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
    # 基础查询函数
    fetch_klines,
    fetch_stocks_info,
    # lhb_detail
    fetch_lhb_detail_by_date,
    fetch_lhb_detail_by_date_range,
    save_lhb_detail_batch,
    # lhb_institution
    fetch_lhb_institution_by_date_range,
    save_lhb_institution_batch,
    # lhb_active_broker
    fetch_lhb_active_broker_by_date_range,
    save_lhb_active_broker_batch,
    # lhb_stock_statistic
    fetch_lhb_stock_statistic_by_range,
    save_lhb_stock_statistic_batch,
    # lhb_broker_detail
    fetch_lhb_broker_detail_by_code,
    save_lhb_broker_detail_batch,
    # holder模块查询函数
    fetch_stock_account_statistics_by_date_range,
    save_stock_account_statistics_batch,
    fetch_stock_comment_by_date,
    save_stock_comment_batch,
    fetch_stock_comment_focus_by_symbol,
    save_stock_comment_focus_batch,
    fetch_stock_comment_desire_by_symbol,
    save_stock_comment_desire_batch,
    fetch_stock_gdhs_all_by_date,
    save_stock_gdhs_all_batch,
    fetch_stock_gdhs_detail_by_symbol,
    save_stock_gdhs_detail_batch,
)

__all__ = [
    # news_models
    "insert_news",
    "fetch_news_by_date",
    "batch_update_ai_case",
    # stock_models
    "fetch_klines",
    "fetch_stocks_info",
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
    # lhb_detail
    "fetch_lhb_detail_by_date",
    "fetch_lhb_detail_by_date_range",
    "save_lhb_detail_batch",
    # lhb_institution
    "fetch_lhb_institution_by_date_range",
    "save_lhb_institution_batch",
    # lhb_active_broker
    "fetch_lhb_active_broker_by_date_range",
    "save_lhb_active_broker_batch",
    # lhb_stock_statistic
    "fetch_lhb_stock_statistic_by_range",
    "save_lhb_stock_statistic_batch",
    # lhb_broker_detail
    "fetch_lhb_broker_detail_by_code",
    "save_lhb_broker_detail_batch",
    # holder模块查询函数
    "fetch_stock_account_statistics_by_date_range",
    "save_stock_account_statistics_batch",
    "fetch_stock_comment_by_date",
    "save_stock_comment_batch",
    "fetch_stock_comment_focus_by_symbol",
    "save_stock_comment_focus_batch",
    "fetch_stock_comment_desire_by_symbol",
    "save_stock_comment_desire_batch",
    "fetch_stock_gdhs_all_by_date",
    "save_stock_gdhs_all_batch",
    "fetch_stock_gdhs_detail_by_symbol",
    "save_stock_gdhs_detail_batch",
]


