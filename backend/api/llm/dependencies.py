"""
LLM模块依赖注入

将服务实例通过FastAPI的Depends()注入到路由函数中。
避免在路由函数中直接实例化服务，实现解耦。
"""


def get_llm_service():
    """获取LLM服务实例"""
    from system_service.llm_service import get_llm_service as _get_service
    return _get_service()