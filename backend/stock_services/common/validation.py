"""
stock_services/common/validation.py — 参数验证统一封装

合并两套功能重叠的验证器：
  1. utils/validate_params.py ParameterValidator（300+ 行，类实现）
  2. unity/utils.py StockValidateService（约 100 行，类实现）

重叠度约 50%：
  - validate_symbol / validate_stock_symbol 功能相同
  - validate_sh_symbol_type / validate_sz_symbol_type 完全相同
  - validate_date_format / validate_date_range 功能一致

本模块提供统一的 StockValidator，消除两套验证器并存的问题。
"""

import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from stock_services.common.response import ok_result, fail_result

logger = logging.getLogger(__name__)


class StockValidator:
    """
    统一股票参数验证器。

    合并以下两套实现的功能：
      - utils/validate_params.py ParameterValidator（类方法）
      - unity/utils.py StockValidateService（已在 3+ 文件中引用）
      - services/basic_services.py validate_rules DSL（6种规则类型）

    提供函数级别和结果字典级别两套 API：
      - validate_symbol() -> (bool, str) 函数级
      - validate_symbol_result() -> dict 结果字典级（兼容旧代码）
    """

    # ══════════════════════════════════════════════════════════════
    #  股票代码验证
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def validate_symbol(symbol: str) -> tuple:
        """
        验证并标准化股票代码。

        Args:
            symbol: 原始股票代码

        Returns:
            (success: bool, normalized_symbol_or_error: str)
        """
        if not symbol or not isinstance(symbol, str):
            return False, "股票代码不能为空且必须是字符串"

        symbol = symbol.strip().upper()

        # 完整格式 SZ000001 / SH600000
        if re.match(r'^(SH|SZ)\d{6}$', symbol):
            return True, symbol

        # 纯 6 位数字，自动添加市场前缀
        if re.match(r'^\d{6}$', symbol):
            if symbol[0] in ('0', '3'):
                return True, f"SZ{symbol}"
            elif symbol[0] in ('6', '9'):
                return True, f"SH{symbol}"
            else:
                return False, f"无法识别股票代码市场: {symbol}"

        # 尝试匹配 SZ + 6位 (已有前缀)
        if re.match(r'^[A-Z]{1,4}\d{6}$', symbol):
            return True, symbol

        return False, f"股票代码格式不正确: {symbol}"

    @staticmethod
    def validate_symbol_result(symbol: str) -> Dict[str, Any]:
        """结果字典版 validate_symbol（兼容 StockValidateService 调用方）"""
        ok, msg_or_sym = StockValidator.validate_symbol(symbol)
        if ok:
            return ok_result(data={"symbol": msg_or_sym})
        return fail_result(message=msg_or_sym, data={"symbol": symbol})

    # ══════════════════════════════════════════════════════════════
    #  板块类型验证
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def validate_sh_symbol_type(symbol: str) -> tuple:
        """验证上交所板块类型"""
        if not symbol or not isinstance(symbol, str):
            return False, "板块类型不能为空"
        valid = {"主板A股", "主板B股", "科创板"}
        if symbol not in valid:
            return False, f"板块类型必须为: {', '.join(sorted(valid))}"
        return True, ""

    @staticmethod
    def validate_sh_symbol_type_result(symbol: str) -> Dict[str, Any]:
        ok, msg = StockValidator.validate_sh_symbol_type(symbol)
        if ok:
            return ok_result(data={"symbol": symbol})
        return fail_result(message=msg, data={"symbol": symbol})

    @staticmethod
    def validate_sz_symbol_type(symbol: str) -> tuple:
        """验证深交所列表类型"""
        if not symbol or not isinstance(symbol, str):
            return False, "列表类型不能为空"
        valid = {"A股列表", "B股列表", "AB股列表", "CDR列表"}
        if symbol not in valid:
            return False, f"列表类型必须为: {', '.join(sorted(valid))}"
        return True, ""

    @staticmethod
    def validate_sz_symbol_type_result(symbol: str) -> Dict[str, Any]:
        ok, msg = StockValidator.validate_sz_symbol_type(symbol)
        if ok:
            return ok_result(data={"symbol": symbol})
        return fail_result(message=msg, data={"symbol": symbol})

    # ══════════════════════════════════════════════════════════════
    #  日期验证
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def validate_date(date_str: str, fmt: str = "%Y-%m-%d") -> tuple:
        """
        验证日期字符串格式。

        Returns:
            (success: bool, error_message: str)
        """
        if not date_str:
            return False, "日期不能为空"
        try:
            datetime.strptime(date_str, fmt)
            return True, ""
        except ValueError:
            return False, f"日期格式不正确: {date_str}，期望 {fmt}"

    @staticmethod
    def validate_date_result(date_str: str, fmt: str = "%Y-%m-%d") -> Dict[str, Any]:
        ok, msg = StockValidator.validate_date(date_str, fmt)
        if ok:
            return ok_result(data={"date": date_str})
        return fail_result(message=msg, data={"date": date_str})

    @staticmethod
    def validate_date_range(start_date: str, end_date: str,
                            fmt: str = "%Y-%m-%d") -> tuple:
        """验证日期范围"""
        ok, msg = StockValidator.validate_date(start_date, fmt)
        if not ok:
            return False, msg
        ok, msg = StockValidator.validate_date(end_date, fmt)
        if not ok:
            return False, msg

        start_dt = datetime.strptime(start_date, fmt)
        end_dt = datetime.strptime(end_date, fmt)
        if end_dt < start_dt:
            return False, f"结束日期 {end_date} 不能早于开始日期 {start_date}"
        return True, ""

    # ══════════════════════════════════════════════════════════════
    #  参数必填验证
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def validate_required_params(params: Dict[str, Any],
                                 required_keys: List[str]) -> tuple:
        """验证必需参数是否存在"""
        missing = [k for k in required_keys if k not in params or params[k] is None]
        if missing:
            return False, f"缺少必需参数: {', '.join(missing)}"
        return True, ""

    @staticmethod
    def validate_required_params_result(params: Dict[str, Any],
                                        required_keys: List[str]) -> Dict[str, Any]:
        ok, msg = StockValidator.validate_required_params(params, required_keys)
        if ok:
            return ok_result(data={"params": params})
        return fail_result(message=msg, data={"params": params, "missing_keys": required_keys})

    # ══════════════════════════════════════════════════════════════
    #  execute_cached_fetch 验证规则 DSL 映射
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def validate_by_rules(params: Dict[str, Any],
                          rules: Dict[str, str]) -> tuple:
        """
        按 rules DSL 执行验证（兼容 basic_services.py validate_rules）。

        Rules 格式:
            {"symbol": "stock", "date": "date_format", ...}

        Returns:
            (success: bool, error_message: str)
        """
        if not rules:
            return True, ""

        for param_name, rule_type in rules.items():
            value = params.get(param_name)

            if rule_type == "stock":
                if not value:
                    return False, f"参数 '{param_name}' 不能为空"
                ok, msg = StockValidator.validate_symbol(value)
                if not ok:
                    return False, f"参数 '{param_name}' 验证失败: {msg}"

            elif rule_type == "date_format":
                ok, msg = StockValidator.validate_date(value)
                if not ok:
                    return False, f"参数 '{param_name}' 验证失败: {msg}"

            elif rule_type == "required":
                if value is None or (isinstance(value, str) and not value.strip()):
                    return False, f"必需参数 '{param_name}' 缺失"

            elif rule_type == "int":
                try:
                    int(value)
                except (TypeError, ValueError):
                    return False, f"参数 '{param_name}' 必须为整数"

            elif rule_type == "float":
                try:
                    float(value)
                except (TypeError, ValueError):
                    return False, f"参数 '{param_name}' 必须为数值"

        return True, ""


# 全局默认实例（兼容旧代码的模块级函数引用）
default_validator = StockValidator()

# 模块级便捷函数
validate_symbol = StockValidator.validate_symbol_result
validate_sh_symbol_type = StockValidator.validate_sh_symbol_type_result
validate_sz_symbol_type = StockValidator.validate_sz_symbol_type_result
validate_date = StockValidator.validate_date_result

__all__ = [
    "StockValidator",
    "default_validator",
    "validate_symbol",
    "validate_sh_symbol_type",
    "validate_sz_symbol_type",
    "validate_date",
]