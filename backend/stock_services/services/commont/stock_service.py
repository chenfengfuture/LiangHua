import logging
from typing import Any, Dict, Optional

import akshare as ak
import pandas as pd

from config.logging_config import log_exception
from models import fetch_stocks_info
from models.stock_models import fetch_all_stocks
from system_service import DatabaseException, ExternalServiceException, DataNotFoundError, ValidationException
from utils import table_exists


class BaseStockService:
    """股票服务基类 - 封装统一的返回结果和异常处理"""

    def __init__(self, service_name: str = "StockService"):
        """
        初始化基类

        Args:
            service_name: 服务名称，用于日志记录
        """
        self.service_name = service_name
        self.logger = logging.getLogger(f"{__name__}.{service_name}")

    def _check_database_table(self, table_name: str = "stocks_info") -> bool:
        """
        检查数据库表是否存在

        Args:
            table_name: 表名

        Returns:
            表是否存在
        """
        try:
            return table_exists(table_name)
        except Exception as e:
            self.logger.warning(f"检查表 {table_name} 时出错: {str(e)}")
            return False

    def _clean_stock_data(self, data: Any, data_type: str = "basic") -> Dict[str, Any]:
        """
        清洗和格式化股票数据

        Args:
            data: 原始数据（DataFrame, dict, list 等）
            data_type: 数据类型（basic, list, xq 等）

        Returns:
            清洗后的数据字典
        """
        if data is None:
            return {}

        if isinstance(data, pd.DataFrame):
            # 处理DataFrame
            if data.empty:
                return {}

            # 根据数据类型进行不同的清洗
            if data_type == "basic":
                # 股票基本信息清洗
                return self._clean_basic_data(data)
            elif data_type == "list":
                # 股票列表清洗
                return self._clean_list_data(data)
            elif data_type == "xq":
                # 雪球数据清洗
                return self._clean_xq_data(data)
            else:
                # 默认转换为字典列表
                return data.to_dict(orient="records")

        elif isinstance(data, dict):
            return data

        elif isinstance(data, list):
            return {"items": data, "count": len(data)}

        else:
            return {"data": data}

    def _clean_basic_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """清洗股票基本信息数据"""
        if df.empty:
            return {}

        # 获取第一条记录
        record = df.iloc[0].to_dict()

        # 标准化字段名
        cleaned = {}
        field_mapping = {
            "代码": "symbol",
            "名称": "name",
            "最新价": "latest_price",
            "涨跌幅": "change_percent",
            "涨跌额": "change_amount",
            "成交量": "volume",
            "成交额": "amount",
            "振幅": "amplitude",
            "最高": "high",
            "最低": "low",
            "今开": "open",
            "昨收": "prev_close",
            "量比": "volume_ratio",
            "换手率": "turnover_rate",
            "市盈率": "pe_ratio",
            "市净率": "pb_ratio",
            "总市值": "total_market_cap",
            "流通市值": "circulating_market_cap",
            "涨速": "rise_speed",
            "5分钟涨跌": "five_min_change",
            "60日涨跌幅": "sixty_day_change",
            "年初至今涨跌幅": "ytd_change",
            "上市日期": "list_date",
            "总股本": "total_shares",
            "流通股本": "circulating_shares"
        }

        for old_key, new_key in field_mapping.items():
            if old_key in record:
                cleaned[new_key] = record[old_key]

        return cleaned

    def _clean_list_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """清洗股票列表数据"""
        if df.empty:
            return {"items": [], "count": 0}

        # 转换为字典列表
        records = df.to_dict(orient="records")

        # 标准化字段
        cleaned_records = []
        for record in records:
            cleaned = {}
            if "代码" in record:
                cleaned["code"] = str(record["代码"]).strip()
            if "名称" in record:
                cleaned["name"] = str(record["名称"]).strip()
            if "上市日期" in record:
                cleaned["list_date"] = record["上市日期"]
            if "总股本" in record:
                cleaned["total_shares"] = record["总股本"]
            if "流通股本" in record:
                cleaned["circulating_shares"] = record["流通股本"]

            cleaned_records.append(cleaned)

        return {
            "items": cleaned_records,
            "count": len(cleaned_records)
        }

    def _clean_xq_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """清洗雪球数据"""
        if df.empty:
            return {}

        # 雪球数据通常是单条记录
        record = df.iloc[0].to_dict()

        # 标准化字段
        cleaned = {}
        field_mapping = {
            "股票代码": "symbol",
            "股票名称": "name",
            "当前价": "current_price",
            "涨跌幅": "change_percent",
            "涨跌额": "change_amount",
            "成交量": "volume",
            "成交额": "amount",
            "换手率": "turnover_rate",
            "市盈率": "pe_ratio",
            "市净率": "pb_ratio",
            "总市值": "total_market_cap",
            "流通市值": "circulating_market_cap",
            "52周最高": "week52_high",
            "52周最低": "week52_low",
            "每股收益": "eps",
            "每股净资产": "nav_per_share",
            "净资产收益率": "roe",
            "股息率": "dividend_yield",
            "行业": "industry",
            "地区": "region",
            "上市时间": "list_date"
        }

        for old_key, new_key in field_mapping.items():
            if old_key in record:
                cleaned[new_key] = record[old_key]

        return cleaned

    def _log_exception(self, e: Exception, context: str = "", level: str = "error") -> None:
        """
        记录异常日志 - 用于服务内部记录异常信息

        注意：此方法只记录日志，不处理异常，异常应该由全局异常处理器处理

        Args:
            e: 异常对象
            context: 异常上下文信息
            level: 日志级别（error, warning, info, debug）
        """
        full_context = f"{self.service_name} - {context}" if context else self.service_name
        log_exception(self.logger, e, full_context, level)
    
    def _validate_symbol(self, symbol: str) -> None:
        """
        验证股票代码格式
        
        Args:
            symbol: 股票代码
            
        Raises:
            ValidationException: 股票代码格式无效
        """
        if not symbol or not isinstance(symbol, str):
            raise ValidationException(
                message="股票代码不能为空",
                details={"symbol": symbol}
            )
        
        # 基本的股票代码格式检查（可以根据需求扩展）
        if len(symbol) < 2 or len(symbol) > 10:
            raise ValidationException(
                message=f"股票代码格式无效: {symbol}",
                details={"symbol": symbol, "reason": "长度应在2-10之间"}
            )
    
    def _handle_database_error(self, e: Exception, context: str = "数据库操作") -> None:
        """
        处理数据库异常，转换为适当的异常类型
        
        Args:
            e: 原始异常
            context: 异常上下文
            
        Raises:
            DatabaseException: 数据库连接错误
            DataNotFoundError: 数据不存在
            ServiceException: 其他数据库错误
        """
        error_str = str(e).lower()
        
        # 记录异常日志
        self._log_exception(e, context, "error")
        
        # 根据异常类型抛出不同的异常
        if "connection" in error_str or "timeout" in error_str or "connect" in error_str:
            raise DatabaseException(f"数据库连接失败: {str(e)}")
        elif "not found" in error_str or "no data" in error_str or "empty" in error_str:
            raise DataNotFoundError(f"数据库中没有找到数据: {str(e)}")
        else:
            raise DatabaseException(f"数据库操作失败: {str(e)}")

    def _get_from_database(self, symbol: str = None) -> Optional[Dict[str, Any]]:
        """
        从数据库获取股票数据

        Args:
            symbol: 股票代码，为None时获取所有股票

        Returns:
            股票数据或None

        Raises:
            DatabaseException: 数据库操作失败
            DataNotFoundError: 数据不存在
        """
        try:
            # 检查表是否存在
            if not self._check_database_table("stocks_info"):
                self.logger.warning("stocks_info 表不存在，跳过数据库查询")
                return None

            if symbol:
                # 验证股票代码格式
                self._validate_symbol(symbol)
                
                # 查询单只股票
                data = fetch_stocks_info(symbol)
                if data:
                    self.logger.info(f"从数据库获取到股票 {symbol} 的信息")
                    return data
                else:
                    # 数据不存在，返回None而不是抛出异常
                    self.logger.info(f"数据库中没有股票 {symbol} 的信息")
                    return None
            else:
                # 查询所有股票
                data = fetch_all_stocks()
                if data:
                    self.logger.info(f"从数据库获取到 {len(data)} 条股票记录")
                    return {"items": data, "count": len(data)}
                else:
                    # 数据库为空，返回None
                    self.logger.info("数据库中没有股票记录")
                    return None

        except (ValidationException, DatabaseException, DataNotFoundError):
            # 这些异常直接抛出，由全局异常处理器处理
            raise
        except Exception as e:
            # 其他异常转换为适当的异常类型
            self._handle_database_error(e, f"数据库查询: symbol={symbol}")

    def _get_from_akshare(self, func_name: str, *args, **kwargs) -> Any:
        """
        调用AKShare接口获取数据

        Args:
            func_name: AKShare函数名
            *args, **kwargs: 函数参数

        Returns:
            AKShare返回的数据

        Raises:
            ExternalServiceException: AKShare接口调用失败
            DataNotFoundError: AKShare接口返回空数据
            ValidationException: 参数验证失败
        """
        try:
            # 验证函数名
            if not func_name or not isinstance(func_name, str):
                raise ValidationException(
                    message="AKShare函数名不能为空",
                    details={"func_name": func_name}
                )
            
            # 动态调用AKShare函数
            func = getattr(ak, func_name, None)
            if func is None:
                error_msg = f"AKShare函数 {func_name} 不存在"
                self._log_exception(Exception(error_msg), f"AKShare函数检查", "error")
                raise ExternalServiceException(error_msg)

            self.logger.info(f"调用AKShare接口: {func_name}，参数: {args}, {kwargs}")
            result = func(*args, **kwargs)

            if result is None or (isinstance(result, pd.DataFrame) and result.empty):
                error_msg = f"AKShare接口 {func_name} 返回空数据"
                self._log_exception(Exception(error_msg), f"AKShare数据检查", "warning")
                raise DataNotFoundError(error_msg)

            return result

        except (ValidationException, ExternalServiceException, DataNotFoundError):
            # 这些异常直接抛出
            raise
        except Exception as e:
            # 记录异常详情
            self._log_exception(e, f"AKShare接口调用: {func_name}", "error")
            
            # 根据异常类型转换为适当的异常
            error_str = str(e).lower()
            if "timeout" in error_str or "connection" in error_str:
                raise ExternalServiceException(f"AKShare接口连接超时: {str(e)}")
            elif "network" in error_str or "http" in error_str:
                raise ExternalServiceException(f"AKShare接口网络错误: {str(e)}")
            else:
                raise ExternalServiceException(f"AKShare接口调用失败: {str(e)}")

    # ======================= 公共服务方法 =======================

    def get_stock_basic_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票基本信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            股票基本信息字典
            
        Raises:
            ValidationException: 参数验证失败
            DatabaseException: 数据库操作失败
            ExternalServiceException: 外部服务调用失败
            DataNotFoundError: 数据不存在
        """
        try:
            # 验证参数
            self._validate_symbol(symbol)
            
            # 首先尝试从数据库获取
            self.logger.info(f"尝试从数据库获取股票 {symbol} 的基本信息")
            db_data = self._get_from_database(symbol)
            
            if db_data:
                self.logger.info(f"从数据库获取到股票 {symbol} 的基本信息")
                return db_data
            
            # 如果数据库没有，尝试从AKShare获取
            self.logger.info(f"从数据库未找到股票 {symbol}，尝试从AKShare获取")
            try:
                akshare_data = self._get_from_akshare("stock_zh_a_spot_em", symbol=symbol)
                cleaned_data = self._clean_stock_data(akshare_data, "basic")
                
                if cleaned_data:
                    self.logger.info(f"从AKShare获取到股票 {symbol} 的基本信息")
                    return cleaned_data
            except DataNotFoundError:
                # AKShare也没有数据，抛出数据不存在异常
                raise DataNotFoundError(f"股票 {symbol} 的基本信息不存在")
            
            # 如果都没有数据，抛出数据不存在异常
            raise DataNotFoundError(f"无法获取股票 {symbol} 的基本信息")
            
        except (ValidationException, DatabaseException, ExternalServiceException, DataNotFoundError):
            # 这些异常直接抛出
            raise
        except Exception as e:
            # 其他异常转换为服务异常
            self._log_exception(e, f"获取股票基本信息: {symbol}", "error")
            raise ExternalServiceException(f"获取股票基本信息失败: {str(e)}")

    def get_stock_list(self, market: str = "A股") -> Dict[str, Any]:
        """
        获取股票列表
        
        Args:
            market: 市场类型（A股、港股、美股等）
            
        Returns:
            股票列表数据
            
        Raises:
            ValidationException: 参数验证失败
            ExternalServiceException: 外部服务调用失败
        """
        try:
            # 验证参数
            if not market or not isinstance(market, str):
                raise ValidationException(
                    message="市场类型不能为空",
                    details={"market": market}
                )
            
            self.logger.info(f"获取 {market} 股票列表")
            
            # 根据市场类型选择不同的AKShare函数
            if market == "A股":
                akshare_data = self._get_from_akshare("stock_info_a_code_name")
            elif market == "港股":
                akshare_data = self._get_from_akshare("stock_info_hk_code_name")
            elif market == "美股":
                akshare_data = self._get_from_akshare("stock_info_us_code_name")
            else:
                raise ValidationException(
                    message=f"不支持的市场类型: {market}",
                    details={"market": market, "supported_markets": ["A股", "港股", "美股"]}
                )
            
            cleaned_data = self._clean_stock_data(akshare_data, "list")
            
            if not cleaned_data or not cleaned_data.get("items"):
                raise DataNotFoundError(f"{market} 股票列表为空")
            
            return cleaned_data
            
        except (ValidationException, ExternalServiceException, DataNotFoundError):
            # 这些异常直接抛出
            raise
        except Exception as e:
            # 其他异常转换为服务异常
            self._log_exception(e, f"获取股票列表: market={market}", "error")
            raise ExternalServiceException(f"获取股票列表失败: {str(e)}")

    def search_stock(self, keyword: str, market: str = "A股") -> Dict[str, Any]:
        """
        搜索股票
        
        Args:
            keyword: 搜索关键词（股票代码或名称）
            market: 市场类型
            
        Returns:
            搜索结果
            
        Raises:
            ValidationException: 参数验证失败
            ExternalServiceException: 外部服务调用失败
            DataNotFoundError: 未找到匹配的股票
        """
        try:
            # 验证参数
            if not keyword or not isinstance(keyword, str):
                raise ValidationException(
                    message="搜索关键词不能为空",
                    details={"keyword": keyword}
                )
            
            if not market or not isinstance(market, str):
                raise ValidationException(
                    message="市场类型不能为空",
                    details={"market": market}
                )
            
            self.logger.info(f"搜索股票: {keyword} (市场: {market})")
            
            # 先获取股票列表
            stock_list = self.get_stock_list(market)
            all_stocks = stock_list.get("items", [])
            
            # 搜索匹配的股票
            results = []
            keyword_lower = keyword.lower()
            
            for stock in all_stocks:
                # 检查股票代码或名称是否匹配
                code_matched = stock.get("code", "").lower().find(keyword_lower) >= 0
                name_matched = stock.get("name", "").lower().find(keyword_lower) >= 0
                
                if code_matched or name_matched:
                    results.append(stock)
            
            if not results:
                raise DataNotFoundError(f"未找到匹配的股票: {keyword}")
            
            return {
                "items": results,
                "count": len(results),
                "keyword": keyword,
                "market": market
            }
            
        except (ValidationException, ExternalServiceException, DataNotFoundError):
            # 这些异常直接抛出
            raise
        except Exception as e:
            # 其他异常转换为服务异常
            self._log_exception(e, f"搜索股票: keyword={keyword}, market={market}", "error")
            raise ExternalServiceException(f"搜索股票失败: {str(e)}")
