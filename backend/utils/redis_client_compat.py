#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 客户端兼容层模块 - redis_client_compat

设计目标：为现有代码提供与 redis_client.py 完全相同的接口
核心功能：将现有函数调用转发到新的 RedisServiceBase 实例

使用方式：
1. 导入此模块替代原来的 redis_client
2. 所有现有代码无需修改即可继续工作
3. 逐步迁移到新的 RedisServiceBase 基类
"""

import json
from typing import Any, Optional, Dict, List
from datetime import datetime

# 导入新的 Redis 服务基类
from system_service.redis_service import RedisServiceBase

# 创建全局 RedisServiceBase 实例
_redis_service = RedisServiceBase(service_name="RedisCompat")


# ============================================================================
#  通用方法（保持与原有接口完全一致）
# ============================================================================

def redis_get(key: str) -> Optional[str]:
    """
    获取 Redis key 的字符串值
    
    Args:
        key: Redis key 名称
        
    Returns:
        字符串值，或 None（key 不存在 / Redis 不可用）
    """
    return _redis_service._cache_get(key)


def redis_set(key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
    """
    设置 Redis key 的值
    
    Args:
        key: Redis key 名称
        value: 要设置的值（会转为字符串）
        expire_seconds: 过期时间（秒），None 表示永不过期
        
    Returns:
        True 设置成功，False 设置失败
    """
    return _redis_service._cache_set(key, value, expire_seconds)


def redis_exists(key: str) -> bool:
    """
    判断 Redis key 是否存在
    
    Args:
        key: Redis key 名称
        
    Returns:
        True 存在，False 不存在或 Redis 不可用
    """
    return _redis_service._cache_exists(key)


def redis_expire(key: str, seconds: int) -> bool:
    """
    设置 Redis key 的过期时间
    
    Args:
        key: Redis key 名称
        seconds: 过期秒数
        
    Returns:
        True 设置成功，False 失败
    """
    return _redis_service._cache_expire(key, seconds)


def _get_client():
    """
    获取 Redis 客户端（内部方法，保持兼容）
    
    Returns:
        redis.Redis 实例，或 None（Redis 不可用时）
    """
    return _redis_service._get_client()


# ============================================================================
#  新闻采集状态便捷函数（保持与原有接口完全一致）
# ============================================================================

# 新闻采集状态 Redis Key 定义（从 RedisServiceBase 复制）
NEWS_COLLECT_TIME_KEYS = RedisServiceBase.NEWS_COLLECT_TIME_KEYS
NEWS_CCTV_TODONE_KEY = RedisServiceBase.NEWS_CCTV_TODONE_KEY


def get_last_collect_time(news_type: str) -> Optional[str]:
    """
    获取指定新闻类型的上次采集时间
    
    Args:
        news_type: 采集类型（company/cls/global/cctv/report）
        
    Returns:
        "%Y-%m-%d %H:%M:%S" 格式时间戳字符串，或 None（触发兜底逻辑）
    """
    return _redis_service.get_last_collect_time(news_type)


def set_last_collect_time(news_type: str, dt: Optional[datetime] = None) -> bool:
    """
    更新指定新闻类型的上次采集时间
    
    Args:
        news_type: 采集类型（company/cls/global/cctv/report）
        dt: 指定时间，默认为当前时间
        
    Returns:
        True 设置成功，False 失败
    """
    return _redis_service.set_last_collect_time(news_type, dt)


def seconds_since_last_collect(news_type: str) -> Optional[float]:
    """
    获取指定新闻类型距上次采集的秒数
    
    Args:
        news_type: 采集类型
        
    Returns:
        秒数（float），或 None（从未采集 / Redis 不可用）
    """
    return _redis_service.seconds_since_last_collect(news_type)


def should_collect(news_type: str, interval_seconds: float) -> bool:
    """
    判断是否应该采集指定类型的新闻
    
    Args:
        news_type: 采集类型
        interval_seconds: 最小采集间隔（秒）
        
    Returns:
        True = 应该采集（从未采集 或 间隔已过）
    """
    return _redis_service.should_collect(news_type, interval_seconds)


def is_cctv_today_done() -> bool:
    """
    判断今天是否已采集过 CCTV 新闻联播
    
    Returns:
        True 今日已采集，False 未采集或 Redis 不可用
    """
    return _redis_service.is_cctv_today_done()


def set_cctv_today_done() -> bool:
    """
    标记今天 CCTV 已采集完成
    
    Returns:
        True 设置成功，False 失败
    """
    return _redis_service.set_cctv_today_done()


def reset_cctv_today_done() -> bool:
    """
    重置 CCTV 今日标记为未采集
    每天 00:00 自动重置时调用
    
    Returns:
        True 设置成功，False 失败
    """
    return _redis_service.reset_cctv_today_done()


def init_news_keys():
    """
    服务启动时初始化所有新闻采集状态 key（仅当 key 不存在时写入默认值）
    幂等操作，不会覆盖已有的采集时间记录
    """
    _redis_service.init_news_keys()


def get_all_collect_status() -> dict:
    """
    获取所有新闻采集类型的上次采集时间，返回字典
    用于管理接口展示或调试
    
    Returns:
        {"company": "2026-04-07 12:00:00", "cctv_today_done": "0", ...}
    """
    return _redis_service.get_all_collect_status()


# ============================================================================
#  三层 Redis 结构操作（保持与原有接口完全一致）
# ============================================================================

# 三层 Redis 结构 Key 定义（从 RedisServiceBase 复制）
NEWS_DATA_KEY_PREFIX = RedisServiceBase.NEWS_DATA_KEY_PREFIX
NEWS_PENDING_LLM_KEY = RedisServiceBase.NEWS_PENDING_LLM_KEY
NEWS_PENDING_PERSIST_KEY = RedisServiceBase.NEWS_PENDING_PERSIST_KEY


def _get_news_data_key(news_id: int, table_name: str = None) -> str:
    """
    生成新闻数据的 Redis key
    如果提供了 table_name，使用 news:data:{table_name}:{id} 格式
    否则使用 news:data:{id} 格式（兼容旧代码）
    """
    return _redis_service._get_news_data_key(news_id, table_name)


def news_data_set(news_id: int, data: dict) -> bool:
    """
    将完整新闻 JSON 写入 Redis String（永久保存，不设过期）
    key = news:data:{table_name}:{news_id} 或 news:data:{news_id}，value = JSON 字符串
    
    Args:
        news_id: 新闻主键 ID（MySQL 自增 id）
        data: 完整新闻字典（应包含 table_name 字段）
        
    Returns:
        True 成功，False 失败
    """
    return _redis_service.news_data_set(news_id, data)


def news_data_get(news_id: int, table_name: str = None) -> Optional[dict]:
    """
    从 Redis 读取完整新闻 JSON
    
    Args:
        news_id: 新闻主键 ID
        table_name: 表名（可选，用于构建正确的 key）
        
    Returns:
        新闻字典，或 None（不存在/失败）
    """
    return _redis_service.news_data_get(news_id, table_name)


def news_data_update(news_id: int, updates: dict) -> bool:
    """
    将 updates 合并写回 news:data:{table_name}:{id}（用于写入 AI 分析结果）
    读取现有 JSON → 合并 updates → 写回
    
    Args:
        news_id: 新闻主键 ID
        updates: 要合并的字段字典（如 ai_result、sentiment 等，应包含 table_name）
        
    Returns:
        True 成功，False 失败
    """
    return _redis_service.news_data_update(news_id, updates)


def news_data_batch_get(news_ids: list, table_names: list = None) -> list:
    """
    批量从 Redis 读取多条新闻 JSON（MGET 优化，高性能）
    
    Args:
        news_ids: 新闻 ID 列表
        table_names: 对应的表名列表（可选，用于构建正确的 key）
        
    Returns:
        新闻字典列表（跳过不存在的）
    """
    return _redis_service.news_data_batch_get(news_ids, table_names)


# ============================================================================
#  Layer 2: news:pending_llm (Redis Set) 操作
# ============================================================================

def _pack_pending_item(news_id: int, table_name: str = None) -> str:
    """打包 pending_llm/pending_persist 队列中的项"""
    return _redis_service._pack_pending_item(news_id, table_name)


def _unpack_pending_item(item: str) -> tuple:
    """解包 pending_llm/pending_persist 队列中的项，返回 (news_id, table_name)"""
    return _redis_service._unpack_pending_item(item)


def pending_llm_add(news_id: int, table_name: str = None) -> bool:
    """
    将新闻 ID 加入 news:pending_llm Set（待 LLM 分析）
    
    Args:
        news_id: 新闻主键 ID
        table_name: 表名（可选，用于区分不同表的相同 ID）
        
    Returns:
        True 成功
    """
    return _redis_service.pending_llm_add(news_id, table_name)


def pending_llm_add_batch(news_ids: list, table_names: list = None) -> int:
    """
    批量将新闻 ID 加入 news:pending_llm Set
    
    Args:
        news_ids: 新闻 ID 列表
        table_names: 对应的表名列表（可选，用于区分不同表的相同 ID）
        
    Returns:
        成功加入的数量
    """
    return _redis_service.pending_llm_add_batch(news_ids, table_names)


def pending_llm_spop(count: int = 6) -> list:
    """
    从 news:pending_llm Set 中随机弹出最多 count 个项（SPOP，线程安全无竞争）
    
    Args:
        count: 最多弹出数量（默认 6）
        
    Returns:
        项字符串列表，格式为 "table_name:news_id" 或 "news_id"
        使用 _unpack_pending_item() 解包为 (news_id, table_name)
    """
    return _redis_service.pending_llm_spop(count)


def pending_llm_size() -> int:
    """获取 news:pending_llm Set 的大小（待分析数量）"""
    return _redis_service.pending_llm_size()


# ============================================================================
#  Layer 3: news:pending_persist (Redis List) 操作
# ============================================================================

def pending_persist_push(news_id: int, table_name: str = None) -> bool:
    """
    将已分析的新闻 ID 推入 news:pending_persist List（待持久化到 MySQL）
    
    Args:
        news_id: 新闻主键 ID
        table_name: 表名（可选，用于区分不同表的相同 ID）
        
    Returns:
        True 成功
    """
    return _redis_service.pending_persist_push(news_id, table_name)


def pending_persist_push_batch(news_ids: list, table_names: list = None) -> int:
    """
    批量推入待持久化 ID
    
    Args:
        news_ids: 新闻 ID 列表
        table_names: 对应的表名列表（可选，用于区分不同表的相同 ID）
        
    Returns:
        推入数量
    """
    return _redis_service.pending_persist_push_batch(news_ids, table_names)


def pending_persist_pop_batch(count: int = 200) -> list:
    """
    原子批量获取并删除 news:pending_persist 中最多 count 个项
    使用 LRANGE + LTRIM 保证原子性（单线程持久化线程，无竞争）
    
    Args:
        count: 最多获取数量（默认 200）
        
    Returns:
        项字符串列表，格式为 "table_name:news_id" 或 "news_id"
        使用 _unpack_pending_item() 解包为 (news_id, table_name)
    """
    return _redis_service.pending_persist_pop_batch(count)


def pending_persist_size() -> int:
    """获取 news:pending_persist List 的长度（待持久化数量）"""
    return _redis_service.pending_persist_size()


# ============================================================================
#  关闭连接池函数
# ============================================================================

def close_redis():
    """关闭 Redis 连接池（服务关闭时调用）"""
    _redis_service.close_redis()


# ============================================================================
#  导出所有函数，保持与原有模块完全一致
# ============================================================================

__all__ = [
    # 通用方法
    'redis_get',
    'redis_set',
    'redis_exists',
    'redis_expire',
    '_get_client',
    'close_redis',
    
    # 新闻采集状态管理
    'NEWS_COLLECT_TIME_KEYS',
    'NEWS_CCTV_TODONE_KEY',
    'get_last_collect_time',
    'set_last_collect_time',
    'seconds_since_last_collect',
    'should_collect',
    'is_cctv_today_done',
    'set_cctv_today_done',
    'reset_cctv_today_done',
    'init_news_keys',
    'get_all_collect_status',
    
    # 三层 Redis 结构
    'NEWS_DATA_KEY_PREFIX',
    'NEWS_PENDING_LLM_KEY',
    'NEWS_PENDING_PERSIST_KEY',
    '_get_news_data_key',
    'news_data_set',
    'news_data_get',
    'news_data_update',
    'news_data_batch_get',
    
    # Layer 2: news:pending_llm
    '_pack_pending_item',
    '_unpack_pending_item',
    'pending_llm_add',
    'pending_llm_add_batch',
    'pending_llm_spop',
    'pending_llm_size',
    
    # Layer 3: news:pending_persist
    'pending_persist_push',
    'pending_persist_push_batch',
    'pending_persist_pop_batch',
    'pending_persist_size',
]