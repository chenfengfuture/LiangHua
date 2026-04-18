"""
stock_info_service.py — 股票数据查询服务

当前保留的接口：
1. get_stock_info(symbol) — 个股基础信息（东方财富 akshare 接口）
2. sync_all_stocks()      — 全市场 A 股列表同步到 stocks_info 表

其余 68 个 AkShare 查询接口已迁移至 api/stock/unity/ 各子模块。
"""

import asyncio
import logging
import random
import time
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict

import akshare as ak
import pandas as pd

# 配置日志
logger = logging.getLogger(__name__)


# ==================== 网络请求重试装饰器 ====================
# 随机User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# 需要重试的网络异常类型
NETWORK_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def get_random_user_agent() -> str:
    """获取随机User-Agent"""
    return random.choice(USER_AGENTS)


def network_retry(max_retries: int = 3, timeout: int = 15, base_delay: float = 1.0):
    """
    网络请求重试装饰器

    Args:
        max_retries: 最大重试次数，默认3次
        timeout: 超时时间（秒），默认15秒
        base_delay: 基础延迟时间（秒），默认1秒
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except NETWORK_EXCEPTIONS as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, base_delay * 0.5)
                        logger.warning(f"[network_retry] {func.__name__} 第{attempt + 1}次失败，{delay:.1f}秒后重试: {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"[network_retry] {func.__name__} 最终失败: {e}")
            raise last_exception
        return wrapper
    return decorator


def safe_call_with_retry(func: Callable, *args, max_retries: int = 3,
                         logger_name: str = "api", **kwargs) -> Any:
    """
    安全调用 akshare 接口（带重试机制）

    Args:
        func: akshare 接口函数
        *args: 位置参数
        max_retries: 最大重试次数
        logger_name: 日志名称前缀
        **kwargs: 关键字参数

    Returns:
        DataFrame 或抛出异常
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except NETWORK_EXCEPTIONS as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = 2.0 * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"[{logger_name}] 第{attempt + 1}次网络异常，{delay:.1f}秒后重试: {e}")
                time.sleep(delay)
            else:
                logger.error(f"[{logger_name}] 最终失败: {e}")
        except Exception as e:
            last_exception = e
            logger.error(f"[{logger_name}] 接口异常: {e}")
            break
    raise last_exception


def _convert_dataframe_to_list(df: pd.DataFrame, log_prefix: str = "") -> list:
    """
    将 DataFrame 转换为 list[dict]，处理特殊值类型（NaT、NaN、Timestamp 等）

    Args:
        df: pandas DataFrame
        log_prefix: 日志前缀

    Returns:
        list[dict]: 转换后的字典列表
    """
    if df is None or (hasattr(df, 'empty') and df.empty):
        return []

    data_list = []
    for _, row in df.iterrows():
        record = {}
        for col in df.columns:
            value = row[col]
            try:
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif isinstance(value, (int, float, str, bool)):
                    pass
                else:
                    value = str(value)
            except Exception as e:
                # 单个字段转换失败，使用None
                logger.debug(f"{log_prefix} 字段转换失败 col={col}: {str(e)}")
                value = None
            record[col] = value
        data_list.append(record)

    return data_list


# ═══════════════════════════════════════════════════════════════════
#  个股基础信息查询（东方财富接口）
# ═══════════════════════════════════════════════════════════════════

