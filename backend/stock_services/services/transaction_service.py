"""
stock_services/services/transaction_service.py — 分笔成交 Service 层

继承 BaseStockService，使用 execute_cached_fetch 模板方法实现
Redis → DB → mootdx 三级缓存查询。
"""

from typing import Dict, Any

from stock_services.services.basic_services import BaseStockService
from stock_services.unity import get_transaction, get_history_transaction
from stock_services.common.logging import get_module_logger

logger = get_module_logger("transaction_service")

REDIS_TTL_TRANSACTION = 15              # 实时分笔缓存 15 秒
REDIS_TTL_HISTORY_TRANSACTION = 7200    # 历史分笔 Redis 缓存 2 小时
DB_TTL_HISTORY_TRANSACTION = 365        # 历史分笔 DB 缓存 365 天
MAX_TRANSACTION_OFFSET = 1000           # 分笔成交单次最大拉取数量
DEFAULT_HISTORY_RETENTION_DAYS = 30     # 历史分笔默认保留 30 天

TRANSACTION_TABLE_NAME = "stock_transactions"
HISTORY_TRANSACTION_TABLE_PREFIX = "stock_history_transactions_"


class TransactionService(BaseStockService):
    """分笔成交服务。"""

    def __init__(self, service_name: str = "TransactionService"):
        super().__init__(service_name=service_name)

    def get_service_info(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "description": "mootdx 分笔成交服务",
            "tables": [TRANSACTION_TABLE_NAME, f"{HISTORY_TRANSACTION_TABLE_PREFIX}YYYYMM"],
        }

    def get_transaction(
        self,
        symbol: str,
        start: int = 0,
        offset: int = 800,
        async_write: bool = True,
        persist: bool = False,
        read_from_db: bool = False,
    ) -> Dict[str, Any]:
        """查询实时分笔成交。默认仅 Redis 缓存，不查也不写 MySQL。"""
        offset = min(int(offset), MAX_TRANSACTION_OFFSET)
        return self.execute_cached_fetch(
            table_name=TRANSACTION_TABLE_NAME,
            params={
                "symbol": symbol,
                "start": start,
                "offset": offset,
                "key_type": "transaction",
            },
            fetch_func=get_transaction,
            validate_rules={
                "symbol": "stock",
            },
            async_write=async_write,
            cache_empty=True,
            ttl_redis=REDIS_TTL_TRANSACTION,
            ttl_db=1,
            write_to_db=persist,
            read_from_db=read_from_db,
            cache_key_exclude_fields=None,
            dedup_keys=["symbol", "trade_date", "seq"],
        )

    def get_history_transaction(
        self,
        symbol: str,
        date: str,
        start: int = 0,
        offset: int = 800,
        async_write: bool = True,
        persist: bool = True,
        auto_clean: bool = True,
        retention_days: int = DEFAULT_HISTORY_RETENTION_DAYS,
    ) -> Dict[str, Any]:
        """查询历史分笔成交。默认入库，并写入清理策略字段。"""
        offset = min(int(offset), MAX_TRANSACTION_OFFSET)
        retention_days = max(1, min(int(retention_days), 3650))
        year_month = date[:6]
        table_name = f"{HISTORY_TRANSACTION_TABLE_PREFIX}{year_month}"

        return self.execute_cached_fetch(
            table_name=table_name,
            params={
                "symbol": symbol,
                "date": date,
                "start": start,
                "offset": offset,
                "auto_clean": auto_clean,
                "retention_days": retention_days,
                "key_type": f"history_transaction_{year_month}",
            },
            fetch_func=get_history_transaction,
            validate_rules={
                "symbol": "stock",
                "date": "date_format",
            },
            async_write=async_write,
            cache_empty=True,
            ttl_redis=REDIS_TTL_HISTORY_TRANSACTION,
            ttl_db=DB_TTL_HISTORY_TRANSACTION,
            write_to_db=persist,
            cache_key_exclude_fields=None,
            dedup_keys=["symbol", "trade_date", "seq"],
        )


transaction_service = TransactionService()
