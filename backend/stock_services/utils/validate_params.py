#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参数验证工具模块

提供统一的参数验证方法，用于验证各种API接口的参数。
所有参数验证方法都集中在此模块中，便于统一管理和维护。
"""

import re
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime

# 导入统一的结果构建函数
try:
    from system_service.service_result import build_success_result, build_error_result
except ImportError:
    # 如果导入失败，提供简单的实现
    def build_success_result(message: str = "", data: Any = None) -> Dict[str, Any]:
        return {"success": True, "message": message, "data": data}
    
    def build_error_result(message: str = "", data: Any = None) -> Dict[str, Any]:
        return {"success": False, "message": message, "data": data}


logger = logging.getLogger(__name__)


class ParameterValidator:
    """
    参数验证器类
    
    提供统一的参数验证方法，包括：
    1. 股票代码验证
    2. 板块类型验证
    3. 日期格式验证
    4. 数值范围验证
    5. 通用参数验证
    """
    
    def __init__(self, validator_name: str = "ParameterValidator"):
        """
        初始化参数验证器
        
        Args:
            validator_name: 验证器名称，用于日志记录
        """
        self.validator_name = validator_name
        self.logger = logging.getLogger(f"{__name__}.{validator_name}")
    
    # ============================================================================
    # 基础验证方法
    # ============================================================================
    
    def validate_required(self, param_name: str, param_value: Any, 
                         param_type: type = None) -> Dict[str, Any]:
        """
        验证参数是否必需且类型正确
        
        Args:
            param_name: 参数名称
            param_value: 参数值
            param_type: 期望的参数类型（可选）
            
        Returns:
            验证结果字典
        """
        # 检查参数是否为空
        if param_value is None:
            return build_error_result(
                message=f"参数 '{param_name}' 不能为 None",
                data={"param_name": param_name, "param_value": param_value}
            )
        
        # 检查字符串是否为空
        if isinstance(param_value, str) and not param_value.strip():
            return build_error_result(
                message=f"参数 '{param_name}' 不能为空字符串",
                data={"param_name": param_name, "param_value": param_value}
            )
        # 检查类型
        if param_type and not isinstance(param_value, param_type):
            return build_error_result(
                message=f"参数 '{param_name}' 类型错误，期望 {param_type.__name__}，实际 {type(param_value).__name__}",
                data={"param_name": param_name, "param_value": param_value, "expected_type": param_type.__name__}
            )
        return build_success_result(
            message=f"参数 '{param_name}' 验证成功",
            data={"param_name": param_name, "param_value": param_value}
        )
    
    def validate_string_length(self, param_name: str, param_value: str, 
                              min_length: int = 0, max_length: int = None) -> Dict[str, Any]:
        """
        验证字符串长度
        
        Args:
            param_name: 参数名称
            param_value: 参数值（字符串）
            min_length: 最小长度
            max_length: 最大长度
            
        Returns:
            验证结果字典
        """
        # 首先验证必需性
        required_result = self.validate_required(param_name, param_value, str)
        if not required_result["success"]:
            return required_result
        
        length = len(param_value)
        
        # 验证最小长度
        if min_length > 0 and length < min_length:
            return build_error_result(
                message=f"参数 '{param_name}' 长度不能小于 {min_length}，实际长度: {length}",
                data={"param_name": param_name, "param_value": param_value, 
                      "min_length": min_length, "actual_length": length}
            )
        
        # 验证最大长度
        if max_length is not None and length > max_length:
            return build_error_result(
                message=f"参数 '{param_name}' 长度不能大于 {max_length}，实际长度: {length}",
                data={"param_name": param_name, "param_value": param_value,
                      "max_length": max_length, "actual_length": length}
            )
        
        return build_success_result(
            message=f"参数 '{param_name}' 长度验证成功",
            data={"param_name": param_name, "param_value": param_value, "length": length}
        )
    
    def validate_numeric_range(self, param_name: str, param_value: Union[int, float],
                              min_value: Union[int, float] = None, 
                              max_value: Union[int, float] = None) -> Dict[str, Any]:
        """
        验证数值范围
        
        Args:
            param_name: 参数名称
            param_value: 参数值（数值）
            min_value: 最小值
            max_value: 最大值
            
        Returns:
            验证结果字典
        """
        # 首先验证必需性
        required_result = self.validate_required(param_name, param_value, (int, float))
        if not required_result["success"]:
            return required_result
        
        # 验证最小值
        if min_value is not None and param_value < min_value:
            return build_error_result(
                message=f"参数 '{param_name}' 不能小于 {min_value}，实际值: {param_value}",
                data={"param_name": param_name, "param_value": param_value,
                      "min_value": min_value}
            )
        
        # 验证最大值
        if max_value is not None and param_value > max_value:
            return build_error_result(
                message=f"参数 '{param_name}' 不能大于 {max_value}，实际值: {param_value}",
                data={"param_name": param_name, "param_value": param_value,
                      "max_value": max_value}
            )
        
        return build_success_result(
            message=f"参数 '{param_name}' 数值范围验证成功",
            data={"param_name": param_name, "param_value": param_value}
        )
    
    # ============================================================================
    # 股票相关验证方法
    # ============================================================================
    
    def validate_stock_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        验证股票代码格式
        
        Args:
            symbol: 股票代码
            
        Returns:
            验证结果字典
        """
        # 验证必需性
        required_result = self.validate_required("symbol", symbol, str)
        if not required_result["success"]:
            return required_result
        
        # 标准化symbol格式（确保大写）
        symbol = symbol.strip().upper()
        
        # 基本格式验证：至少包含字母和数字
        if not re.match(r'^[A-Z]{1,4}\d{6}$', symbol):
            # 尝试添加市场前缀
            if symbol.startswith(('SH', 'SZ')):
                if not re.match(r'^(SH|SZ)\d{6}$', symbol):
                    return build_error_result(
                        message=f"股票代码格式不正确: {symbol}",
                        data={"symbol": symbol}
                    )
            else:
                # 尝试自动添加市场前缀
                if len(symbol) == 6:
                    # 简单规则：6位数字，0/3开头为深圳，6开头为上海
                    if symbol[0] in ('0', '3'):
                        symbol = f"SZ{symbol}"
                    elif symbol[0] in ('6', '9'):
                        symbol = f"SH{symbol}"
                    else:
                        return build_error_result(
                            message=f"无法识别股票代码市场: {symbol}",
                            data={"symbol": symbol}
                        )
                else:
                    return build_error_result(
                        message=f"股票代码格式不正确: {symbol}",
                        data={"symbol": symbol}
                    )
        
        return build_success_result(
            message="股票代码验证成功",
            data={"symbol": symbol}
        )
    
    def validate_sh_symbol_type(self, symbol: str) -> Dict[str, Any]:
        """
        验证上交所股票板块类型
        
        Args:
            symbol: 板块类型，可选值："主板A股", "主板B股", "科创板"
            
        Returns:
            验证结果字典
        """
        # 验证必需性
        required_result = self.validate_required("symbol", symbol, str)
        if not required_result["success"]:
            return required_result
        
        # 验证板块类型
        valid_types = {"主板A股", "主板B股", "科创板"}
        if symbol not in valid_types:
            return build_error_result(
                message=f"板块类型参数必须为以下值之一: {', '.join(sorted(valid_types))}",
                data={"symbol": symbol, "valid_types": list(valid_types)}
            )
        
        return build_success_result(
            message="上交所板块类型验证成功",
            data={"symbol": symbol}
        )
    
    def validate_sz_symbol_type(self, symbol: str) -> Dict[str, Any]:
        """
        验证深交所股票列表类型
        
        Args:
            symbol: 列表类型，可选值："A股列表", "B股列表", "AB股列表", "CDR列表"
            
        Returns:
            验证结果字典
        """
        # 验证必需性
        required_result = self.validate_required("symbol", symbol, str)
        if not required_result["success"]:
            return required_result
        
        # 验证列表类型
        valid_types = {"A股列表", "B股列表", "AB股列表", "CDR列表"}
        if symbol not in valid_types:
            return build_error_result(
                message=f"深交所列表类型参数必须为以下值之一: {', '.join(sorted(valid_types))}",
                data={"symbol": symbol, "valid_types": list(valid_types)}
            )
        
        return build_success_result(
            message="深交所列表类型验证成功",
            data={"symbol": symbol}
        )
    
    def validate_bj_symbol_type(self) -> Dict[str, Any]:
        """
        验证北交所股票列表（北交所只有一个列表，不需要参数）
        
        Returns:
            验证结果字典
        """
        # 北交所不需要参数验证，总是返回成功
        return build_success_result(
            message="北交所列表验证成功",
            data={"symbol": "北交所"}
        )
    
    # ============================================================================
    # 日期相关验证方法
    # ============================================================================
    
    def validate_date_format(self, date_str: str, 
                            date_format: str = "%Y-%m-%d") -> Dict[str, Any]:
        """
        验证日期格式
        
        Args:
            date_str: 日期字符串
            date_format: 期望的日期格式
            
        Returns:
            验证结果字典
        """
        # 验证必需性
        required_result = self.validate_required("date", date_str, str)
        if not required_result["success"]:
            return required_result
        
        try:
            # 尝试解析日期
            datetime.strptime(date_str, date_format)
            return build_success_result(
                message=f"日期格式验证成功: {date_str}",
                data={"date": date_str, "format": date_format}
            )
        except ValueError:
            return build_error_result(
                message=f"日期格式不正确: {date_str}，期望格式: {date_format}",
                data={"date": date_str, "expected_format": date_format}
            )
    
    def validate_date_range(self, start_date: str, end_date: str,
                           date_format: str = "%Y-%m-%d") -> Dict[str, Any]:
        """
        验证日期范围（结束日期不能早于开始日期）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            date_format: 日期格式
            
        Returns:
            验证结果字典
        """
        # 验证开始日期
        start_result = self.validate_date_format(start_date, date_format)
        if not start_result["success"]:
            return start_result
        
        # 验证结束日期
        end_result = self.validate_date_format(end_date, date_format)
        if not end_result["success"]:
            return end_result
        
        # 解析日期
        start_dt = datetime.strptime(start_date, date_format)
        end_dt = datetime.strptime(end_date, date_format)
        
        # 验证日期范围
        if end_dt < start_dt:
            return build_error_result(
                message=f"结束日期 {end_date} 不能早于开始日期 {start_date}",
                data={"start_date": start_date, "end_date": end_date}
            )
        
        return build_success_result(
            message="日期范围验证成功",
            data={"start_date": start_date, "end_date": end_date}
        )
    
    # ============================================================================
    # 复合验证方法（用于execute_cached_fetch）
    # ============================================================================
    
    def validate_sh_stock_list_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证上交所股票列表查询参数（用于execute_cached_fetch）
        
        Args:
            params: 参数字典，包含symbol字段
            
        Returns:
            验证结果字典
        """
        self.logger.debug(f"验证上交所股票列表参数: {params}")
        
        # 提取参数
        symbol_type = params.get("symbol", "")
        
        # 验证板块类型
        return self.validate_sh_symbol_type(symbol_type)
    
    def validate_sz_stock_list_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证深交所股票列表查询参数（用于execute_cached_fetch）
        
        Args:
            params: 参数字典，包含symbol字段
            
        Returns:
            验证结果字典
        """
        self.logger.debug(f"验证深交所股票列表参数: {params}")
        
        # 提取参数
        symbol_type = params.get("symbol", "")
        
        # 验证列表类型
        return self.validate_sz_symbol_type(symbol_type)
    
    def validate_stock_symbol_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证股票代码参数（用于execute_cached_fetch）
        
        Args:
            params: 参数字典，包含symbol字段
            
        Returns:
            验证结果字典
        """
        self.logger.debug(f"验证股票代码参数: {params}")
        
        # 提取参数
        symbol = params.get("symbol", "")
        
        # 验证股票代码
        return self.validate_stock_symbol(symbol)
    
    def validate_date_range_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证日期范围参数（用于execute_cached_fetch）
        
        Args:
            params: 参数字典，包含start_date和end_date字段
            
        Returns:
            验证结果字典
        """
        self.logger.debug(f"验证日期范围参数: {params}")
        
        # 提取参数
        start_date = params.get("start_date", "")
        end_date = params.get("end_date", "")
        
        # 验证日期范围
        return self.validate_date_range(start_date, end_date)


# 创建全局验证器实例
default_validator = ParameterValidator()

# 导出常用验证函数（兼容旧代码）
validate_sh_symbol_type = default_validator.validate_sh_symbol_type
validate_sh_stock_list_params = default_validator.validate_sh_stock_list_params
validate_stock_symbol = default_validator.validate_stock_symbol
validate_stock_symbol_params = default_validator.validate_stock_symbol_params
validate_sz_symbol_type = default_validator.validate_sz_symbol_type
validate_sz_stock_list_params = default_validator.validate_sz_stock_list_params
validate_date_format = default_validator.validate_date_format
validate_date_range = default_validator.validate_date_range
validate_date_range_params = default_validator.validate_date_range_params

# 导出类
__all__ = [
    "ParameterValidator",
    "default_validator",
    "validate_sh_symbol_type",
    "validate_sh_stock_list_params",
    "validate_stock_symbol",
    "validate_stock_symbol_params",
    "validate_sz_symbol_type",
    "validate_sz_stock_list_params",
    "validate_date_format",
    "validate_date_range",
    "validate_date_range_params",
]