def get_stock_info(symbol: str) -> Dict[str, Any]:
    """
    查询指定股票代码的个股基础信息（东方财富接口）

    Args:
        symbol: 股票代码，如 "000001"（平安银行），"603777"（来伊份）

    Returns:
        统一结构字典：
        {
            "success": True/False,
            "data": { "股票简称": "平安银行", "股票代码": "000001", ... },
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

    logger.debug(f"[个股信息查询] 开始查询 symbol={symbol}")

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

            # 将列表转换为嵌套字典
            data_dict = {}
            for entry in data_list:
                if isinstance(entry, dict) and 'item' in entry and 'value' in entry:
                    data_dict[entry['item']] = entry['value']
                elif isinstance(entry, dict):
                    data_dict.update(entry)

            data_dict['symbol'] = symbol

            logger.debug(f"[个股信息查询] 查询成功 symbol={symbol}, 数据条数={len(data_list)}")

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


# ═══════════════════════════════════════════════════════════════════
#  全市场股票同步接口
# ═══════════════════════════════════════════════════════════════════

async def sync_all_stocks() -> Dict[str, Any]:
    """
    全市场股票列表同步接口（异步并发版本）
    
    整合5个新接口，异步并发抓取上证、深证、北证股票和退市股数据，
    统一字段映射后直接批量写入数据库，无需临时表。
    
    流程：
    1. 异步并发抓取5个数据源（上证、深证、北证、上证退市、深证退市）
    2. 统一字段映射：symbol, name, market, list_date, is_active
    3. 数据去重（基于symbol，活跃状态优先）
    4. 确保stocks_info表存在（不存在则自动创建）
    5. 批量Upsert：使用INSERT ... ON DUPLICATE KEY UPDATE
    6. 标记不在本次正常股票列表中的已有股票为退市（is_active=0）
    
    Returns:
        统一结构字典：
        {
            "success": True/False,
            "data": {
                "total_fetched": int,      # 接口获取总数
                "sh_stocks": int,          # 上交所股票数
                "sz_stocks": int,          # 深交所股票数  
                "bj_stocks": int,          # 北交所股票数
                "sh_delisted": int,        # 上交所退市股数
                "sz_delisted": int,        # 深交所退市股数
                "inserted": int,           # 新增数量
                "updated": int,            # 更新数量
                "delisted": int,           # 退市标记数量
                "duration_ms": int         # 耗时(毫秒)
            },
            "error": str | None
        }
    """
    import time
    start_time = time.time()
    
    try:
        # 导入新添加的5个接口
        from api.stock.unity.basic.service import (
            stock_info_bj_name_code,
            stock_info_sh_delist,
            stock_info_sh_name_code,
            stock_info_sz_delist,
            stock_info_sz_name_code,
        )
        
        logger.info("[股票同步] 开始异步全市场股票同步")
        fetch_start = time.time()
        
        # 1. 异步并发抓取5个数据源
        logger.debug("[股票同步] 异步并发抓取5个数据源...")
        
        # 定义异步任务函数
        async def fetch_sh_stocks():
            """抓取上交所股票数据"""
            try:
                result = await asyncio.to_thread(stock_info_sh_name_code, "主板A股")
                if result["success"]:
                    logger.debug(f"[股票同步] 上交所股票数据抓取成功，共 {len(result['data'])} 条")
                    return result["data"]
                else:
                    logger.warning(f"[股票同步] 上交所股票数据抓取失败: {result['error']}")
                    return []
            except Exception as e:
                logger.warning(f"[股票同步] 上交所股票数据抓取异常: {e}")
                return []
        
        async def fetch_sz_stocks():
            """抓取深交所股票数据"""
            try:
                result = await asyncio.to_thread(stock_info_sz_name_code, "A股列表")
                if result["success"]:
                    logger.debug(f"[股票同步] 深交所股票数据抓取成功，共 {len(result['data'])} 条")
                    return result["data"]
                else:
                    logger.warning(f"[股票同步] 深交所股票数据抓取失败: {result['error']}")
                    return []
            except Exception as e:
                logger.warning(f"[股票同步] 深交所股票数据抓取异常: {e}")
                return []
        
        async def fetch_bj_stocks():
            """抓取北交所股票数据（设置5秒超时）"""
            try:
                # 设置5秒超时，避免北交所接口拖慢整体同步
                result = await asyncio.wait_for(asyncio.to_thread(stock_info_bj_name_code), timeout=5.0)
                if result["success"]:
                    logger.debug(f"[股票同步] 北交所股票数据抓取成功，共 {len(result['data'])} 条")
                    return result["data"]
                else:
                    logger.warning(f"[股票同步] 北交所股票数据抓取失败: {result['error']}")
                    return []
            except asyncio.TimeoutError:
                logger.warning("[股票同步] 北交所股票数据抓取超时（5秒），返回空列表")
                return []
            except Exception as e:
                logger.warning(f"[股票同步] 北交所股票数据抓取异常: {e}")
                return []
        
        async def fetch_sh_delisted():
            """抓取上交所退市股数据"""
            try:
                result = await asyncio.to_thread(stock_info_sh_delist, "全部")
                if result["success"]:
                    logger.debug(f"[股票同步] 上交所退市股数据抓取成功，共 {len(result['data'])} 条")
                    return result["data"]
                else:
                    logger.warning(f"[股票同步] 上交所退市股数据抓取失败: {result['error']}")
                    return []
            except Exception as e:
                logger.warning(f"[股票同步] 上交所退市股数据抓取异常: {e}")
                return []
        
        async def fetch_sz_delisted():
            """抓取深交所退市股数据"""
            try:
                result = await asyncio.to_thread(stock_info_sz_delist, "终止上市公司")
                if result["success"]:
                    logger.debug(f"[股票同步] 深交所退市股数据抓取成功，共 {len(result['data'])} 条")
                    return result["data"]
                else:
                    logger.warning(f"[股票同步] 深交所退市股数据抓取失败: {result['error']}")
                    return []
            except Exception as e:
                logger.warning(f"[股票同步] 深交所退市股数据抓取异常: {e}")
                return []
        
        # 并发执行所有抓取任务
        try:
            sh_stocks, sz_stocks, bj_stocks, sh_delisted, sz_delisted = await asyncio.gather(
                fetch_sh_stocks(),
                fetch_sz_stocks(),
                fetch_bj_stocks(),
                fetch_sh_delisted(),
                fetch_sz_delisted(),
                return_exceptions=True
            )
        except Exception as e:
            logger.error(f"[股票同步] 并发抓取任务异常: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"并发抓取任务异常: {str(e)}"
            }
        
        # 处理可能的异常返回
        def safe_list(value):
            if isinstance(value, Exception):
                logger.warning(f"[股票同步] 抓取任务返回异常: {value}")
                return []
            return value
        
        sh_stocks = safe_list(sh_stocks)
        sz_stocks = safe_list(sz_stocks)
        bj_stocks = safe_list(bj_stocks)
        sh_delisted = safe_list(sh_delisted)
        sz_delisted = safe_list(sz_delisted)
        
        # 检查是否有数据
        total_data = len(sh_stocks) + len(sz_stocks) + len(bj_stocks) + len(sh_delisted) + len(sz_delisted)
        if total_data == 0:
            return {
                "success": False,
                "data": None,
                "error": "所有数据源抓取失败，没有获取到任何股票数据"
            }
        
        fetch_end = time.time()
        logger.debug(f"[股票同步] 异步抓取完成，共获取 {total_data} 条原始记录，耗时 {fetch_end - fetch_start:.2f}秒")
        
        # 2. 统一字段映射（与之前相同的映射函数）
        map_start = time.time()
        def _map_sh_stock(item):
            """映射上交所股票数据"""
            symbol = item.get("证券代码", "").strip()
            name = item.get("证券简称", "").strip()
            full_name = item.get("公司全称", "").strip()
            list_date_str = item.get("上市日期", "")
            
            # 如果symbol为空，跳过该记录
            if not symbol:
                return None
            
            # 标准化symbol
            if not symbol.endswith(".SH"):
                symbol = f"{symbol}.SH"
            
            # 解析上市日期
            list_date = None
            if list_date_str:
                try:
                    list_date = datetime.strptime(list_date_str, "%Y-%m-%d").date()
                except:
                    list_date = None
            
            return {
                "symbol": symbol,
                "name": name,
                "full_name": full_name,
                "market": "SH",
                "list_date": list_date,
                "is_active": 1
            }
        
        def _map_sz_stock(item):
            """映射深交所股票数据"""
            symbol = item.get("A股代码", "").strip()
            name = item.get("A股简称", "").strip()
            list_date_str = item.get("A股上市日期", "")
            industry = item.get("所属行业", "").strip()
            
            # 如果symbol为空，跳过该记录
            if not symbol:
                return None
            
            # 标准化symbol
            if not symbol.endswith(".SZ"):
                symbol = f"{symbol}.SZ"
            
            # 解析上市日期
            list_date = None
            if list_date_str:
                try:
                    list_date = datetime.strptime(list_date_str, "%Y-%m-%d").date()
                except:
                    list_date = None
            
            return {
                "symbol": symbol,
                "name": name,
                "market": "SZ",
                "list_date": list_date,
                "industry": industry,
                "is_active": 1
            }
        
        def _map_bj_stock(item):
            """映射北交所股票数据"""
            symbol = item.get("证券代码", "").strip()
            name = item.get("证券简称", "").strip()
            list_date_str = item.get("上市日期", "")
            industry = item.get("所属行业", "").strip()
            region = item.get("地区", "").strip()
            
            # 如果symbol为空，跳过该记录
            if not symbol:
                return None
            
            # 标准化symbol
            if not symbol.endswith(".BJ"):
                symbol = f"{symbol}.BJ"
            
            # 解析上市日期
            list_date = None
            if list_date_str:
                try:
                    list_date = datetime.strptime(list_date_str, "%Y-%m-%d").date()
                except:
                    list_date = None
            
            return {
                "symbol": symbol,
                "name": name,
                "market": "BJ",
                "list_date": list_date,
                "industry": industry,
                "region": region,
                "is_active": 1
            }
        
        def _map_sh_delisted(item):
            """映射上交所退市股数据"""
            symbol = item.get("公司代码", "").strip()
            name = item.get("公司简称", "").strip()
            list_date_str = item.get("上市日期", "")
            delist_date_str = item.get("暂停上市日期", "")
            
            # 标准化symbol
            if symbol and not symbol.endswith(".SH"):
                symbol = f"{symbol}.SH"
            
            # 解析上市日期
            list_date = None
            if list_date_str:
                try:
                    list_date = datetime.strptime(list_date_str, "%Y-%m-%d").date()
                except:
                    list_date = None
            
            # 解析退市日期
            delist_date = None
            if delist_date_str:
                try:
                    delist_date = datetime.strptime(delist_date_str, "%Y-%m-%d").date()
                except:
                    delist_date = None
            
            return {
                "symbol": symbol,
                "name": name,
                "market": "SH",
                "list_date": list_date,
                "delist_date": delist_date,
                "is_active": 0
            }
        
        def _map_sz_delisted(item):
            """映射深交所退市股数据"""
            symbol = item.get("证券代码", "").strip()
            name = item.get("证券简称", "").strip()
            list_date_str = item.get("上市日期", "")
            delist_date_str = item.get("终止上市日期", "")
            
            # 标准化symbol
            if symbol and not symbol.endswith(".SZ"):
                symbol = f"{symbol}.SZ"
            
            # 解析上市日期
            list_date = None
            if list_date_str:
                try:
                    list_date = datetime.strptime(list_date_str, "%Y-%m-%d").date()
                except:
                    list_date = None
            
            # 解析退市日期
            delist_date = None
            if delist_date_str:
                try:
                    delist_date = datetime.strptime(delist_date_str, "%Y-%m-%d").date()
                except:
                    delist_date = None
            
            return {
                "symbol": symbol,
                "name": name,
                "market": "SZ",
                "list_date": list_date,
                "delist_date": delist_date,
                "is_active": 0
            }
        
        # 3. 应用映射并去重
        logger.debug("[股票同步] 统一字段映射并去重...")
        
        # 使用字典去重，以symbol为key，保留最新的数据（活跃状态优先）
        stocks_dict = {}
        
        # 市场数据配置：每个元组包含(数据列表, 映射函数, 是否跳过空symbol)
        market_configs = [
            (sh_stocks, _map_sh_stock, True),      # 上交所股票
            (sz_stocks, _map_sz_stock, True),      # 深交所股票  
            (bj_stocks, _map_bj_stock, True),      # 北交所股票
            (sh_delisted, _map_sh_delisted, False),  # 上交所退市股
            (sz_delisted, _map_sz_delisted, False)   # 深交所退市股
        ]
        
        for data_list, map_func, skip_if_none in market_configs:
            if not data_list:
                continue
                
            for item in data_list:
                try:
                    mapped = map_func(item)
                    
                    # 处理空symbol情况
                    if skip_if_none and mapped is None:
                        continue
                    if not mapped or not mapped.get("symbol"):
                        continue
                        
                    symbol = mapped["symbol"]
                    is_active = mapped.get("is_active", 1)
                    
                    # 如果已经存在，优先保留活跃状态的数据
                    if symbol in stocks_dict:
                        existing = stocks_dict[symbol]
                        existing_active = existing.get("is_active", 1)
                        # 如果新数据是活跃的，或者旧数据是不活跃的，则替换
                        if is_active == 1 or existing_active == 0:
                            stocks_dict[symbol] = mapped
                    else:
                        stocks_dict[symbol] = mapped
                        
                except Exception as e:
                    # 根据映射函数确定市场名称用于日志
                    market_name = "未知市场"
                    if map_func == _map_sh_stock:
                        market_name = "上交所"
                    elif map_func == _map_sz_stock:
                        market_name = "深交所"
                    elif map_func == _map_bj_stock:
                        market_name = "北交所"
                    elif map_func == _map_sh_delisted:
                        market_name = "上交所退市"
                    elif map_func == _map_sz_delisted:
                        market_name = "深交所退市"
                    
                    logger.warning(f"[股票同步] 映射{market_name}股票失败: {e}, 数据: {item}")
        
        map_end = time.time()
        total_fetched = len(stocks_dict)
        active_count = sum(1 for stock in stocks_dict.values() if stock.get("is_active", 1) == 1)
        logger.debug(f"[股票同步] 映射去重完成，共 {total_fetched} 条记录，其中活跃股票 {active_count} 条，耗时 {map_end - map_start:.2f}秒")
        
        # 4. 确保表存在
        db_start = time.time()
        from models.stock_models import CREATE_STOCKS_INFO_DDL
        from utils.db import get_conn, table_exists
        
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                # 检查表是否存在，不存在则创建
                if not table_exists("stocks_info"):
                    logger.info("[股票同步] stocks_info表不存在，正在创建...")
                    cur.execute(CREATE_STOCKS_INFO_DDL)
                    conn.commit()
                    logger.info("[股票同步] stocks_info表创建成功")
                
                # 5. 批量Upsert（INSERT ... ON DUPLICATE KEY UPDATE）
                # 准备参数列表
                upsert_params = []
                for symbol, stock in stocks_dict.items():
                    upsert_params.append((
                        symbol,
                        stock.get("name"),
                        stock.get("market"),
                        stock.get("list_date"),
                        stock.get("full_name"),
                        stock.get("industry"),
                        stock.get("region"),
                        stock.get("is_active", 1)
                    ))
                
                if not upsert_params:
                    logger.warning("[股票同步] 没有数据需要写入")
                    inserted_count = 0
                    updated_count = 0
                else:
                    # 批量Upsert
                    upsert_sql = """
                    INSERT INTO stocks_info 
                    (symbol, name, market, list_date, full_name, industry, region, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        market = VALUES(market),
                        list_date = VALUES(list_date),
                        full_name = VALUES(full_name),
                        industry = VALUES(industry),
                        region = VALUES(region),
                        is_active = VALUES(is_active),
                        update_time = CURRENT_TIMESTAMP
                    """
                    
                    # 执行批量Upsert
                    logger.debug(f"[股票同步] 批量Upsert SQL: {upsert_sql}")
                    logger.debug(f"[股票同步] 批量Upsert参数数量: {len(upsert_params)}")
                    if upsert_params:
                        logger.debug(f"[股票同步] 第一个参数: {upsert_params[0]}")
                    
                    try:
                        cur.executemany(upsert_sql, upsert_params)
                        total_affected = cur.rowcount
                    except Exception as e:
                        logger.error(f"[股票同步] 批量Upsert执行失败，SQL: {upsert_sql}")
                        logger.error(f"[股票同步] 错误详情: {e}")
                        logger.error(f"[股票同步] 参数示例: {upsert_params[0] if upsert_params else '无参数'}")
                        raise
                    
                    # 由于MySQL的executemany() rowcount行为，我们估算插入和更新数量
                    # 实际项目中可能需要更精确的统计
                    inserted_count = len(upsert_params)  # 近似值，实际插入可能少于这个数
                    updated_count = total_affected - inserted_count  # 近似值
                    
                    logger.debug(f"[股票同步] 批量Upsert完成，总影响行数: {total_affected}")
                
                # 6. 标记不在本次正常股票列表中的已有股票为退市（is_active=0）
                # 正常股票列表指is_active=1的股票（不包括退市股）
                active_symbols = [symbol for symbol, stock in stocks_dict.items() 
                                 if stock.get("is_active", 1) == 1 and symbol and symbol.strip()]
                
                if active_symbols:
                    # 使用NOT IN子查询标记退市
                    placeholders = ', '.join(['%s'] * len(active_symbols))
                    delist_sql = f"""
                    UPDATE stocks_info 
                    SET is_active = 0, update_time = CURRENT_TIMESTAMP
                    WHERE is_active = 1 
                    AND symbol NOT IN ({placeholders})
                    """
                    
                    # 调试日志
                    logger.debug(f"[股票同步] 退市标记SQL: {delist_sql}")
                    logger.debug(f"[股票同步] 活跃股票数量: {len(active_symbols)}")
                    if active_symbols:
                        logger.debug(f"[股票同步] 前5个活跃股票: {active_symbols[:5]}")
                    
                    try:
                        cur.execute(delist_sql, active_symbols)
                        delisted_count = cur.rowcount
                    except Exception as e:
                        logger.error(f"[股票同步] 退市标记SQL执行失败，SQL: {delist_sql}")
                        logger.error(f"[股票同步] 错误详情: {e}")
                        logger.error(f"[股票同步] 活跃股票数量: {len(active_symbols)}")
                        raise
                    logger.debug(f"[股票同步] 标记 {delisted_count} 条记录为退市")
                else:
                    delisted_count = 0
                    logger.warning("[股票同步] 没有正常股票数据，无法执行退市标记")
                
                conn.commit()
                

        finally:
            conn.close()
        
        db_end = time.time()
        logger.debug(f"[股票同步] 数据库操作完成，耗时 {db_end - db_start:.2f}秒")
        # 计算耗时
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"[股票同步] 异步同步完成，总耗时 {duration_ms}ms")
        
        return {
            "success": True,
            "data": {
                "total_fetched": total_fetched,
                "sh_stocks": len(sh_stocks),
                "sz_stocks": len(sz_stocks),
                "bj_stocks": len(bj_stocks),
                "sh_delisted": len(sh_delisted),
                "sz_delisted": len(sz_delisted),
                "inserted": inserted_count,
                "updated": updated_count,
                "delisted": delisted_count,
                "duration_ms": duration_ms
            },
            "error": None
        }
        
    except Exception as e:
        error_msg = f"股票同步失败: {str(e)}"
        logger.error(f"[股票同步] {error_msg}")
        logger.debug(f"[股票同步] 异常详情: {traceback.format_exc()}")
        
        return {
            "success": False,
            "data": None,
            "error": error_msg
        }








