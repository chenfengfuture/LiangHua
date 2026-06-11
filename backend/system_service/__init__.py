"""
独立服务层模块

将业务逻辑从路由层抽离，实现清晰的关注点分离：
- 路由层：HTTP请求处理、参数验证、响应组装
- 服务层：核心业务逻辑、数据操作、业务规则
"""



# 导出新闻相关服务（暂时注释，因为导入依赖问题）
# from .news_service import (
#     NewsCollectorService,
#     NewsLLMAnalyzerService,
#     NewsPersistService,
#     get_news_collector_service,
#     get_news_llm_analyzer_service,
#     get_news_persist_service,
# )

# 导出LLM相关服务（暂时注释，因为导入依赖问题）
# from .llm_service import (
#     LLMService,
#     get_llm_service,
# )

# 导出服务结果结构
from .service_result import (
    ServiceResult,
    ServiceResultModel,
    success_result,
    error_result,
    wrap_service_result,
    ServiceResponse,
)


# 导出全局异常处理器
from .exception_handler import (
    ServiceException,
    ValidationException,
    DataNotFoundError,
    DatabaseException,
    ExternalServiceException,
    register_global_exception_handler,
)

# 导出表结构缓存服务
from .schema_cache import (
    SchemaCache,
    get_schema_cache,
    get_table_columns,
    cast_value_by_column,
    filter_record_by_schema,
)

from .db_service import (
    DBService,
    get_db_service,
    upsert_data_with_schema,
    simple_upsert,
)

from .async_writer import (
    AsyncWriter,
    WriteTask,
    get_async_writer,
    submit_async_upsert,
    shutdown_async_writer,
)

__all__ = [
    # 服务结果结构
    "ServiceResult",
    "ServiceResultModel",
    "success_result",
    "error_result",
    "wrap_service_result",
    "ServiceResponse",
    
    # 全局异常处理器
    "ServiceException",
    "ValidationException",
    "DataNotFoundError",
    "DatabaseException",
    "ExternalServiceException",
    "register_global_exception_handler",
    
    # 表结构缓存
    "SchemaCache",
    "get_schema_cache",
    "get_table_columns",
    "cast_value_by_column",
    "filter_record_by_schema",
    
    # 数据库写入服务
    "DBService",
    "get_db_service",
    "upsert_data_with_schema",
    "simple_upsert",
    
    # 异步写入服务
    "AsyncWriter",
    "WriteTask",
    "get_async_writer",
    "submit_async_upsert",
    "shutdown_async_writer",
]