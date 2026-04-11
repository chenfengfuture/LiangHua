# -*- coding: utf-8 -*-
"""
技术选股排名模块
包含创新高、连续上涨、持续放量、向上突破等技术选股指标
"""

import logging
import traceback
import time
import random
from typing import Dict, Any

import akshare as ak

from ..utils import _convert_dataframe_to_list

logger = logging.getLogger(__name__)


def get_stock_rank_cxg_ths(symbol: str = "创月新高") -> Dict[str, Any]:
    """
    同花顺技术指标-创新高数据查询接口

    接口: stock_rank_cxg_ths
    目标地址: https://data.10jqka.com.cn/rank/cxg/
    描述: 同花顺-数据中心-技术选股-创新高
    限量: 单次指定 symbol 的所有数据

    输入参数:
        symbol: str, 创新高类型，choice of {
            "创月新高",   # 创一个月内新高
            "半年新高",   # 创半年内新高
            "一年新高",   # 创一年内新高
            "历史新高"    # 创历史新高
        }

    返回统一结构:
        { "success": bool, "data": [...], "error": None 或错误信息, "symbol": str }
    """
    valid_symbols = ["创月新高", "半年新高", "一年新高", "历史新高"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"symbol 必须为以下值之一: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[同花顺创新高] 开始查询 symbol={symbol}")

    max_retries = 3
    base_delay = 2.0

    for attempt in range(max_retries):
        try:
            df = ak.stock_rank_cxg_ths(symbol=symbol)

            if df is None or df.empty:
                logger.warning(f"[同花顺创新高] 返回数据为空 symbol={symbol}")
                return {
                    "success": True,
                    "data": [],
                    "error": None,
                    "symbol": symbol
                }

            # 动态适配列数处理
            data_list = []
            standard_columns = ['序号', '股票代码', '股票简称', '涨跌幅', '换手率',
                               '最新价', '前期高点', '前期高点日期']

            for _, row in df.iterrows():
                record = {}
                for col in df.columns:
                    if col not in standard_columns:
                        continue
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

                if record:
                    data_list.append(record)

            logger.info(f"[同花顺创新高] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

            return {
                "success": True,
                "data": data_list,
                "error": None,
                "symbol": symbol
            }

        except Exception as e:
            error_msg = f"查询同花顺创新高失败: {str(e)}"
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[同花顺创新高] 第{attempt + 1}次失败 symbol={symbol}，{delay:.1f}秒后重试: {error_msg}")
                time.sleep(delay)
                continue
            else:
                logger.error(f"[同花顺创新高] 最终失败 symbol={symbol}, error={error_msg}")
                logger.debug(f"[同花顺创新高] 异常详情: {traceback.format_exc()}")

                return {
                    "success": False,
                    "data": None,
                    "error": error_msg,
                    "symbol": symbol
                }


def get_stock_rank_lxsz_ths() -> Dict[str, Any]:
    """
    同花顺技术选股-连续上涨数据查询接口

    接口: stock_rank_lxsz_ths
    目标地址: https://data.10jqka.com.cn/rank/lxsz/
    描述: 同花顺-数据中心-技术选股-连续上涨
    限量: 单次返回所有数据

    返回统一结构:
        { "success": bool, "data": [...], "error": None 或错误信息, "symbol": "lxsz" }
    """
    logger.info("[同花顺连续上涨] 开始查询连续上涨数据")

    try:
        df = ak.stock_rank_lxsz_ths()

        if df.empty:
            logger.warning("[同花顺连续上涨] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "lxsz"
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺连续上涨]")

        logger.info(f"[同花顺连续上涨] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "lxsz"
        }

    except Exception as e:
        error_msg = f"查询同花顺连续上涨失败: {str(e)}"
        logger.error(f"[同花顺连续上涨] 异常 error={error_msg}")
        logger.debug(f"[同花顺连续上涨] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "lxsz"
        }


def get_stock_rank_cxfl_ths() -> Dict[str, Any]:
    """
    查询同花顺技术选股-持续放量数据

    接口: akshare.stock_rank_cxfl_ths
    目标地址: https://data.10jqka.com.cn/rank/cxfl/

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "cxfl" }
    """
    logger.info("[同花顺持续放量] 开始查询持续放量数据")

    try:
        df = ak.stock_rank_cxfl_ths()

        if df.empty:
            logger.warning("[同花顺持续放量] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "cxfl"
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺持续放量]")

        logger.info(f"[同花顺持续放量] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "cxfl"
        }

    except Exception as e:
        error_msg = f"查询同花顺持续放量失败: {str(e)}"
        logger.error(f"[同花顺持续放量] 异常 error={error_msg}")
        logger.debug(f"[同花顺持续放量] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "cxfl"
        }


def get_stock_rank_cxsl_ths() -> Dict[str, Any]:
    """
    查询同花顺技术选股-持续缩量数据

    接口: akshare.stock_rank_cxsl_ths
    目标地址: https://data.10jqka.com.cn/rank/cxsl/

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "cxsl" }
    """
    logger.info("[同花顺持续缩量] 开始查询持续缩量数据")

    try:
        df = ak.stock_rank_cxsl_ths()

        if df.empty:
            logger.warning("[同花顺持续缩量] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "cxsl"
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺持续缩量]")

        logger.info(f"[同花顺持续缩量] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "cxsl"
        }

    except Exception as e:
        error_msg = f"查询同花顺持续缩量失败: {str(e)}"
        logger.error(f"[同花顺持续缩量] 异常 error={error_msg}")
        logger.debug(f"[同花顺持续缩量] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "cxsl"
        }


def get_stock_rank_xstp_ths(symbol: str = "500日均线") -> Dict[str, Any]:
    """
    查询同花顺技术选股-向上突破数据

    接口: akshare.stock_rank_xstp_ths
    目标地址: https://data.10jqka.com.cn/rank/xstp/

    Args:
        symbol: 均线周期类型，choice of {"5日均线", "10日均线", "20日均线",
                  "30日均线", "60日均线", "90日均线", "250日均线", "500日均线"}

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": str }
    """
    valid_symbols = ["5日均线", "10日均线", "20日均线", "30日均线",
                     "60日均线", "90日均线", "250日均线", "500日均线"]
    if symbol not in valid_symbols:
        return {
            "success": False,
            "data": None,
            "error": f"无效的symbol参数，请选择: {valid_symbols}",
            "symbol": symbol
        }

    logger.info(f"[同花顺向上突破] 开始查询 symbol={symbol}")

    try:
        df = ak.stock_rank_xstp_ths(symbol=symbol)

        if df.empty:
            logger.warning(f"[同花顺向上突破] symbol={symbol} 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": symbol
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺向上突破]")

        logger.info(f"[同花顺向上突破] symbol={symbol} 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": symbol
        }

    except Exception as e:
        error_msg = f"查询同花顺向上突破失败: {str(e)}"
        logger.error(f"[同花顺向上突破] symbol={symbol} 异常 error={error_msg}")
        logger.debug(f"[同花顺向上突破] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": symbol
        }


def get_stock_rank_ljqs_ths() -> Dict[str, Any]:
    """
    查询同花顺技术选股-量价齐升数据

    接口: akshare.stock_rank_ljqs_ths
    目标地址: https://data.10jqka.com.cn/rank/ljqs/

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "ljqs" }
    """
    logger.info("[同花顺量价齐升] 开始查询量价齐升数据")

    try:
        df = ak.stock_rank_ljqs_ths()

        if df.empty:
            logger.warning("[同花顺量价齐升] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "ljqs"
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺量价齐升]")

        logger.info(f"[同花顺量价齐升] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "ljqs"
        }

    except Exception as e:
        error_msg = f"查询同花顺量价齐升失败: {str(e)}"
        logger.error(f"[同花顺量价齐升] 异常 error={error_msg}")
        logger.debug(f"[同花顺量价齐升] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "ljqs"
        }


def get_stock_rank_ljqd_ths() -> Dict[str, Any]:
    """
    查询同花顺技术选股-量价齐跌数据

    接口: akshare.stock_rank_ljqd_ths
    目标地址: https://data.10jqka.com.cn/rank/ljqd/

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "ljqd" }
    """
    logger.info("[同花顺量价齐跌] 开始查询量价齐跌数据")

    try:
        df = ak.stock_rank_ljqd_ths()

        if df.empty:
            logger.warning("[同花顺量价齐跌] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "ljqd"
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺量价齐跌]")

        logger.info(f"[同花顺量价齐跌] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "ljqd"
        }

    except Exception as e:
        error_msg = f"查询同花顺量价齐跌失败: {str(e)}"
        logger.error(f"[同花顺量价齐跌] 异常 error={error_msg}")
        logger.debug(f"[同花顺量价齐跌] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "ljqd"
        }


def get_stock_rank_xzjp_ths() -> Dict[str, Any]:
    """
    查询同花顺技术选股-险资举牌数据

    接口: akshare.stock_rank_xzjp_ths
    目标地址: https://data.10jqka.com.cn/financial/xzjp/

    返回统一结构：{ "success": bool, "data": list[dict] | None, "error": str | None, "symbol": "xzjp" }
    """
    logger.info("[同花顺险资举牌] 开始查询险资举牌数据")

    try:
        df = ak.stock_rank_xzjp_ths()

        if df.empty:
            logger.warning("[同花顺险资举牌] 返回数据为空")
            return {
                "success": True,
                "data": [],
                "error": None,
                "symbol": "xzjp"
            }

        data_list = _convert_dataframe_to_list(df, "[同花顺险资举牌]")

        logger.info(f"[同花顺险资举牌] 查询成功，数据条数={len(data_list)}")

        return {
            "success": True,
            "data": data_list,
            "error": None,
            "symbol": "xzjp"
        }

    except Exception as e:
        error_msg = f"查询同花顺险资举牌失败: {str(e)}"
        logger.error(f"[同花顺险资举牌] 异常 error={error_msg}")
        logger.debug(f"[同花顺险资举牌] 异常详情: {traceback.format_exc()}")

        return {
            "success": False,
            "data": None,
            "error": error_msg,
            "symbol": "xzjp"
        }
