#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging, traceback
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status


"""
全局异常处理模块

提供：
1. 业务异常基类及子类（支持错误码、HTTP状态码、附加详情）
2. 全局异常处理器（注册到 FastAPI 应用）
3. 请求上下文日志记录（URL、方法、IP、参数）
4. 开发/生产环境不同的错误响应
5. FastAPI 内置异常（HTTPException、RequestValidationError）的统一转换
"""

# 配置日志
logger = logging.getLogger(__name__)
# ======================= 自定义异常类 =======================

class ServiceException(Exception):
    """
    服务层业务异常基类
    所有业务异常都应继承此类
    """

    def __init__(
            self,
            message: str,
            business_code: Optional[str] = None,
            http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
            details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化业务异常

        Args:
            message: 用户友好的错误消息
            business_code: 业务错误码（如 "DATA_NOT_FOUND"），前端可据此做差异化处理
            http_status: HTTP 状态码（默认 500）
            details: 附加错误详情（如字段名、错误值等，不包含敏感信息）
        """
        self.message = message
        self.business_code = business_code or self._default_business_code()
        self.http_status = http_status
        self.details = details or {}
        super().__init__(message)

    def _default_business_code(self) -> str:
        """默认业务错误码，子类可覆盖"""
        return "SERVICE_ERROR"

    def to_dict(self) -> Dict[str, Any]:
        """转换为标准错误响应体（不包含 HTTP 状态码）"""
        return {
            "success": False,
            "code": self.business_code,
            "message": self.message,
            "details": self.details if self.details else None,
            "data": None
        }


class ValidationException(ServiceException):
    """参数验证异常（HTTP 422）"""

    def __init__(
            self,
            message: str = "参数验证失败",
            business_code: str = "VALIDATION_ERROR",
            details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            business_code=business_code,
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )

    @classmethod
    def from_field(cls, field: str, value: Any, reason: str):
        """快速创建字段验证异常"""
        return cls(
            message=f"字段 '{field}' 验证失败: {reason}",
            details={"field": field, "value": value, "reason": reason}
        )


class DataNotFoundError(ServiceException):
    """数据不存在异常（HTTP 404）"""

    def __init__(
            self,
            message: str = "请求的资源不存在",
            business_code: str = "DATA_NOT_FOUND",
            details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            business_code=business_code,
            http_status=status.HTTP_404_NOT_FOUND,
            details=details
        )


class DatabaseException(ServiceException):
    """数据库操作异常（HTTP 503）"""

    def __init__(
            self,
            message: str = "数据库操作失败",
            business_code: str = "DATABASE_ERROR",
            details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            business_code=business_code,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class ExternalServiceException(ServiceException):
    """外部服务调用异常（HTTP 502）"""

    def __init__(
            self,
            message: str = "外部服务请求失败",
            business_code: str = "EXTERNAL_SERVICE_ERROR",
            details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            business_code=business_code,
            http_status=status.HTTP_502_BAD_GATEWAY,
            details=details
        )


class ForbiddenException(ServiceException):
    """权限不足异常（HTTP 403）"""

    def __init__(
            self,
            message: str = "权限不足",
            business_code: str = "FORBIDDEN",
            details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            business_code=business_code,
            http_status=status.HTTP_403_FORBIDDEN,
            details=details
        )


class UnauthorizedException(ServiceException):
    """未认证异常（HTTP 401）"""

    def __init__(
            self,
            message: str = "未授权访问",
            business_code: str = "UNAUTHORIZED",
            details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            business_code=business_code,
            http_status=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


# ======================= 全局异常处理器 =======================

def _get_request_context(request: Request) -> Dict[str, Any]:
    """提取请求上下文用于日志记录"""
    client_ip = request.client.host if request.client else "unknown"
    return {
        "url": request.url.path,
        "method": request.method,
        "client_ip": client_ip,
        "query_params": dict(request.query_params),
    }


def _is_development() -> bool:
    """判断是否为开发环境（可根据实际配置调整）"""
    import os
    return os.getenv("ENV", "production").lower() in ("dev", "development", "local")


def register_global_exception_handler(app: FastAPI):
    """
    注册全局异常处理器到 FastAPI 应用

    捕获所有未被服务层装饰器处理的异常，统一转换为标准错误响应格式。
    同时处理 FastAPI 内置异常（HTTPException、RequestValidationError）。

    Args:
        app: FastAPI 应用实例
    """

    # ---------- 处理 RequestValidationError（FastAPI 参数校验失败） ----------
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求参数验证错误"""
        # 提取错误详情
        errors = []
        for error in exc.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            errors.append({"field": field, "message": msg})

        # 记录警告日志
        ctx = _get_request_context(request)
        logger.warning(
            f"参数验证失败: {ctx['method']} {ctx['url']} - {errors}",
            extra={"request_context": ctx}
        )

        # 开发环境返回详细错误，生产环境仅返回摘要
        if _is_development():
            details = {"errors": errors}
            message = "参数验证失败"
        else:
            details = None
            message = "请求参数错误"

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "code": "VALIDATION_ERROR",
                "message": message,
                "details": details,
                "data": None
            }
        )

    # ---------- 处理 HTTPException（FastAPI 原生异常） ----------
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理 FastAPI 原生 HTTP 异常"""
        ctx = _get_request_context(request)
        logger.warning(
            f"HTTP异常: {exc.status_code} - {exc.detail} - {ctx['method']} {ctx['url']}",
            extra={"request_context": ctx}
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "code": "HTTP_EXCEPTION",
                "message": exc.detail,
                "details": None,
                "data": None
            }
        )

    # ---------- 处理自定义业务异常 ServiceException ----------
    @app.exception_handler(ServiceException)
    async def service_exception_handler(request: Request, exc: ServiceException):
        """处理自定义业务异常"""
        ctx = _get_request_context(request)

        # 根据异常类型选择日志级别
        if exc.http_status >= 500:
            logger.error(
                f"业务异常(服务器错误): {exc.business_code} - {exc.message} - {ctx['method']} {ctx['url']}",
                extra={"request_context": ctx, "details": exc.details}
            )
        else:
            logger.warning(
                f"业务异常(客户端错误): {exc.business_code} - {exc.message} - {ctx['method']} {ctx['url']}",
                extra={"request_context": ctx, "details": exc.details}
            )

        # 开发环境返回完整详情，生产环境隐藏细节
        if _is_development():
            content = exc.to_dict()
        else:
            content = {
                "success": False,
                "code": exc.business_code,
                "message": exc.message,
                "details": None,
                "data": None
            }

        return JSONResponse(
            status_code=exc.http_status,
            content=content
        )

    # ---------- 处理所有未捕获的异常（兜底） ----------
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """全局兜底异常处理器"""
        ctx = _get_request_context(request)

        # 记录完整堆栈
        logger.error(
            f"未捕获异常: {type(exc).__name__}: {str(exc)} - {ctx['method']} {ctx['url']}",
            extra={"request_context": ctx},
            exc_info=True
        )

        # 生产环境隐藏详细错误
        if _is_development():
            message = f"{type(exc).__name__}: {str(exc)}"
            details = {"traceback": traceback.format_exc()}
        else:
            message = "服务器内部错误，请稍后重试"
            details = None

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "code": "INTERNAL_SERVER_ERROR",
                "message": message,
                "details": details,
                "data": None
            }
        )

    logger.info("全局异常处理器已注册")


# ======================= 导出内容 =======================
__all__ = [
    # 异常类
    "ServiceException",
    "ValidationException",
    "DataNotFoundError",
    "DatabaseException",
    "ExternalServiceException",
    "ForbiddenException",
    "UnauthorizedException",
    # 注册函数
    "register_global_exception_handler",
]