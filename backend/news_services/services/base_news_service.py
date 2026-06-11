"""
news_services/services/base_news_service.py — 新闻服务基类

复用 system_service.redis_service.RedisServiceBase，提供：
  - 统一返回格式（{success, data, message}）
  - 统一异常捕获和日志
  - 统一启动/停止/状态查询接口（默认实现）

参考 stock_services/services/basic_services.py 的 BaseStockService。
"""

import logging
from typing import Any, Dict, Optional

from system_service.redis_service import RedisServiceBase


class BaseNewsService(RedisServiceBase):
    """
    新闻服务基类

    提供统一能力：
      - wrap_success / wrap_error  统一返回格式
      - log_exception              异常日志
      - get_status (默认未启动)    子类可覆盖
    """

    def __init__(self, service_name: str):
        super().__init__(service_name=service_name)
        self.logger = logging.getLogger(service_name)

    # ─────────────────────────────────────────────────────────────
    #  统一返回格式
    # ─────────────────────────────────────────────────────────────

    def wrap_success(self, data: Any = None, message: str = "") -> Dict[str, Any]:
        """统一成功返回"""
        return {
            "success": True,
            "data": data,
            "message": message,
        }

    def wrap_error(self, message: str, data: Any = None) -> Dict[str, Any]:
        """统一错误返回"""
        return {
            "success": False,
            "data": data,
            "message": message,
        }

    # ─────────────────────────────────────────────────────────────
    #  通用异常处理
    # ─────────────────────────────────────────────────────────────

    def log_exception(self, action: str, exc: Exception) -> None:
        """统一异常日志"""
        self.logger.error(f"[{self.service_name}] {action} 异常: {exc}")

    # ─────────────────────────────────────────────────────────────
    #  生命周期默认接口（子类按需覆盖）
    # ─────────────────────────────────────────────────────────────

    def start(self) -> Dict[str, Any]:
        """启动服务（默认空实现）"""
        return self.wrap_success(message=f"{self.service_name} start (base)")

    def stop(self) -> Dict[str, Any]:
        """停止服务（默认空实现）"""
        return self.wrap_success(message=f"{self.service_name} stop (base)")

    def get_status(self) -> Dict[str, Any]:
        """状态查询（默认空实现）"""
        return self.wrap_success(data={"running": False})
