#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K 线全市场采集 SSE 流式推送器

负责：
  · 采集进度实时推送到前端
  · 每只股票完成时推送结果
  · 最终汇总推送
  · 异常处理与断开重连支持
"""

import json
import threading
import time
from datetime import date, datetime
from typing import Any, Dict, Generator, List

from stock_services.common.logging import get_module_logger

log = get_module_logger("kline_sse")


class KlineSSEStreamer:
    """K 线全市场采集 SSE 流式推送器"""

    # 任务状态存储（支持多并发）
    _tasks: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()

    @classmethod
    def create_task(cls, params: Dict) -> str:
        """创建 SSE 采集任务，返回 task_id"""
        task_id = f"kline_sse_{int(time.time() * 1000)}"
        with cls._lock:
            cls._tasks[task_id] = {
                "status": "initializing",
                "params": params,
                "progress": {
                    "current": 0, "total": 0,
                    "redis_done": 0, "db_done": 0, "mootdx_done": 0,
                    "failed": 0, "records": 0
                },
                "results": {},  # symbol → {records, source, count}
                "errors": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        return task_id

    @classmethod
    def update_progress(cls, task_id: str, **kwargs):
        """更新任务进度（采集线程调用）"""
        with cls._lock:
            if task_id in cls._tasks:
                cls._tasks[task_id]["progress"].update(kwargs)
                cls._tasks[task_id]["updated_at"] = datetime.now().isoformat()

    @classmethod
    def add_stock_result(cls, task_id: str, symbol: str, records: List, source: str):
        """添加单只股票结果（采集线程调用）"""
        with cls._lock:
            if task_id in cls._tasks:
                cls._tasks[task_id]["results"][symbol] = {
                    "symbol": symbol,
                    "records": records,
                    "source": source,
                    "count": len(records)
                }

    @classmethod
    def add_error(cls, task_id: str, error: str):
        """添加错误信息（采集线程调用）"""
        with cls._lock:
            if task_id in cls._tasks:
                cls._tasks[task_id]["errors"].append(error)

    @classmethod
    def set_status(cls, task_id: str, status: str):
        """设置任务状态（采集线程调用）"""
        with cls._lock:
            if task_id in cls._tasks:
                cls._tasks[task_id]["status"] = status

    @classmethod
    def get_task_result(cls, task_id: str) -> Dict:
        """获取任务完整结果"""
        with cls._lock:
            return cls._tasks.get(task_id, {})

    @classmethod
    def stream_generator(cls, task_id: str) -> Generator[str, None, None]:
        """
        SSE 生成器（FastAPI 路由调用）

        Yields:
            SSE 格式消息：
              event: start     → 任务开始
              event: progress  → 进度更新
              event: stock     → 单只股票完成
              event: complete  → 全部完成
              event: error     → 错误
        """
        last_progress = None
        sent_stocks = set()

        # 先发送开始消息
        yield f"event: start\ndata: {json.dumps({'task_id': task_id, 'message': '开始全市场 K 线采集'}, ensure_ascii=False)}\n\n"

        # 轮询状态，实时推送
        while True:
            with cls._lock:
                task = cls._tasks.get(task_id)

            if not task:
                yield f"event: error\ndata: {json.dumps({'message': '任务不存在'}, ensure_ascii=False)}\n\n"
                break

            status = task["status"]
            progress = task["progress"]

            # 1. 推送进度更新（仅当有变化时）
            if progress != last_progress:
                yield f"event: progress\ndata: {json.dumps(progress, ensure_ascii=False)}\n\n"
                last_progress = dict(progress)

            # 2. 推送新增的股票结果
            for symbol, data in task["results"].items():
                if symbol not in sent_stocks:
                    # 只推送元数据，不推送完整 records 避免 SSE 消息过大
                    stock_meta = {k: v for k, v in data.items() if k != "records"}
                    yield f"event: stock\ndata: {json.dumps(stock_meta, ensure_ascii=False)}\n\n"
                    sent_stocks.add(symbol)

            # 3. 任务结束，推送最终结果
            if status in ("completed", "failed"):
                final_data = {
                    "task_id": task_id,
                    "status": status,
                    "total_stocks": progress["total"],
                    "completed_stocks": len(sent_stocks),
                    "failed_stocks": progress["failed"],
                    "total_records": progress["records"],
                    "source_breakdown": {
                        "redis": progress["redis_done"],
                        "db": progress["db_done"],
                        "mootdx": progress["mootdx_done"],
                    },
                    "errors": task["errors"][:20],  # 最多返回20个错误
                }
                yield f"event: complete\ndata: {json.dumps(final_data, ensure_ascii=False)}\n\n"
                break

            # 避免 CPU 空转
            time.sleep(0.1)

        # 任务完成后保留 5 分钟再清理（此处省略 TTL 自动清理逻辑）


# 模块级单例
kline_sse_streamer = KlineSSEStreamer()
