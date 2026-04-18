#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票基本信息模块
接口列表：
1. get_stock_info(symbol) - 查询股票基本信息
2. get_all_stock_codes() - 查询全市场A股股票代码列表
3. get_all_stock_codes_json() - 查询全市场A股股票代码列表（JSON格式）
4. get_sh_stock_codes(symbol="主板A股") - 查询上交所股票代码
5. get_sz_stock_codes(symbol="A股列表") - 查询深交所股票代码
6. get_bj_stock_codes() - 查询北交所股票代码
7. get_sh_delist_stocks(symbol="全部") - 查询上交所退市股票
8. get_sz_delist_stocks(symbol="终止上市公司") - 查询深交所退市股票
9. get_xq_stock_info(symbol) - 查询雪球财经个股概况
10. get_stock_info_json(symbol) - 查询股票信息并返回JSON字符串

数据库表结构：
- stocks_info 表：包含 symbol, name, market, list_date 等字段
"""

import json
from typing import Any, Dict

from stock_services.services.commont.stock_service import BaseStockService
# 导入统一的异常处理和结果格式模块
from system_service.exception_handler import (
    ServiceException,
    ValidationException,
    DataNotFoundError,
    ExternalServiceException,
    DatabaseException
)
from system_service.service_result import (
    success_result
)

# 导入数据库工具

# 导入日志配置
from config.logging_config import get_logger

logger = get_logger(__name__)


class StockBasicService(BaseStockService):
    """股票基本信息服务类 - 整合所有接口"""
    
    def __init__(self):
        """初始化服务"""
        super().__init__("StockBasicService")
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        查询指定股票代码的个股基础信息
        
        注意：此函数直接抛出异常，由全局异常处理器处理
        
        Args:
            symbol: 股票代码，如 "000001"（平安银行），"603777"（来伊份）
            
        Returns:
            统一格式的响应数据
            
        Raises:
            ValidationException: 参数验证失败
            DataNotFoundError: 股票信息未找到
            ExternalServiceException: 外部服务调用失败
            DatabaseException: 数据库操作失败
        """
        try:
            # 参数验证
            if not symbol or not isinstance(symbol, str):
                raise ValidationException(
                    message="股票代码必须为非空字符串",
                    details={"symbol": symbol or ""}
                )
            
            self.logger.info(f"开始查询股票基本信息 symbol={symbol}")
            
            # 1. 先尝试从数据库获取
            db_data = None
            try:
                db_data = self._get_from_database(symbol)
            except DatabaseException as db_e:
                self._log_exception(db_e, "数据库查询股票信息", "error")
                # 数据库异常时继续尝试AKShare
            
            if db_data:
                cleaned_data = self._clean_stock_data(db_data, "basic")
                self.logger.info(f"成功从数据库获取股票 {symbol} 的信息")
                return success_result(
                    data=cleaned_data,
                    message="从数据库获取股票信息成功"
                )
            
            # 2. 数据库没有数据，调用AKShare接口
            self.logger.info(f"数据库无数据，调用AKShare接口查询 symbol={symbol}")
            
            # 调用AKShare获取股票基本信息
            akshare_data = self._get_from_akshare(
                "stock_individual_info_em",
                symbol=symbol
            )
            
            # 清洗数据
            cleaned_data = self._clean_stock_data(akshare_data, "basic")
            
            if not cleaned_data:
                raise DataNotFoundError(f"未找到股票 {symbol} 的信息")
            
            self.logger.info(f"成功从AKShare获取股票 {symbol} 的信息")
            return success_result(
                data=cleaned_data,
                message="从AKShare获取股票信息成功"
            )
            
        except (ValidationException, DataNotFoundError, ExternalServiceException, DatabaseException):
            # 这些异常直接抛出，由全局异常处理器处理
            raise
        except Exception as e:
            # 其他未预期的异常
            self._log_exception(e, f"查询股票信息: {symbol}", "error")
            raise ServiceException(f"查询股票信息失败: {str(e)}")
    
    def get_all_stock_codes(self) -> Dict[str, Any]:
        """
        获取全市场A股股票代码列表
        
        注意：此函数直接抛出异常，由全局异常处理器处理
        
        Returns:
            统一格式的响应数据
        """
        self.logger.info("开始查询全市场A股股票代码列表")
        
        # 1. 先尝试从数据库获取
        db_data = self._get_from_database()
        if db_data:
            return success_result(
                data=db_data,
                message="从数据库获取全市场股票代码成功"
            )
        
        # 2. 数据库没有数据，调用AKShare接口
        self.logger.info("数据库无数据，调用AKShare接口查询全市场股票代码")
        
        # 调用AKShare获取全市场股票代码
        akshare_data = self._get_from_akshare("stock_info_a_code_name")
        
        # 清洗数据
        cleaned_data = self._clean_stock_data(akshare_data, "list")
        
        if not cleaned_data or cleaned_data.get("count", 0) == 0:
            raise DataNotFoundError("未找到全市场股票代码")
        
        return success_result(
            data=cleaned_data,
            message="从AKShare获取全市场股票代码成功"
        )
    
    def get_all_stock_codes_json(self) -> Dict[str, Any]:
        """
        获取全市场A股股票代码列表（JSON格式）
        
        注意：此函数直接抛出异常，由全局异常处理器处理
        
        Returns:
            统一格式的响应数据，data字段为JSON字符串
        """
        self.logger.info("开始查询全市场A股股票代码列表（JSON格式）")
        
        # 先获取数据
        result = self.get_all_stock_codes()
        
        if not result.get("success", False):
            return result
        
        # 将数据转换为JSON字符串
        data = result.get("data", {})
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        return success_result(
            data=json_str,
            message="获取全市场股票代码JSON成功"
        )
    
    def get_sh_stock_codes(self, symbol: str = "主板A股") -> Dict[str, Any]:
        """
        获取上海证券交易所股票代码和简称数据
        
        注意：此函数直接抛出异常，由全局异常处理器处理
        
        Args:
            symbol: 股票板块类型，可选值：{"主板A股", "主板B股", "科创板"}
            
        Returns:
            统一格式的响应数据
        """
        # 参数验证
        valid_symbols = {"主板A股", "主板B股", "科创板"}
        if symbol not in valid_symbols:
            raise ValidationException(
                message=f"symbol参数必须为: {valid_symbols}",
                details={"symbol": symbol}
            )
        
        self.logger.info(f"开始查询上交所股票代码列表 symbol={symbol}")
        
        # 调用AKShare接口
        akshare_data = self._get_from_akshare(
            "stock_info_sh_name_code",
            symbol=symbol
        )
        
        # 清洗数据
        cleaned_data = self._clean_stock_data(akshare_data, "list")
        
        if not cleaned_data or cleaned_data.get("count", 0) == 0:
            raise DataNotFoundError(f"未找到上交所 {symbol} 的股票代码")
        
        return success_result(
            data=cleaned_data,
            message=f"获取上交所{symbol}股票代码成功"
        )
    
    def get_sz_stock_codes(self, symbol: str = "A股列表") -> Dict[str, Any]:
        """
        获取深圳证券交易所股票代码和简称数据
        
        注意：此函数直接抛出异常，由全局异常处理器处理
        
        Args:
            symbol: 股票列表类型，可选值：{"A股列表", "B股列表", "AB股列表", "CDR列表"}
            
        Returns:
            统一格式的响应数据
        """
        # 参数验证
        valid_symbols = {"A股列表", "B股列表", "AB股列表", "CDR列表"}
        if symbol not in valid_symbols:
            raise ValidationException(
                message=f"symbol参数必须为: {valid_symbols}",
                details={"symbol": symbol}
            )
        
        self.logger.info(f"开始查询深交所股票代码列表 symbol={symbol}")
        
        # 调用AKShare接口
        akshare_data = self._get_from_akshare(
            "stock_info_sz_name_code",
            symbol=symbol
        )
        
        # 清洗数据
        cleaned_data = self._clean_stock_data(akshare_data, "list")
        
        if not cleaned_data or cleaned_data.get("count", 0) == 0:
            raise DataNotFoundError(f"未找到深交所 {symbol} 的股票代码")
        
        return success_result(
            data=cleaned_data,
            message=f"获取深交所{symbol}股票代码成功"
        )
    
    def get_bj_stock_codes(self) -> Dict[str, Any]:
        """
        获取北京证券交易所股票代码和简称数据
        
        注意：此函数直接抛出异常，由全局异常处理器处理
        
        Returns:
            统一格式的响应数据
        """
        self.logger.info("开始查询北交所股票代码列表")
        
        # 调用AKShare接口
        akshare_data = self._get_from_akshare("stock_info_bj_name_code")
        
        # 清洗数据
        cleaned_data = self._clean_stock_data(akshare_data, "list")
        
        if not cleaned_data or cleaned_data.get("count", 0) == 0:
            raise DataNotFoundError("未找到北交所股票代码")
        
        return success_result(
            data=cleaned_data,
            message="获取北交所股票代码成功"
        )
    
    def get_sh_delist_stocks(self, symbol: str = "全部") -> Dict[str, Any]:
        """
        获取上海证券交易所暂停/终止上市股票
        
        注意：此函数直接抛出异常，由全局异常处理器处理
        
        Args:
            symbol: 市场类型，可选值：{"全部", "沪市", "科创板"}
            
        Returns:
            统一格式的响应数据
        """
        # 参数验证
        valid_symbols = {"全部", "沪市", "科创板"}
        if symbol not in valid_symbols:
            raise ValidationException(
                message=f"symbol参数必须为: {valid_symbols}",
                details={"symbol": symbol}
            )
        
        self.logger.info(f"开始查询上交所退市股票列表 symbol={symbol}")
        
        # 调用AKShare接口
        akshare_data = self._get_from_akshare(
            "stock_info_sh_delist",
            symbol=symbol
        )
        
        # 清洗数据
        cleaned_data = self._clean_stock_data(akshare_data, "list")
        
        if not cleaned_data or cleaned_data.get("count", 0) == 0:
            raise DataNotFoundError(f"未找到上交所 {symbol} 的退市股票")
        
        return success_result(
            data=cleaned_data,
            message=f"获取上交所{symbol}退市股票成功"
        )
    
    def get_sz_delist_stocks(self, symbol: str = "终止上市公司") -> Dict[str, Any]:
        """
        获取深圳证券交易所终止/暂停上市股票
        
        注意：此函数直接抛出异常，由全局异常处理器处理
        
        Args:
            symbol: 股票状态类型，可选值：{"终止上市公司", "暂停上市公司"}
            
        Returns:
            统一格式的响应数据
        """
        # 参数验证
        valid_symbols = {"终止上市公司", "暂停上市公司"}
        if symbol not in valid_symbols:
            raise ValidationException(
                message=f"symbol参数必须为: {valid_symbols}",
                details={"symbol": symbol}
            )
        
        self.logger.info(f"开始查询深交所退市股票列表 symbol={symbol}")
        
        # 调用AKShare接口
        akshare_data = self._get_from_akshare(
            "stock_info_sz_delist",
            symbol=symbol
        )
        
        # 清洗数据
        cleaned_data = self._clean_stock_data(akshare_data, "list")
        
        if not cleaned_data or cleaned_data.get("count", 0) == 0:
            raise DataNotFoundError(f"未找到深交所 {symbol} 的退市股票")
        
        return success_result(
            data=cleaned_data,
            message=f"获取深交所{symbol}退市股票成功"
        )
    
    def get_xq_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        查询雪球财经-个股-公司概况
        
        注意：此函数直接抛出异常，由全局异常处理器处理
        
        Args:
            symbol: 股票代码，需带市场前缀，如 "SH601127"
            
        Returns:
            统一格式的响应数据
        """
        # 参数验证
        if not symbol or not isinstance(symbol, str):
            raise ValidationException(
                message="股票代码必须为非空字符串",
                details={"symbol": symbol or ""}
            )
        
        self.logger.info(f"开始查询雪球个股概况 symbol={symbol}")
        
        # 调用AKShare接口
        akshare_data = self._get_from_akshare(
            "stock_individual_basic_info_xq",
            symbol=symbol
        )
        
        # 清洗数据
        cleaned_data = self._clean_stock_data(akshare_data, "xq")
        
        if not cleaned_data:
            raise DataNotFoundError(f"未找到雪球股票 {symbol} 的信息")
        
        return success_result(
            data=cleaned_data,
            message="获取雪球个股概况成功"
        )
    
    def get_stock_info_json(self, symbol: str) -> Dict[str, Any]:
        """
        查询个股信息并返回JSON字符串
        
        注意：此函数直接抛出异常，由全局异常处理器处理
        
        Args:
            symbol: 股票代码，如 "000001" 或 "000001.SZ"
            
        Returns:
            统一格式的响应数据，data字段为JSON字符串
        """
        self.logger.info(f"开始查询股票信息JSON symbol={symbol}")
        
        # 先获取股票信息
        result = self.get_stock_info(symbol)
        
        if not result.get("success", False):
            return result
        
        # 将数据转换为JSON字符串
        data = result.get("data", {})
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        return success_result(
            data=json_str,
            message="获取股票信息JSON成功"
        )


unity_service = StockBasicService()
