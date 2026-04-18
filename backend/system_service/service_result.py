"""
统一服务结果结构定义

定义服务层统一的返回格式，确保所有服务函数返回一致的结构：
- success: bool - 操作是否成功
- message: str - 成功时的提示或失败时的错误描述
- data: Any - 成功时返回的业务数据，失败时为 None

所有服务函数必须返回此结构的字典（或 Pydantic 模型实例）。
禁止服务函数返回其他格式（如直接返回列表、字符串、整数）。
"""

from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field


@dataclass
class ServiceResult:
    """服务结果数据类
    
    用于服务层统一返回结果，包含成功状态、消息和数据。
    """
    success: bool
    message: str
    data: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    def __repr__(self) -> str:
        return f"ServiceResult(success={self.success}, message={self.message}, data={type(self.data).__name__})"


class ServiceResultModel(BaseModel):
    """服务结果Pydantic模型
    
    用于API响应验证和文档生成。
    """
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="成功提示或错误描述")
    data: Optional[Any] = Field(None, description="业务数据，失败时为None")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "操作成功",
                "data": {"key": "value"}
            }
        }


def success_result(data: Any = None, message: str = "操作成功") -> Dict[str, Any]:
    """创建成功结果
    
    Args:
        data: 业务数据
        message: 成功消息
        
    Returns:
        包含成功结果的字典
    """
    return {
        "success": True,
        "message": message,
        "data": data
    }


def error_result(message: str, data: Any = None) -> Dict[str, Any]:
    """创建错误结果
    
    Args:
        message: 错误描述
        data: 可选的错误相关数据
        
    Returns:
        包含错误结果的字典
    """
    return {
        "success": False,
        "message": message,
        "data": data
    }


def wrap_service_result(func):
    """装饰器：包装服务函数返回结果
    
    将服务函数的返回值包装成统一格式。
    如果函数返回的是ServiceResult或字典，直接返回；
    否则包装为成功结果。
    
    Args:
        func: 服务函数
        
    Returns:
        包装后的函数
    """
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            
            # 如果已经是ServiceResult实例，转换为字典
            if isinstance(result, ServiceResult):
                return result.to_dict()
            
            # 如果已经是符合格式的字典，直接返回
            if isinstance(result, dict) and "success" in result:
                return result
            
            # 其他情况包装为成功结果
            return success_result(result)
            
        except Exception as e:
            # 捕获所有异常，返回错误结果
            return error_result(f"服务调用失败: {str(e)}")
    
    return wrapper


# 类型别名，便于代码中使用
ServiceResponse = Union[Dict[str, Any], ServiceResult, ServiceResultModel]


__all__ = [
    "ServiceResult",
    "ServiceResultModel",
    "success_result",
    "error_result",
    "wrap_service_result",
    "ServiceResponse",
]