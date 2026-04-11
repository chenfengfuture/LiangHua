# -*- coding: utf-8 -*-
"""
股权质押模块
包含股权质押相关查询接口
"""

import logging
import traceback
import time
import random
from typing import Dict, Any

import akshare as ak
import pandas as pd

from ..utils import safe_call_with_retry, _convert_dataframe_to_list

logger = logging.getLogger(__name__)


def get_stock_gpzy_profile_em() -> Dict[str, Any]:
    """
    股权质押市场概况查询接口（东方财富接口）

    接口: stock_gpzy_profile_em
    目标地址: https://data.eastmoney.com/gpzy/marketProfile.aspx
    描述: 东方财富网-数据中心-特色数据-股权质押-股权质押市场概况
    限量: 单次所有历史数据

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "gpzy_profile"
        }

    注意: 数据量可能较大，调用时请耐心等待。
    """
    logger.info("[股权质押概况] 开始查询市场概况")

    try:
        df = ak.stock_gpzy_profile_em()

        if df.empty:
            logger.warning("[股权质押概况] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "gpzy_profile"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[股权质押概况] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "gpzy_profile"
        }

    except Exception as e:
        error_msg = f"查询股权质押市场概况失败: {str(e)}"
        logger.error(f"[股权质押概况] 异常 error={error_msg}")
        logger.debug(f"[股权质押概况] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "gpzy_profile"
        }


def get_stock_gpzy_pledge_ratio_em(date: str) -> Dict[str, Any]:
    """
    上市公司质押比例查询接口（东方财富接口）

    接口: stock_gpzy_pledge_ratio_em
    目标地址: https://data.eastmoney.com/gpzy/pledgeRatio.aspx
    描述: 东方财富网-数据中心-特色数据-股权质押-上市公司质押比例
    限量: 单次返回指定交易日的所有历史数据

    输入参数:
        date: str - 交易日，格式为 "YYYYMMDD"，如 "20240906"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "gpzy_pledge_ratio"
        }

    注意: 日期参数需要根据网站提供的交易日为准，否则可能返回空数据。
    """
    if not date or not isinstance(date, str):
        return {
            "success": False,
            "data": None,
            "error": "日期参数必须为非空字符串，格式为 YYYYMMDD",
            "symbol": "gpzy_pledge_ratio"
        }

    logger.info(f"[上市公司质押比例] 开始查询 date={date}")

    try:
        df = ak.stock_gpzy_pledge_ratio_em(date=date)

        if df.empty:
            logger.warning(f"[上市公司质押比例] 返回数据为空 date={date}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "gpzy_pledge_ratio"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[上市公司质押比例] 查询成功 date={date}, 数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "gpzy_pledge_ratio"
        }

    except Exception as e:
        error_msg = f"查询上市公司质押比例失败: {str(e)}"
        logger.error(f"[上市公司质押比例] 异常 date={date}, error={error_msg}")
        logger.debug(f"[上市公司质押比例] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "gpzy_pledge_ratio"
        }


def get_stock_gpzy_individual_pledge_ratio_detail_em(symbol: str) -> Dict[str, Any]:
    """
    个股重要股东股权质押明细查询接口（东方财富接口）

    接口: stock_gpzy_company_em (原 stock_gpzy_individual_pledge_ratio_detail_em 已停用)
    目标地址: https://data.eastmoney.com/gpzy/
    描述: 东方财富网-数据中心-股权质押-个股质押明细
    限量: 单次所有历史数据

    输入参数:
        symbol: str - 股票代码，如 "603132"

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": symbol
        }
    """
    if not symbol or not isinstance(symbol, str):
        return {
            "success": False,
            "data": None,
            "error": "股票代码必须为非空字符串",
            "symbol": symbol or ""
        }

    logger.info(f"[个股质押明细] 开始查询 symbol={symbol}")

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            try:
                df = ak.stock_gpzy_company_em(symbol=symbol)
                logger.info(f"[个股质押明细] 使用 stock_gpzy_company_em 接口 symbol={symbol}")
            except (AttributeError, TypeError) as ae:
                logger.warning(f"[个股质押明细] stock_gpzy_company_em 不可用，尝试备用接口 symbol={symbol}")
                df = ak.stock_gpzy_individual_pledge_ratio_detail_em(symbol=symbol)

            if df is None or df.empty:
                logger.warning(f"[个股质押明细] 返回数据为空 symbol={symbol}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }

            data_list = _convert_dataframe_to_list(df, "[个股质押明细]")

            logger.info(f"[个股质押明细] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except Exception as e:
            error_msg = f"查询个股质押明细失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[个股质押明细] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[个股质押明细] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[个股质押明细] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_gpzy_industry_data_em() -> Dict[str, Any]:
    """
    上市公司质押比例-行业数据查询接口（东方财富接口）

    接口: stock_gpzy_industry_data_em
    目标地址: https://data.eastmoney.com/gpzy/industryData.aspx
    描述: 东方财富网-数据中心-特色数据-股权质押-上市公司质押比例-行业数据
    限量: 单次返回所有历史数据

    返回统一结构:
        {
            "success": True/False,
            "data": [...],
            "error": None 或错误信息,
            "symbol": "gpzy_industry"
        }
    """
    logger.info("[行业质押数据] 开始查询行业质押数据")

    try:
        df = ak.stock_gpzy_industry_data_em()

        if df.empty:
            logger.warning("[行业质押数据] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "gpzy_industry"
            }

        data_list = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                value = row[col]
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
                record[col] = value
            data_list.append(record)

        logger.info(f"[行业质押数据] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "gpzy_industry"
        }

    except Exception as e:
        error_msg = f"查询行业质押数据失败: {str(e)}"
        logger.error(f"[行业质押数据] 异常 error={error_msg}")
        logger.debug(f"[行业质押数据] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "gpzy_industry"
        }
