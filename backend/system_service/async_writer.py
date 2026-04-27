#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步写入队列模块

功能：
1. 任务队列管理
2. 消费者线程池
3. 异步提交接口
4. 异常处理和日志记录

设计原则：
- 使用线程安全队列（queue.Queue）
- 支持优雅关闭（等待队列清空，终止线程）
- 内部捕获异常，记录日志，不向外抛出异常
- 队列满时立即返回失败，不阻塞
- 消费者线程捕获所有异常，避免线程崩溃
"""

import logging
import queue
import threading
import time
import atexit
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from .db_service import get_db_service

logger = logging.getLogger(__name__)


@dataclass
class WriteTask:
    """
    写入任务数据类
    
    属性：
        table_name: 表名
        data_list: 数据列表
        submit_time: 提交时间戳
        retry_count: 重试次数
    """
    table_name: str
    data_list: List[Dict[str, Any]]
    submit_time: float = None
    retry_count: int = 0
    
    def __post_init__(self):
        """初始化后处理"""
        if self.submit_time is None:
            self.submit_time = time.time()


class AsyncWriter:
    """
    异步写入服务类
    """
    
    def __init__(self, max_queue_size: int = 1000, worker_count: int = 2, 
                 max_retries: int = 3, retry_delay: float = 1.0):
        """
        初始化异步写入服务
        
        Args:
            max_queue_size: 队列最大长度，防止内存爆炸
            worker_count: 消费者线程数量
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.logger = logger
        self.max_queue_size = max_queue_size
        self.worker_count = worker_count
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 线程安全队列
        self.task_queue = queue.Queue(maxsize=max_queue_size)
        
        # 消费者线程列表
        self.workers = []
        
        # 停止标志
        self._stop_flag = False
        
        # 统计信息
        self.stats = {
            "submitted_tasks": 0,
            "processed_tasks": 0,
            "failed_tasks": 0,
            "queue_size": 0,
            "active_workers": 0,
            "queue_full_count": 0
        }
        
        # 启动消费者线程
        self._start_workers()
        
        # 注册退出处理
        atexit.register(self.shutdown)
        
        self.logger.info(f"异步写入服务初始化完成，队列大小: {max_queue_size}，工作线程: {worker_count}")
    
    def submit_async_upsert(self, table_name: str, data_list: List[Dict[str, Any]], 
                           ) -> bool:
        """
        提交异步upsert任务
        
        Args:
            table_name: 表名
            data_list: 数据列表
            
        Returns:
            True: 任务提交成功（已加入队列）
            False: 任务提交失败（队列满或其他错误）
            
        负向约束：
        - 禁止执行任何阻塞操作（如网络 I/O、数据库查询）
        - 禁止修改原始数据（应深拷贝）
        """
        if not data_list:
            self.logger.debug("跳过异步写入（数据列表为空）")
            return True
        
        # 验证参数
        if not table_name:
            self.logger.error("参数验证失败: table_name 不能为空")
            return False
        
        try:
            # 深拷贝数据，避免修改原始数据
            data_to_write = deepcopy(data_list)
            
            # 创建任务
            task = WriteTask(
                table_name=table_name,
                data_list=data_to_write,
            )
            
            # 尝试将任务放入队列（非阻塞）
            try:
                self.task_queue.put(task, block=False)
                
                # 更新统计
                self.stats["submitted_tasks"] += 1
                self.stats["queue_size"] = self.task_queue.qsize()
                
                self.logger.debug(f"异步写入任务提交成功: {table_name}, 数据量: {len(data_to_write)}")
                return True
                
            except queue.Full:
                # 队列满，记录错误
                self.stats["queue_full_count"] += 1
                self.logger.error(f"异步写入队列已满，任务提交失败: {table_name}, 队列大小: {self.max_queue_size}")
                return False
                
        except Exception as e:
            # 捕获所有异常，避免影响调用方
            self.logger.error(f"提交异步写入任务异常: {e}")
            return False
    
    def _consumer(self, thread_id: int) -> None:
        """
        消费者线程函数
        
        Args:
            thread_id: 线程ID
            
        负向约束：
        - 禁止忽略异常（必须捕获并记录）
        """
        self.logger.info(f"消费者线程 {thread_id} 启动")
        self.stats["active_workers"] += 1
        
        # 获取数据库服务
        db_service = get_db_service()
        
        while not self._stop_flag:
            try:
                # 从队列获取任务（设置超时，避免无限等待）
                try:
                    task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    # 队列为空，继续等待
                    continue
                
                # 处理任务
                try:
                    self._process_task(task, db_service)

                    # 任务处理成功
                    self.stats["processed_tasks"] += 1

                except Exception as e:
                    # 任务处理失败
                    self.logger.error(f"处理异步写入任务失败: {task.table_name}, 错误: {e}")
                finally:
                    # 标记任务完成
                    self.task_queue.task_done()

                    # 更新统计
                    self.stats["queue_size"] = self.task_queue.qsize()

            except Exception as e:
                # 捕获线程函数中的所有异常，避免线程崩溃
                self.logger.error(f"消费者线程 {thread_id} 异常: {e}")
        
        self.logger.info(f"消费者线程 {thread_id} 停止")
        self.stats["active_workers"] -= 1
    
    def _process_task(self, task: WriteTask, db_service) -> None:
        """
        处理单个写入任务
        
        Args:
            task: 写入任务
            db_service: 数据库服务实例
        """
        start_time = time.time()
        
        try:
            # 调用数据库服务进行写入
            result = db_service.upsert_data_with_schema(
                table_name=task.table_name,
                data_list=task.data_list,
            )
            
            if not result.get("success", False):
                raise Exception(f"数据库写入失败: {result.get('message', '未知错误')}")
            
            # 记录处理时间
            elapsed_time = time.time() - start_time
            self.logger.debug(f"异步写入任务处理完成: {task.table_name}, 数据量: {len(task.data_list)}, 耗时: {elapsed_time:.2f}秒")
            
        except Exception as e:
            # 重新抛出异常，由调用方处理重试逻辑
            raise
    
    def _start_workers(self) -> None:
        """启动消费者线程"""
        for i in range(self.worker_count):
            worker = threading.Thread(
                target=self._consumer,
                args=(i,),
                name=f"AsyncWriter-Worker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        self.logger.info(f"启动 {self.worker_count} 个消费者线程")
    
    def shutdown(self) -> None:
        """
        优雅关闭异步写入服务
        
        流程：
        1. 设置停止标志
        2. 等待队列清空
        3. 等待消费者线程结束
        """
        if self._stop_flag:
            return
        
        self.logger.info("开始关闭异步写入服务...")
        self._stop_flag = True
        
        # 等待队列清空
        try:
            self.task_queue.join()
            self.logger.info("队列已清空")
        except Exception as e:
            self.logger.error(f"等待队列清空异常: {e}")
        
        # 等待消费者线程结束
        for i, worker in enumerate(self.workers):
            try:
                if worker.is_alive():
                    worker.join(timeout=5.0)
                    self.logger.info(f"消费者线程 {i} 已停止")
            except Exception as e:
                self.logger.error(f"等待消费者线程 {i} 停止异常: {e}")
        
        self.logger.info("异步写入服务关闭完成")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取服务统计信息
        
        Returns:
            统计信息字典
        """
        return {
            **self.stats,
            "queue_size": self.task_queue.qsize(),
            "timestamp": time.time()
        }


# 全局异步写入服务实例
_async_writer_instance: Optional[AsyncWriter] = None
_async_writer_lock = threading.Lock()


def get_async_writer() -> AsyncWriter:
    """
    获取异步写入服务实例（单例模式）
    
    Returns:
        AsyncWriter实例
    """
    global _async_writer_instance
    if _async_writer_instance is None:
        with _async_writer_lock:
            if _async_writer_instance is None:
                _async_writer_instance = AsyncWriter()
    return _async_writer_instance


# 便捷函数
def submit_async_upsert(table_name: str, data_list: List[Dict[str, Any]], 
                       unique_keys: List[str]) -> bool:
    """
    提交异步upsert任务（便捷函数）
    
    Args:
        table_name: 表名
        data_list: 数据列表
        
    Returns:
        是否成功提交任务
    """
    return get_async_writer().submit_async_upsert(table_name, data_list)


def shutdown_async_writer() -> None:
    """关闭异步写入服务（便捷函数）"""
    if _async_writer_instance:
        _async_writer_instance.shutdown()


# 注册退出处理
atexit.register(shutdown_async_writer)


# 导出函数
__all__ = [
    "AsyncWriter",
    "WriteTask",
    "get_async_writer",
    "submit_async_upsert",
    "shutdown_async_writer",
]


# 深拷贝函数（避免导入问题）
def deepcopy(obj: Any) -> Any:
    """深拷贝函数，避免导入问题"""
    import copy
    return copy.deepcopy(obj)