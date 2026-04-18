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
]