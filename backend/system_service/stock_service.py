#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票核心业务服务模块

将股票业务逻辑从路由层抽离，实现清晰的关注点分离：
- 路由层：HTTP请求处理、参数验证、响应组装
- 服务层：核心业务逻辑、数据操作、业务规则

遵循依赖注入原则，通过FastAPI的Depends()传递服务实例。
"""

import math
import queue
import threading
import time as _time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import Depends

# 核心工具（全局连接池）
from utils.db import get_conn
from utils.collector import get_mootdx_client


class StockDataService:
    """股票数据核心服务"""
    
    def __init__(self):
        # 交易时间序列
        self._TRADING_TIMES = self._gen_trading_times()
        
        # 内存缓存：已存在的分笔分表名
        self._known_trans_tables: set = set()
        self._known_trans_tables_loaded = False
        
        # 异步写入队列（分笔成交数据批量异步写入）
        self._trans_write_queue = queue.Queue()
        self._trans_write_thread = None
        self._trans_write_lock = threading.Lock()
    
    # ─── 工具函数 ─────────────────────────────────────────────────────────────────
    
    def _date_str_to_mootdx(self, date_str: str) -> str:
        """
        日期格式转换：YYYY-MM-DD → YYYYMMDD
        
        参数：
            date_str: 日期字符串，格式为YYYY-MM-DD
            
        返回：
            转换后的日期字符串，格式为YYYYMMDD
            
        示例：
            _date_str_to_mootdx("2024-04-15") → "20240415"
        """
        return date_str.replace('-', '')
    
    def safe_float(self, val) -> Optional[float]:
        """
        安全地将值转换为浮点数
        
        参数：
            val: 要转换的值
            
        返回：
            转换后的浮点数，如果转换失败或值为NaN/Inf则返回None
            
        处理逻辑：
            1. 如果值为None，返回None
            2. 尝试转换为浮点数
            3. 检查是否为NaN或Inf
            4. 四舍五入到4位小数
        """
        if val is None:
            return None
        try:
            f = float(val)
            return None if math.isnan(f) or math.isinf(f) else round(f, 4)
        except:
            return None
    
    def get_table_names(self, start_year: int, end_year: int) -> List[str]:
        """
        根据年份范围返回需要查询的表名列表
        
        参数：
            start_year: 起始年份
            end_year: 结束年份
            
        返回：
            表名列表，格式为["stock_klines_2024", "stock_klines_2025", ...]
            
        示例：
            get_table_names(2024, 2025) → ["stock_klines_2024", "stock_klines_2025"]
        """
        return [f"stock_klines_{y}" for y in range(start_year, end_year + 1)]
    
    # ─── A股交易时间序列 ──────────────────────────────────────────────────────────
    
    def _gen_trading_times(self) -> List[str]:
        """
        生成 A 股完整交易时间序列，共 240 分钟
        
        返回：
            时间序列列表，格式为["09:31", "09:32", ..., "15:00"]
            
        交易时间规则：
            上午：9:31 - 11:30（119分钟）
            下午：13:01 - 15:00（121分钟）
            总计：240分钟
        """
        times = []
        
        # 上午交易时间：9:31 - 11:30
        for h in range(9, 12):
            s_min = 31 if h == 9 else 0
            e_min = 30 if h == 11 else 60
            for m in range(s_min, e_min + 1 if h == 11 else e_min):
                times.append(f"{h:02d}:{m:02d}")
        
        # 下午交易时间：13:01 - 15:00
        for h in range(13, 16):
            s_min = 1 if h == 13 else 0
            e_min = 0 if h == 15 else 60
            if h == 15:
                times.append("15:00")
                break
            for m in range(s_min, 60):
                times.append(f"{h:02d}:{m:02d}")
        
        return times[:240]
    
    # ─── 异步写入队列管理 ──────────────────────────────────────────────────────────
    
    def _trans_write_worker(self):
        """
        后台线程：批量异步写入分笔成交数据
        
        工作流程：
            1. 从队列中批量获取数据（最多500条或等待1秒）
            2. 按表（股票代码+日期）分组数据
            3. 批量写入数据库
            4. 循环处理，直到收到终止信号（None）
        """
        while True:
            try:
                batch = []
                start_time = _time.time()
                
                # 批量获取数据
                while len(batch) < 500:
                    try:
                        item = self._trans_write_queue.get(timeout=0.1)
                        if item is None:  # 终止信号
                            return
                        batch.append(item)
                    except queue.Empty:
                        if batch and (_time.time() - start_time) > 1:
                            break
                        continue

                if batch:
                    # 按表分组
                    by_table = defaultdict(list)
                    for item in batch:
                        key = (item['symbol'], item['date'])
                        by_table[key].append(item['records'])

                    # 批量写入
                    for (symbol, date_str), records_list in by_table.items():
                        all_records = []
                        for r in records_list:
                            all_records.extend(r)
                        self._db_save_transactions(symbol, date_str, all_records)

            except Exception as e:
                print(f"[trans_worker] error: {e}")
    
    def _start_trans_worker(self):
        """
        启动异步写入线程（懒启动）
        
        线程管理：
            - 单例模式，确保只有一个写入线程
            - 守护线程，主程序退出时自动结束
            - 线程安全启动
        """
        with self._trans_write_lock:
            if self._trans_write_thread is None or not self._trans_write_thread.is_alive():
                self._trans_write_thread = threading.Thread(
                    target=self._trans_write_worker,
                    daemon=True
                )
                self._trans_write_thread.start()
                print("[trans_worker] started")
    
    def enqueue_save_transactions(self, symbol: str, trade_date: str, records: list):
        """
        将分笔数据加入异步写入队列
        
        参数：
            symbol: 股票代码
            trade_date: 交易日期（YYYY-MM-DD格式）
            records: 分笔数据记录列表
            
        流程：
            1. 检查记录是否为空
            2. 启动写入线程（如果未启动）
            3. 将数据加入队列
        """
        if not records:
            return
        
        self._start_trans_worker()
        self._trans_write_queue.put({
            'symbol': symbol,
            'date': trade_date,
            'records': records
        })
    
    # ─── 分时数据 DB 操作 ─────────────────────────────────────────────────────────
    
    def _db_query_minutes(self, symbol: str, trade_date: str) -> Optional[List[Dict[str, Any]]]:
        """
        查询日内分时数据缓存
        
        参数：
            symbol: 股票代码
            trade_date: 交易日期（YYYY-MM-DD格式）
            
        返回：
            分时数据列表，每个元素包含：
                - time: 时间标签（HH:MM格式）
                - price: 价格
                - vol: 成交量
                - avg_price: 均价
            如果无数据则返回None
        """
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT minute_idx, time_label, price, vol, avg_price "
                    "FROM intraday_minutes "
                    "WHERE symbol=%s AND trade_date=%s "
                    "ORDER BY minute_idx ASC",
                    (symbol, trade_date)
                )
                rows = cur.fetchall()
            
            if not rows:
                return None
            
            return [
                {
                    "time":      r["time_label"],
                    "price":     self.safe_float(r["price"]),
                    "vol":       int(r["vol"]),
                    "avg_price": self.safe_float(r["avg_price"]),
                }
                for r in rows
            ]
        finally:
            conn.close()
    
    def _db_save_minutes(self, symbol: str, trade_date: str, records: list):
        """
        批量插入日内分时数据，忽略重复记录
        
        参数：
            symbol: 股票代码
            trade_date: 交易日期（YYYY-MM-DD格式）
            records: 分时数据记录列表
            
        数据库表结构：
            - symbol: 股票代码
            - trade_date: 交易日期
            - time_label: 时间标签
            - minute_idx: 分钟索引
            - price: 价格
            - vol: 成交量
            - avg_price: 均价
        """
        if not records:
            return
        
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                sql = (
                    "INSERT IGNORE INTO intraday_minutes "
                    "(symbol, trade_date, time_label, minute_idx, price, vol, avg_price) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
                )
                data = [
                    (
                        symbol,
                        trade_date,
                        r["time"],
                        i,
                        r["price"] or 0,
                        r["vol"] or 0,
                        r["avg_price"] or 0
                    )
                    for i, r in enumerate(records)
                ]
                cur.executemany(sql, data)
            conn.commit()
        finally:
            conn.close()
    
    # ─── 分笔数据 DB 操作 ─────────────────────────────────────────────────────────
    
    def _load_known_trans_tables(self, cur):
        """
        首次调用时加载所有已存在分表名到内存
        
        参数：
            cur: 数据库游标
            
        作用：
            缓存已存在的分笔分表名，避免重复查询数据库
            提高分表存在性检查的性能
        """
        if self._known_trans_tables_loaded:
            return
        
        cur.execute(
            "SELECT TABLE_NAME FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA='lianghua' AND TABLE_NAME LIKE 'intraday_transactions_%'"
        )
        for row in cur.fetchall():
            self._known_trans_tables.add(row["TABLE_NAME"])
        
        self._known_trans_tables_loaded = True
    
    def _trans_table(self, trade_date: str) -> str:
        """
        根据交易日期生成分笔分表名
        
        参数：
            trade_date: 交易日期（YYYY-MM-DD格式）
            
        返回：
            分表名，格式为"intraday_transactions_YYYYMMDD"
            
        示例：
            _trans_table("2024-04-15") → "intraday_transactions_20240415"
        """
        return "intraday_transactions_" + trade_date.replace("-", "")
    
    def _ensure_trans_table(self, cur, table_name: str):
        """
        如果分笔分表不存在则自动创建
        
        参数：
            cur: 数据库游标
            table_name: 表名
            
        表结构说明：
            - id: 自增主键
            - symbol: 股票代码
            - trade_time: 成交时间（HH:MM:SS）
            - seq: 同秒序号
            - price: 成交价格
            - vol: 成交量
            - side: 买卖方向（B买入/S卖出/N中性）
            - created_at: 创建时间
            
        索引：
            - uq_sym_time_seq: 唯一索引，防止重复记录
            - idx_sym_time: 查询索引，提高查询性能
        """
        if table_name in self._known_trans_tables:
            return
        
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS `{table_name}` (
              `id`         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
              `symbol`     VARCHAR(10) NOT NULL,
              `trade_time` CHAR(8)     NOT NULL COMMENT '成交时间 HH:MM:SS',
              `seq`        SMALLINT UNSIGNED NOT NULL DEFAULT 0 COMMENT '同秒序号',
              `price`      DECIMAL(10,4) NOT NULL DEFAULT 0,
              `vol`        INT UNSIGNED  NOT NULL DEFAULT 0,
              `side`       CHAR(1)       NOT NULL DEFAULT 'N' COMMENT 'B买入/S卖出/N中性',
              `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
              UNIQUE KEY `uq_sym_time_seq` (`symbol`, `trade_time`, `seq`),
              KEY `idx_sym_time` (`symbol`, `trade_time`)
            ) ENGINE=InnoDB COMMENT='股票日内分笔成交明细缓存（按天分表）'
        """)
        self._known_trans_tables.add(table_name)
    
    def _db_query_transactions(self, symbol: str, trade_date: str, limit: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """
        从按天分表查询分笔缓存
        
        参数：
            symbol: 股票代码
            trade_date: 交易日期（YYYY-MM-DD格式）
            limit: 查询限制数量，None表示查询全部
            
        返回：
            分笔数据列表，每个元素包含：
                - time: 成交时间
                - price: 成交价格
                - vol: 成交量
                - side: 买卖方向
            如果表不存在或无数据则返回None
        """
        table = self._trans_table(trade_date)
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                self._load_known_trans_tables(cur)
                if table not in self._known_trans_tables:
                    return None

                # 检查表中是否有该股票的数据
                cur.execute(f"SELECT 1 FROM `{table}` WHERE symbol=%s LIMIT 1", (symbol,))
                if not cur.fetchone():
                    return None

                # 执行查询
                if limit is None:
                    cur.execute(
                        f"SELECT trade_time, price, vol, side FROM `{table}` WHERE symbol=%s "
                        f"ORDER BY trade_time ASC, seq ASC", (symbol,)
                    )
                else:
                    cur.execute(
                        f"SELECT trade_time, price, vol, side FROM `{table}` WHERE symbol=%s "
                        f"ORDER BY trade_time DESC, seq DESC LIMIT %s", (symbol, limit)
                    )
                rows = cur.fetchall()
            
            # 如果有限制，需要反转结果（因为查询时按DESC排序）
            if limit is not None:
                rows.reverse()
            
            return [
                {
                    "time": r["trade_time"],
                    "price": self.safe_float(r["price"]),
                    "vol": int(r["vol"]),
                    "side": r["side"]
                }
                for r in rows
            ]
        finally:
            conn.close()
    
    def _db_save_transactions(self, symbol: str, trade_date: str, records: list):
        """
        批量写入分笔成交到按天分表
        
        参数：
            symbol: 股票代码
            trade_date: 交易日期（YYYY-MM-DD格式）
            records: 分笔数据记录列表
            
        处理逻辑：
            1. 检查记录是否为空
            2. 生成同秒序号
            3. 批量插入数据（分批处理，每批1000条）
            4. 统计插入数量
        """
        if not records:
            return
        
        seq_counter = defaultdict(int)
        table = self._trans_table(trade_date)
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                self._ensure_trans_table(cur, table)
                sql = f"INSERT IGNORE INTO `{table}` (symbol, trade_time, seq, price, vol, side) VALUES (%s, %s, %s, %s, %s, %s)"
                
                # 准备数据
                data = []
                for r in records:
                    t = r["time"] or "00:00:00"
                    seq = seq_counter[t]
                    seq_counter[t] += 1
                    data.append((
                        symbol,
                        t,
                        seq,
                        r["price"] or 0,
                        r["vol"] or 0,
                        r["side"] or "N"
                    ))

                # 分批插入
                batch_size = 1000
                total_inserted = 0
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    cur.executemany(sql, batch)
                    total_inserted += cur.rowcount
                
                conn.commit()
                print(f"[trans] saved {len(data)} rows (inserted {total_inserted}) → {table}")
        
        except Exception as e:
            print(f"[trans] save error: {e}")
        finally:
            conn.close()


class StockInfoService:
    """股票信息服务"""
    
    def __init__(self):
        pass
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取股票基本信息（占位实现，实际业务由 StockBasicService 提供）
        
        参数：
            symbol: 股票代码
            
        返回：
            股票基本信息字典
        """
        # 占位实现，暂返回示例数据；实际业务请使用 StockBasicService.get_stock_info_em()
        return {
            "symbol": symbol,
            "name": "示例股票",
            "status": "active"
        }
    
    def sync_all_stocks(self) -> Dict[str, Any]:
        """
        同步全市场股票信息（占位实现，实际同步逻辑在 stock_info_service 中）
        
        返回：
            同步结果字典
        """
        # 占位实现，暂返回示例数据；实际业务请使用 stock_info_service.sync_all_stocks()
        return {
            "success": True,
            "message": "同步完成",
            "count": 5502
        }


class StockLLMService:
    """股票LLM分析服务"""
    
    def __init__(self):
        pass
    
    def get_analyzer(self):
        """
        获取LLM分析器（占位实现，实际分析器由 StockLLMAnalyzer 提供）
        
        返回：
            LLM分析器实例
        """
        # 占位实现，暂返回示例数据；实际业务请使用 stock_llm.get_analyzer()
        return {
            "analyzer": "stock_llm_analyzer",
            "status": "ready"
        }
    
    def initialize_service(self):
        """
        初始化LLM服务（占位实现，实际初始化逻辑在 stock_llm.initialize_service() 中）
        
        返回：
            初始化结果
        """
        # 占位实现，暂返回示例数据；实际业务请使用 stock_llm.initialize_service()
        return {
            "success": True,
            "message": "LLM服务初始化完成"
        }


class StockLHBService:
    """股票龙虎榜服务"""
    
    def __init__(self):
        # 导入龙虎榜服务模块
        from api.stock.services.stock_lhb_service import StockLHBService as LHBSpecificService
        self.lhb_specific_service = LHBSpecificService()
    
    def get_lhb_data(self, symbol: str = None, date: str = None) -> Dict[str, Any]:
        """
        获取龙虎榜数据
        
        参数：
            symbol: 股票代码（可选）
            date: 日期（可选）
            
        返回：
            龙虎榜数据
        """
        try:
            # 获取今天的日期作为默认结束日期
            from datetime import datetime, timedelta
            end_date = datetime.now().strftime("%Y%m%d")
            
            # 如果提供了日期参数，使用该日期作为查询范围
            if date:
                # 将YYYY-MM-DD格式转换为YYYYMMDD格式
                query_date = date.replace("-", "")
                # 查询该日期前后3天的数据
                start_date = (datetime.strptime(query_date, "%Y%m%d") - timedelta(days=3)).strftime("%Y%m%d")
                end_date = (datetime.strptime(query_date, "%Y%m%d") + timedelta(days=3)).strftime("%Y%m%d")
            else:
                # 默认查询最近7天的数据
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
            
            # 调用龙虎榜详情接口
            result = self.lhb_specific_service.get_lhb_detail(start_date, end_date, symbol or "lhb_data")
            
            # 如果提供了股票代码，过滤数据
            if symbol and result.get("success") and result.get("data"):
                filtered_data = []
                for item in result["data"]:
                    # 检查是否有股票代码字段
                    if "symbol" in item and item["symbol"] == symbol:
                        filtered_data.append(item)
                    elif "代码" in item and item["代码"] == symbol:
                        filtered_data.append(item)
                    elif "股票代码" in item and item["股票代码"] == symbol:
                        filtered_data.append(item)
                
                if filtered_data:
                    result["data"] = filtered_data
                    result["message"] = f"找到 {len(filtered_data)} 条关于 {symbol} 的龙虎榜记录"
                else:
                    result["data"] = []
                    result["message"] = f"未找到关于 {symbol} 的龙虎榜记录"
            
            return result
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "data": None,
                "error": f"获取龙虎榜数据失败: {str(e)}",
                "symbol": symbol,
                "date": date,
                "traceback": traceback.format_exc()
            }


# ─── 依赖注入函数 ──────────────────────────────────────────────────────────────

def get_stock_data_service() -> StockDataService:
    """获取股票数据服务实例"""
    return StockDataService()


def get_stock_info_service() -> StockInfoService:
    """获取股票信息服务实例"""
    return StockInfoService()


def get_stock_llm_service() -> StockLLMService:
    """获取股票LLM分析服务实例"""
    return StockLLMService()


def get_stock_lhb_service() -> StockLHBService:
    """获取股票龙虎榜服务实例"""
    return StockLHBService()