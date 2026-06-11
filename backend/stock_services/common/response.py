"""
stock_services/common/response.py — 统一响应格式

复用 system_service.service_result 的标准响应函数，
消除 mootdx/base_service.py 中自定义的 _ok() / _fail() 包装。

设计思路：
  不新增响应格式，仅做引用包装。
  现有 system_service.service_result 已提供 success_result / error_result 标准定义。

使用方式：
    from stock_services.common.response import ok_result, fail_result

    result = ok_result(data=records)
    result = fail_result(message="查询失败")
"""

from system_service.service_result import (
    success_result as ok_result,
    error_result as fail_result,
)

# 保持与 mootdx/base_service.py 旧 _ok()/_fail() 签名兼容
# 旧签名：_ok(data) / _fail(msg)
# 新签名：ok_result(data=data) / fail_result(message=msg)
#
# 这两个包装函数解决了 mootdx 基类中自行定义 _ok/_fail 的冗余问题

__all__ = [
    "ok_result",
    "fail_result",
]