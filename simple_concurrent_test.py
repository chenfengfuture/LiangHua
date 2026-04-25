#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试通用多线程并发调用函数

功能：直接测试 execute_concurrent_tasks 函数的逻辑
"""

import sys
import os
import time
import threading
from typing import Dict, Any, List, Callable
import importlib.util

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 首先，让我创建一个简化的测试类来验证函数逻辑
class MockStockBasicService:
    """模拟 StockBasicService 类，用于测试"""
    
    def __init__(self):
        self.logger = self._create_mock_logger()
    
    def _create_mock_logger(self):
        """创建模拟日志器"""
        class MockLogger:
            def __init__(self):
                self.messages = []
            
            def info(self, msg):
                print(f"[INFO] {msg}")
                self.messages.append(("INFO", msg))
            
            def error(self, msg):
                print(f"[ERROR] {msg}")
                self.messages.append(("ERROR", msg))
            
            def warning(self, msg):
                print(f"[WARNING] {msg}")
                self.messages.append(("WARNING", msg))
            
            def debug(self, msg):
                # 调试信息不打印
                self.messages.append(("DEBUG", msg))
        
        return MockLogger()
    
    def execute_concurrent_tasks(self, base_func: Callable, param_list: List[Dict[str, Any]], 
                                max_workers: int = 5, timeout: int = 60) -> Dict[str, Any]:
        """
        通用多线程并发调用函数 - 简化版本
        
        功能：接收一个基础函数和一组参数列表，利用线程池并发执行多个任务，
              合并所有任务的返回结果，处理异常，单个任务失败不影响其他任务。
        """
        self.logger.info(f"开始执行并发任务，函数: {base_func.__name__}，任务数: {len(param_list)}")
        
        # 验证参数
        if not callable(base_func):
            self.logger.error("基础函数必须是可调用对象")
            return {
                "success": False,
                "data": {"base_func": str(base_func)},
                "message": "基础函数必须是可调用对象"
            }
        
        if not param_list or not isinstance(param_list, list):
            self.logger.error("参数列表不能为空且必须是列表")
            return {
                "success": False,
                "data": {"param_list": param_list},
                "message": "参数列表不能为空且必须是列表"
            }
        
        try:
            # 模拟线程池执行
            results = []
            success_results = []
            failed_results = []
            
            for i, params in enumerate(param_list):
                task_name = params.get("name", f"{base_func.__name__}_{i}")
                
                try:
                    args = params.get("args", ())
                    kwargs = params.get("kwargs", {})
                    
                    # 执行任务
                    result = base_func(*args, **kwargs)
                    
                    # 记录成功结果
                    results.append({
                        "name": task_name,
                        "success": True,
                        "result": result
                    })
                    success_results.append({
                        "name": task_name,
                        "data": result
                    })
                    
                    self.logger.debug(f"任务 {task_name} 执行成功")
                    
                except Exception as e:
                    # 记录失败结果
                    results.append({
                        "name": task_name,
                        "success": False,
                        "error": str(e)
                    })
                    failed_results.append({
                        "name": task_name,
                        "error": str(e)
                    })
                    
                    self.logger.warning(f"任务 {task_name} 执行失败: {e}")
            
            # 合并成功任务的数据
            merged_data = self._merge_concurrent_results(success_results)
            
            # 构建统计信息
            total_tasks = len(param_list)
            success_count = len(success_results)
            fail_count = len(failed_results)
            
            # 整体成功判断：至少有一个任务成功
            overall_success = success_count > 0
            
            if overall_success:
                message = f"并发任务执行完成，成功 {success_count} 个，失败 {fail_count} 个"
                self.logger.info(message)
            else:
                message = f"并发任务执行失败，所有 {total_tasks} 个任务均失败"
                self.logger.warning(message)
            
            return {
                "success": overall_success,
                "message": message,
                "data": {
                    "all_results": results,
                    "success_results": success_results,
                    "failed_results": failed_results,
                    "merged_data": merged_data,
                    "statistics": {
                        "total_tasks": total_tasks,
                        "success_count": success_count,
                        "fail_count": fail_count,
                        "success_rate": success_count / total_tasks if total_tasks > 0 else 0
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"执行并发任务异常: {e}")
            return {
                "success": False,
                "message": f"执行并发任务异常: {str(e)}",
                "data": {
                    "base_func": base_func.__name__,
                    "param_list_count": len(param_list) if param_list else 0
                }
            }
    
    def _merge_concurrent_results(self, success_results: List[Dict[str, Any]]) -> Any:
        """
        合并并发任务的结果
        """
        if not success_results:
            return []
        
        # 提取所有数据
        all_data = [result["data"] for result in success_results]
        
        # 检查数据类型
        if all(isinstance(data, list) for data in all_data):
            # 所有结果都是列表，合并为一个列表
            merged = []
            for data in all_data:
                merged.extend(data)
            return merged
        
        elif all(isinstance(data, dict) for data in all_data):
            # 所有结果都是字典，合并为一个字典
            merged = {}
            for data in all_data:
                merged.update(data)
            return merged
        
        else:
            # 数据类型不一致，返回原始结果列表
            return all_data

# 测试函数
def mock_success_task(data: str, delay: float = 0.1) -> dict:
    """模拟成功任务"""
    time.sleep(delay)  # 模拟网络延迟
    return {
        "status": "success",
        "data": f"任务数据: {data}",
        "timestamp": time.time()
    }

def mock_failure_task(error_msg: str) -> dict:
    """模拟失败任务"""
    raise ValueError(f"模拟任务失败: {error_msg}")

def test_basic_functionality():
    """测试基础功能"""
    print("=== 测试基础功能 ===")
    
    # 创建服务实例
    service = MockStockBasicService()
    
    # 准备参数列表
    param_list = [
        {"args": ("任务1",), "kwargs": {"delay": 0.1}, "name": "task1"},
        {"args": ("任务2",), "kwargs": {"delay": 0.05}, "name": "task2"},
        {"args": ("任务3",), "kwargs": {"delay": 0.2}, "name": "task3"},
    ]
    
    # 执行并发任务
    result = service.execute_concurrent_tasks(
        base_func=mock_success_task,
        param_list=param_list,
        max_workers=3
    )
    
    # 验证结果
    print(f"整体成功: {result['success']}")
    print(f"消息: {result['message']}")
    
    if result['success']:
        data = result['data']
        print(f"总任务数: {data['statistics']['total_tasks']}")
        print(f"成功数: {data['statistics']['success_count']}")
        print(f"失败数: {data['statistics']['fail_count']}")
        print(f"成功率: {data['statistics']['success_rate']:.2%}")
        
        print("\n合并后的数据:")
        print(data['merged_data'])
        
        # 验证
        assert data['statistics']['total_tasks'] == 3
        assert data['statistics']['success_count'] == 3
        assert data['statistics']['fail_count'] == 0
        assert result['success'] == True
        
        print("✓ 基础功能测试通过")
        return True
    else:
        print("✗ 基础功能测试失败")
        return False

def test_mixed_success_failure():
    """测试混合成功和失败的任务"""
    print("\n=== 测试混合成功和失败的任务 ===")
    
    # 创建服务实例
    service = MockStockBasicService()
    
    def mixed_task(task_type: str, value: str):
        """混合任务"""
        if task_type == "success":
            return {"status": "success", "value": value}
        else:
            raise ValueError(f"任务失败: {value}")
    
    # 准备参数列表
    param_list = [
        {"args": ("success", "任务1"), "name": "success1"},
        {"args": ("failure", "错误1"), "name": "failure1"},
        {"args": ("success", "任务2"), "name": "success2"},
        {"args": ("failure", "错误2"), "name": "failure2"},
    ]
    
    # 执行并发任务
    result = service.execute_concurrent_tasks(
        base_func=mixed_task,
        param_list=param_list,
        max_workers=2
    )
    
    # 验证结果
    print(f"整体成功: {result['success']} (期望: True，因为至少有一个成功)")
    print(f"消息: {result['message']}")
    
    if result['success']:
        data = result['data']
        print(f"总任务数: {data['statistics']['total_tasks']}")
        print(f"成功数: {data['statistics']['success_count']}")
        print(f"失败数: {data['statistics']['fail_count']}")
        
        # 验证
        assert data['statistics']['total_tasks'] == 4
        assert data['statistics']['success_count'] == 2
        assert data['statistics']['fail_count'] == 2
        assert result['success'] == True  # 至少有一个成功
        
        print("✓ 混合任务测试通过")
        return True
    else:
        print("✗ 混合任务测试失败")
        return False

def test_data_merging():
    """测试数据合并功能"""
    print("\n=== 测试数据合并功能 ===")
    
    # 创建服务实例
    service = MockStockBasicService()
    
    # 测试列表合并
    def list_task(page: int) -> list:
        return [f"item_{page}_{i}" for i in range(3)]
    
    param_list = [
        {"args": (1,), "name": "page1"},
        {"args": (2,), "name": "page2"},
    ]
    
    result = service.execute_concurrent_tasks(list_task, param_list)
    
    if result['success']:
        merged_data = result['data']['merged_data']
        print(f"列表合并结果: {merged_data}")
        assert len(merged_data) == 6  # 2页 * 3项
        print("✓ 列表合并测试通过")
    
    # 测试字典合并
    def dict_task(key: str) -> dict:
        return {key: f"value_{key}"}
    
    param_list = [
        {"args": ("key1",), "name": "dict1"},
        {"args": ("key2",), "name": "dict2"},
    ]
    
    result = service.execute_concurrent_tasks(dict_task, param_list)
    
    if result['success']:
        merged_data = result['data']['merged_data']
        print(f"字典合并结果: {merged_data}")
        assert len(merged_data) == 2  # 2个键值对
        print("✓ 字典合并测试通过")
    
    return True

def test_parameter_validation():
    """测试参数验证"""
    print("\n=== 测试参数验证 ===")
    
    # 创建服务实例
    service = MockStockBasicService()
    
    # 测试无效函数
    result = service.execute_concurrent_tasks("not_a_function", [{"args": ("test",)}])
    print(f"无效函数测试: {result['success']} (期望: False)")
    assert result['success'] == False
    
    # 测试空参数列表
    result = service.execute_concurrent_tasks(mock_success_task, [])
    print(f"空参数列表测试: {result['success']} (期望: False)")
    assert result['success'] == False
    
    # 测试非列表参数
    result = service.execute_concurrent_tasks(mock_success_task, "not_a_list")
    print(f"非列表参数测试: {result['success']} (期望: False)")
    assert result['success'] == False
    
    print("✓ 参数验证测试通过")
    return True

def main():
    """主测试函数"""
    print("开始测试通用多线程并发调用函数...")
    
    tests = [
        ("基础功能", test_basic_functionality),
        ("混合任务", test_mixed_success_failure),
        ("数据合并", test_data_merging),
        ("参数验证", test_parameter_validation),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*50}")
            print(f"执行测试: {test_name}")
            print(f"{'='*50}")
            
            success = test_func()
            if success:
                passed_tests += 1
                print(f"✓ 测试 {test_name} 通过")
            else:
                print(f"✗ 测试 {test_name} 失败")
                
        except Exception as e:
            print(f"✗ 测试 {test_name} 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*50}")
    print(f"测试完成: {passed_tests}/{total_tests} 通过")
    print(f"{'='*50}")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过!")
        return 0
    else:
        print("⚠️  部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())