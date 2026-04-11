# -*- coding: utf-8 -*-
"""
股票基本信息模块
包含个股基础信息查询接口
"""

import json
import logging
import traceback
import time
import random
from typing import Dict, Any

import akshare as ak
import pandas as pd

from ..utils import safe_call_with_retry, _convert_dataframe_to_list

logger = logging.getLogger(__name__)


def get_stock_info(symbol: str) -> Dict[str, Any]:
    """
    查询指定股票代码的个股基础信息（东方财富接口）

    Args:
        symbol: 股票代码，如 "000001"（平安银行），"603777"（来伊份）

    Returns:
        统一结构字典：
        {
            "success": True/False,
            "data": {
                "item": ...,
                "value": ...,
            },
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

    logger.info(f"[个股信息查询] 开始查询 symbol={symbol}")

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            df = safe_call_with_retry(
                ak.stock_individual_info_em,
                symbol=symbol,
                max_retries=1,
                logger_name="个股信息查询"
            )

            data_list = []
            if df is not None and not df.empty:
                if 'item' in df.columns and 'value' in df.columns:
                    for _, row in df.iterrows():
                        item = row['item']
                        value = row['value']
                        if isinstance(value, (int, float, str, bool, type(None))):
                            pass
                        else:
                            value = str(value)
                        data_list.append({"item": item, "value": value})
                else:
                    data_list = df.to_dict(orient='records')

            data_dict = {}
            for entry in data_list:
                if isinstance(entry, dict) and 'item' in entry and 'value' in entry:
                    key = entry['item']
                    val = entry['value']
                    data_dict[key] = val
                elif isinstance(entry, dict):
                    data_dict.update(entry)

            data_dict['symbol'] = symbol

            logger.info(f"[个股信息查询] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_dict,
                "error": None,
                "symbol": symbol
            }

        except Exception as e:
            error_msg = f"查询个股信息失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[个股信息查询] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[个股信息查询] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[个股信息查询] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_info_json(symbol: str) -> str:
    """
    查询个股信息并返回 JSON 字符串（方便直接返回 HTTP 响应）

    Args:
        symbol: 股票代码

    Returns:
        JSON 字符串，包含统一结构
    """
    result = get_stock_info(symbol)
    return json.dumps(result, ensure_ascii=False, indent=2)


def get_stock_individual_basic_info_xq(symbol: str) -> Dict[str, Any]:
    """
    查询雪球财经-个股-公司概况

    接口: akshare.stock_individual_basic_info_xq
    目标地址: https://xueqiu.com/snowman/S/SH601127/detail#/GSJJ

    描述: 雪球财经-个股-公司概况-公司简介

    Args:
        symbol: 股票代码，需带市场前缀，如 "SH601127"

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }

    使用说明：
        1. 提供公司基本信息、公司简介等数据
        2. 数据格式为键值对形式
        3. 可用于获取公司基本信息补充
    """
    if not symbol:
        return {
            "success": False,
            "data": None,
            "error": "股票代码不能为空",
            "symbol": ""
        }

    logger.info(f"[雪球公司概况] 开始查询 symbol={symbol}")

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            result = ak.stock_individual_basic_info_xq(symbol=symbol)

            if result is None:
                logger.warning(f"[雪球公司概况] symbol={symbol} 返回为None")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }

            if hasattr(result, 'empty'):
                df = result
                if df is None or len(df) == 0:
                    logger.warning(f"[雪球公司概况] symbol={symbol} 返回数据为空")
                    return {
                        "success": True,
                        "data": [],
                        "error": None,
                        "symbol": symbol
                    }
                data_list = _convert_dataframe_to_list(df, "[雪球公司概况]")

            elif isinstance(result, dict):
                data_list = [result] if result else []

            elif isinstance(result, list):
                data_list = result

            else:
                data_list = []

            logger.info(f"[雪球公司概况] symbol={symbol} 查询成功，数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except KeyError as ke:
            error_msg = f"雪球接口返回数据格式异常: {str(ke)}"
            logger.warning(f"[雪球公司概况] symbol={symbol} 接口返回格式异常: {error_msg}")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }
        except Exception as e:
            error_msg = f"查询雪球公司概况失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[雪球公司概况] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[雪球公司概况] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[雪球公司概况] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }
