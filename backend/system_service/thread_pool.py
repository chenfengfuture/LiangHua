#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多线程并发调用模块

功能：
1. 并发执行多个独立任务（如调用 call_akshare_api 或服务函数）
2. 单个任务失败不影响其他任务
3. 收集所有任务的结果（包括成功/失败状态、数据、错误信息）
4. 支持整体超时控制
5. 支持任务重试机制

设计原则：
- 使用 concurrent.futures.ThreadPoolExecutor 实现线程池
- 统一返回格式：列表，每个元素为 {"name": str, "success": bool, "result": any, "error": str}
- 内部捕获异常，记录日志，不向外抛出异常
"""

import logging
import concurrent.futures
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, Future

# 获取模块日志器
logger = logging.getLogger(__name__)


class Task:
    """任务定义类"""
    
    def __init__(self, func: Callable, args: Tuple = (), kwargs: Dict = None, 
                 name: str = None):
        """
        初始化任务
        
        Args:
            func: 要执行的函数
            args: 位置参数元组
            kwargs: 关键字参数字典
            name: 任务名称（用于标识）
        """
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.name = name or func.__name__
        
    def execute(self) -> Any:
        """执行任务"""
        return self.func(*self.args, **self.kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "func": self.func,
            "args": self.args,
            "kwargs": self.kwargs,
            "name": self.name
        }


class ThreadPoolService:
    """线程池服务类"""
    
    def __init__(self, default_max_workers: int = 5, default_timeout: int = 60):
        """
        初始化线程池服务
        
        Args:
            default_max_workers: 默认最大工作线程数
            default_timeout: 默认整体超时时间（秒）
        """
        self.logger = logger
        self.default_max_workers = default_max_workers
        self.default_timeout = default_timeout
        
        self.logger.info(f"线程池服务初始化完成，默认配置: max_workers={default_max_workers}, timeout={default_timeout}")
    
    def run_concurrent_tasks(self, tasks: List[Dict[str, Any]], 
                            max_workers: int = None, 
                            timeout: int = None) -> List[Dict[str, Any]]:
        """
        并发执行多个任务
        
        Args:
            tasks: 任务列表，每个元素为字典 {"func": Callable, "args": tuple, "kwargs": dict, "name": str}
            max_workers: 最大并发线程数，默认使用类默认值
            timeout: 整体超时时间（秒），默认使用类默认值
            
        Returns:
            结果列表，每个元素为字典 {"name": str, "success": bool, "result": any, "error": str}
        """
        start_time = time.time()
        operation = "thread_pool_run_concurrent_tasks"
        
        # 使用默认值或传入值
        max_workers = max_workers or self.default_max_workers
        timeout = timeout or self.default_timeout
        
        # 验证参数
        if not tasks:
            self.logger.warning("任务列表为空，直接返回空列表")
            return []
        
        task_count = len(tasks)
        
        try:
            self._log_start(operation, task_count=task_count, max_workers=max_workers, timeout=timeout)
            
            # 准备结果列表
            results = []
            
            # 使用线程池执行任务
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务到线程池
                future_to_task = {}
                for task_dict in tasks:
                    try:
                        # 创建任务对象
                        task = Task(
                            func=task_dict.get("func"),
                            args=task_dict.get("args", ()),
                            kwargs=task_dict.get("kwargs", {}),
                            name=task_dict.get("name")
                        )
                        
                        # 提交任务到线程池
                        future = executor.submit(task.execute)
                        future_to_task[future] = task
                        
                    except Exception as e:
                        # 任务提交失败，记录错误结果
                        self.logger.error(f"任务提交失败: {e}")
                        results.append({
                            "name": task_dict.get("name", "unknown"),
                            "success": False,
                            "result": None,
                            "error": f"任务提交失败: {str(e)}"
                        })
                
                # 收集已完成的结果
                try:
                    # 使用 as_completed 收集结果，支持超时
                    for future in concurrent.futures.as_completed(future_to_task.keys(), timeout=timeout):
                        task = future_to_task[future]
                        
                        try:
                            # 获取任务结果
                            result = future.result()
                            
                            # 记录成功结果
                            results.append({
                                "name": task.name,
                                "success": True,
                                "result": result,
                                "error": None
                            })
                            
                            self.logger.debug(f"任务 {task.name} 执行成功")
                            
                        except Exception as e:
                            # 任务执行异常
                            error_msg = f"任务执行异常: {str(e)}"
                            self.logger.error(f"任务 {task.name} 执行失败: {e}")
                            
                            results.append({
                                "name": task.name,
                                "success": False,
                                "result": None,
                                "error": error_msg
                            })
                            
                except concurrent.futures.TimeoutError:
                    # 整体超时
                    self.logger.warning(f"任务执行整体超时 ({timeout}秒)")
                    
                    # 记录未完成的任务
                    for future, task in future_to_task.items():
                        if not future.done():
                            # 尝试取消任务
                            future.cancel()
                            
                            results.append({
                                "name": task.name,
                                "success": False,
                                "result": None,
                                "error": f"任务超时被取消 (整体超时: {timeout}秒)"
                            })
            
            # 统计执行结果
            success_count = sum(1 for r in results if r["success"])
            fail_count = len(results) - success_count
            
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_success(operation, elapsed_ms, 
                             task_count=task_count, success_count=success_count, fail_count=fail_count)
            
            return results
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(operation, e, elapsed_ms, task_count=task_count)
            
            # 返回所有任务失败的结果
            error_results = []
            for task_dict in tasks:
                error_results.append({
                    "name": task_dict.get("name", "unknown"),
                    "success": False,
                    "result": None,
                    "error": f"线程池执行异常: {str(e)}"
                })
            
            return error_results
    
    def run_concurrent_tasks_with_retry(self, tasks: List[Dict[str, Any]], 
                                       max_workers: int = None, 
                                       retries: int = 1,
                                       timeout: int = None) -> List[Dict[str, Any]]:
        """
        并发执行多个任务，支持失败重试
        
        Args:
            tasks: 任务列表，每个元素为字典 {"func": Callable, "args": tuple, "kwargs": dict, "name": str}
            max_workers: 最大并发线程数，默认使用类默认值
            retries: 重试次数（0表示不重试）
            timeout: 整体超时时间（秒），默认使用类默认值
            
        Returns:
            结果列表，每个元素为字典 {"name": str, "success": bool, "result": any, "error": str}
        """
        start_time = time.time()
        operation = "thread_pool_run_concurrent_tasks_with_retry"
        
        # 使用默认值或传入值
        max_workers = max_workers or self.default_max_workers
        timeout = timeout or self.default_timeout
        
        # 验证参数
        if not tasks:
            self.logger.warning("任务列表为空，直接返回空列表")
            return []
        
        if retries < 0:
            retries = 0
        
        task_count = len(tasks)
        
        try:
            self._log_start(operation, task_count=task_count, max_workers=max_workers, 
                           retries=retries, timeout=timeout)
            
            # 第一次执行
            first_results = self.run_concurrent_tasks(tasks, max_workers, timeout)
            
            # 统计需要重试的任务
            tasks_to_retry = []
            retry_mapping = {}  # 映射原始任务索引到重试任务列表
            
            for i, result in enumerate(first_results):
                if not result["success"] and retries > 0:
                    # 任务失败且需要重试
                    original_task = tasks[i]
                    tasks_to_retry.append(original_task)
                    retry_mapping[len(tasks_to_retry) - 1] = i
            
            # 执行重试
            retry_results = []
            if tasks_to_retry:
                self.logger.info(f"开始重试 {len(tasks_to_retry)} 个失败任务")
                
                for retry_attempt in range(1, retries + 1):
                    self.logger.info(f"重试第 {retry_attempt} 次，剩余任务: {len(tasks_to_retry)}")
                    
                    # 执行当前批次的重试
                    current_retry_results = self.run_concurrent_tasks(tasks_to_retry, max_workers, timeout)
                    
                    # 处理重试结果
                    new_tasks_to_retry = []
                    new_retry_mapping = {}
                    
                    for retry_idx, retry_result in enumerate(current_retry_results):
                        original_idx = retry_mapping[retry_idx]
                        
                        if retry_result["success"]:
                            # 重试成功，更新结果
                            first_results[original_idx] = retry_result
                            self.logger.info(f"任务 {retry_result['name']} 第 {retry_attempt} 次重试成功")
                        else:
                            # 重试仍然失败，准备下一次重试
                            if retry_attempt < retries:
                                new_tasks_to_retry.append(tasks_to_retry[retry_idx])
                                new_retry_mapping[len(new_tasks_to_retry) - 1] = original_idx
                            
                            self.logger.warning(f"任务 {retry_result['name']} 第 {retry_attempt} 次重试失败")
                    
                    # 更新待重试任务列表
                    tasks_to_retry = new_tasks_to_retry
                    retry_mapping = new_retry_mapping
                    
                    if not tasks_to_retry:
                        break
            
            # 最终统计
            success_count = sum(1 for r in first_results if r["success"])
            fail_count = len(first_results) - success_count
            
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_success(operation, elapsed_ms, 
                             task_count=task_count, success_count=success_count, 
                             fail_count=fail_count, retries=retries)
            
            return first_results
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            self._log_error(operation, e, elapsed_ms, task_count=task_count, retries=retries)
            
            # 返回错误结果
            error_results = []
            for task_dict in tasks:
                error_results.append({
                    "name": task_dict.get("name", "unknown"),
                    "success": False,
                    "result": None,
                    "error": f"带重试的线程池执行异常: {str(e)}"
                })
            
            return error_results
    
    def run_batch_tasks(self, func: Callable, task_params_list: List[Dict[str, Any]], 
                       max_workers: int = None, timeout: int = None) -> List[Dict[str, Any]]:
        """
        批量执行相同函数但参数不同的任务
        
        Args:
            func: 要执行的函数
            task_params_list: 参数列表，每个元素为 {"args": tuple, "kwargs": dict, "name": str}
            max_workers: 最大并发线程数
            timeout: 整体超时时间（秒）
            
        Returns:
            结果列表，每个元素为字典 {"name": str, "success": bool, "result": any, "error": str}
        """
        # 构建任务列表
        tasks = []
        for i, params in enumerate(task_params_list):
            task_name = params.get("name", f"{func.__name__}_{i}")
            
            tasks.append({
                "func": func,
                "args": params.get("args", ()),
                "kwargs": params.get("kwargs", {}),
                "name": task_name
            })
        
        return self.run_concurrent_tasks(tasks, max_workers, timeout)
    
    def _log_start(self, operation: str, **kwargs):
        """记录操作开始日志"""
        self.logger.info(f"开始执行 {operation}，参数: {kwargs}")
    
    def _log_success(self, operation: str, elapsed_ms: float, **kwargs):
        """记录操作成功日志"""
        self.logger.info(f"{operation} 执行成功，耗时: {elapsed_ms:.2f}ms，参数: {kwargs}")
    
    def _log_error(self, operation: str, error: Exception, elapsed_ms: float, **kwargs):
        """记录操作失败日志"""
        self.logger.error(f"{operation} 执行失败，耗时: {elapsed_ms:.2f}ms，错误: {error}，参数: {kwargs}")
    
    @staticmethod
    def _build_task_result(name: str, success: bool, result: Any = None, error: str = None) -> Dict[str, Any]:
        """构建任务结果"""
        return {
            "name": name,
            "success": success,
            "result": result,
            "error": error
        }


# 全局线程池服务实例
_thread_pool_instance: Optional[ThreadPoolService] = None


def init_thread_pool(default_max_workers: int = 5, default_timeout: int = 60) -> Dict[str, Any]:
    """
    初始化线程池服务（全局函数）
    
    Args:
        default_max_workers: 默认最大工作线程数
        default_timeout: 默认整体超时时间（秒）
        
    Returns:
        统一格式结果
    """
    global _thread_pool_instance
    
    try:
        if _thread_pool_instance is not None:
            logger.warning("线程池服务已初始化，跳过重复初始化")
            return {
                "success": True,
                "data": {"initialized": True, "default_max_workers": default_max_workers},
                "message": "线程池服务已初始化"
            }
        
        # 创建线程池服务实例
        _thread_pool_instance = ThreadPoolService(
            default_max_workers=default_max_workers,
            default_timeout=default_timeout
        )
        
        logger.info(f"线程池服务初始化成功，默认配置: max_workers={default_max_workers}, timeout={default_timeout}")
        
        return {
            "success": True,
            "data": {
                "default_max_workers": default_max_workers,
                "default_timeout": default_timeout,
                "initialized": True
            },
            "message": "线程池服务初始化成功"
        }
        
    except Exception as e:
        logger.error(f"初始化线程池服务失败: {e}")
        _thread_pool_instance = None
        
        return {
            "success": False,
            "data": None,
            "message": f"初始化线程池服务失败: {str(e)}"
        }


def run_concurrent_tasks(tasks: List[Dict[str, Any]], 
                        max_workers: int = None, 
                        timeout: int = None) -> List[Dict[str, Any]]:
    """
    并发执行多个任务（全局函数）
    
    Args:
        tasks: 任务列表，每个元素为字典 {"func": Callable, "args": tuple, "kwargs": dict, "name": str}
        max_workers: 最大并发线程数
        timeout: 整体超时时间（秒）
        
    Returns:
        结果列表，每个元素为字典 {"name": str, "success": bool, "result": any, "error": str}
    """
    global _thread_pool_instance
    
    try:
        if _thread_pool_instance is None:
            # 自动初始化（使用默认配置）
            init_result = init_thread_pool()
            if not init_result["success"]:
                logger.error(f"线程池服务自动初始化失败: {init_result['message']}")
                # 返回失败结果
                error_results = []
                for task_dict in tasks:
                    error_results.append({
                        "name": task_dict.get("name", "unknown"),
                        "success": False,
                        "result": None,
                        "error": f"线程池服务初始化失败: {init_result['message']}"
                    })
                return error_results
        
        return _thread_pool_instance.run_concurrent_tasks(tasks, max_workers, timeout)
        
    except Exception as e:
        logger.error(f"执行并发任务失败: {e}")
        
        # 返回错误结果
        error_results = []
        for task_dict in tasks:
            error_results.append({
                "name": task_dict.get("name", "unknown"),
                "success": False,
                "result": None,
                "error": f"并发任务执行异常: {str(e)}"
            })
        
        return error_results


def run_concurrent_tasks_with_retry(tasks: List[Dict[str, Any]], 
                                   max_workers: int = None, 
                                   retries: int = 1,
                                   timeout: int = None) -> List[Dict[str, Any]]:
    """
    并发执行多个任务，支持失败重试（全局函数）
    
    Args:
        tasks: 任务列表，每个元素为字典 {"func": Callable, "args": tuple, "kwargs": dict, "name": str}
        max_workers: 最大并发线程数
        retries: 重试次数
        timeout: 整体超时时间（秒）
        
    Returns:
        结果列表，每个元素为字典 {"name": str, "success": bool, "result": any, "error": str}
    """
    global _thread_pool_instance
    
    try:
        if _thread_pool_instance is None:
            # 自动初始化（使用默认配置）
            init_result = init_thread_pool()
            if not init_result["success"]:
                logger.error(f"线程池服务自动初始化失败: {init_result['message']}")
                # 返回失败结果
                error_results = []
                for task_dict in tasks:
                    error_results.append({
                        "name": task_dict.get("name", "unknown"),
                        "success": False,
                        "result": None,
                        "error": f"线程池服务初始化失败: {init_result['message']}"
                    })
                return error_results
        
        return _thread_pool_instance.run_concurrent_tasks_with_retry(
            tasks, max_workers, retries, timeout
        )
        
    except Exception as e:
        logger.error(f"执行带重试的并发任务失败: {e}")
        
        # 返回错误结果
        error_results = []
        for task_dict in tasks:
            error_results.append({
                "name": task_dict.get("name", "unknown"),
                "success": False,
                "result": None,
                "error": f"带重试的并发任务执行异常: {str(e)}"
            })
        
        return error_results


def run_batch_tasks(func: Callable, task_params_list: List[Dict[str, Any]], 
                   max_workers: int = None, timeout: int = None) -> List[Dict[str, Any]]:
    """
    批量执行相同函数但参数不同的任务（全局函数）
    
    Args:
        func: 要执行的函数
        task_params_list: 参数列表，每个元素为 {"args": tuple, "kwargs": dict, "name": str}
        max_workers: 最大并发线程数
        timeout: 整体超时时间（秒）
        
    Returns:
        结果列表，每个元素为字典 {"name": str, "success": bool, "result": any, "error": str}
    """
    global _thread_pool_instance
    
    try:
        if _thread_pool_instance is None:
            # 自动初始化（使用默认配置）
            init_result = init_thread_pool()
            if not init_result["success"]:
                logger.error(f"线程池服务自动初始化失败: {init_result['message']}")
                # 返回失败结果
                error_results = []
                for i, params in enumerate(task_params_list):
                    task_name = params.get("name", f"{func.__name__}_{i}")
                    error_results.append({
                        "name": task_name,
                        "success": False,
                        "result": None,
                        "error": f"线程池服务初始化失败: {init_result['message']}"
                    })
                return error_results
        
        return _thread_pool_instance.run_batch_tasks(func, task_params_list, max_workers, timeout)
        
    except Exception as e:
        logger.error(f"执行批量任务失败: {e}")
        
        # 返回错误结果
        error_results = []
        for i, params in enumerate(task_params_list):
            task_name = params.get("name", f"{func.__name__}_{i}")
            error_results.append({
                "name": task_name,
                "success": False,
                "result": None,
                "error": f"批量任务执行异常: {str(e)}"
            })
        
        return error_results


# 便捷函数别名
thread_pool = {
    "init": init_thread_pool,
    "run": run_concurrent_tasks,
    "run_with_retry": run_concurrent_tasks_with_retry,
    "run_batch": run_batch_tasks
}


__all__ = [
    "ThreadPoolService",
    "Task",
    "init_thread_pool",
    "run_concurrent_tasks",
    "run_concurrent_tasks_with_retry",
    "run_batch_tasks",
    "thread_pool"
]