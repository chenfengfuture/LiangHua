"""
session_manager.py — Redis会话管理器

功能：
1. 自动生成会话ID（当用户未提供时）
2. 会话存储到Redis，支持过期时间
3. 会话验证和续期
4. 会话统计和清理

"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from utils.redis_client import *


logger = logging.getLogger(__name__)

# Redis键前缀
SESSION_KEY_PREFIX = "llm:session:"
SESSION_DATA_KEY_PREFIX = "llm:session_data:"
IP_SESSION_MAPPING_KEY = "llm:ip_session_mapping:"  # IP到session的映射

# 会话配置
SESSION_TTL_SECONDS = 1800  # 30分钟
SESSION_REFRESH_SECONDS = 300  # 5分钟刷新一次
MAX_SESSIONS_PER_IP = 1  # 每个IP最多1个session（修正方案要求）

# IP限制配置
IP_SESSION_COUNT_KEY = "llm:ip_session_count:"


class RedisSessionManager:
    """Redis会话管理器"""
    
    @staticmethod
    def generate_session_id() -> str:
        """生成新的会话ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def get_redis_key(session_id: str) -> str:
        """获取Redis键"""
        return f"{SESSION_KEY_PREFIX}{session_id}"
    
    @staticmethod
    def get_session_data_key(session_id: str) -> str:
        """获取会话数据Redis键"""
        return f"{SESSION_DATA_KEY_PREFIX}{session_id}"
    
    @staticmethod
    def get_ip_session_count_key(ip_address: str) -> str:
        """获取IP会话计数键"""
        return f"{IP_SESSION_COUNT_KEY}{ip_address}"
    
    @staticmethod
    def get_ip_session_mapping_key(ip_address: str) -> str:
        """获取IP到session的映射键"""
        return f"{IP_SESSION_MAPPING_KEY}{ip_address}"
    
    @staticmethod
    async def create_session(client_ip: str = None) -> Tuple[str, Dict[str, Any]]:
        """
        创建新会话
        
        Args:
            client_ip: 客户端IP地址（用于限制）
            
        Returns:
            (session_id, session_info)
        """
        session_id = RedisSessionManager.generate_session_id()
        
        # 检查IP会话限制
        if client_ip:
            ip_key = RedisSessionManager.get_ip_session_count_key(client_ip)
            current_count = redis_get(ip_key)
            if current_count and int(current_count) >= MAX_SESSIONS_PER_IP:
                logger.warning(f"IP {client_ip} 达到最大会话限制: {MAX_SESSIONS_PER_IP}")
                # 可以在这里实现清理最旧会话的逻辑
        
        session_info = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_access": datetime.now().isoformat(),
            "access_count": 1,
            "client_ip": client_ip,
            "status": "active"
        }
        
        # 存储到Redis
        session_key = RedisSessionManager.get_redis_key(session_id)
        redis_set(session_key, json.dumps(session_info, ensure_ascii=False))
        redis_expire(session_key, SESSION_TTL_SECONDS)
        
        # 更新IP会话计数和映射
        if client_ip:
            ip_key = RedisSessionManager.get_ip_session_count_key(client_ip)
            ip_mapping_key = RedisSessionManager.get_ip_session_mapping_key(client_ip)
            
            # 获取当前IP的session_id（如果有）
            existing_session_id = redis_get(ip_mapping_key)
            if existing_session_id:
                # 删除旧的session（保证原子性）
                old_session_key = RedisSessionManager.get_redis_key(existing_session_id)
                r = _get_client()
                if r:
                    r.delete(old_session_key)
                    logger.debug(f"删除旧的session: {existing_session_id} for IP: {client_ip}")
            
            # 设置IP到session的映射
            redis_set(ip_mapping_key, session_id)
            redis_expire(ip_mapping_key, SESSION_TTL_SECONDS)
            
            # 更新IP会话计数
            current_count = redis_get(ip_key)
            if current_count:
                redis_set(ip_key, str(int(current_count) + 1))
                redis_expire(ip_key, SESSION_TTL_SECONDS * 2)  # IP计数过期时间更长
            else:
                redis_set(ip_key, "1")
                redis_expire(ip_key, SESSION_TTL_SECONDS * 2)
        
        logger.debug(f"创建新会话: {session_id}, IP: {client_ip}")
        return session_id, session_info
    
    @staticmethod
    def get_session(session_id: str, refresh: bool = True) -> Optional[Dict[str, Any]]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
            refresh: 是否刷新过期时间
            
        Returns:
            会话信息字典，如果不存在返回None
        """
        if not session_id:
            return None
        
        session_key = RedisSessionManager.get_redis_key(session_id)
        
        # 检查会话是否存在
        if not redis_exists(session_key):
            logger.debug(f"会话不存在: {session_id}")
            return None
        
        # 获取会话数据
        session_data = redis_get(session_key)
        if not session_data:
            return None
        
        try:
            session_info = json.loads(session_data)
            
            # 刷新会话
            if refresh:
                session_info["last_access"] = datetime.now().isoformat()
                session_info["access_count"] = session_info.get("access_count", 0) + 1
                
                # 更新Redis
                redis_set(session_key, json.dumps(session_info, ensure_ascii=False))
                redis_expire(session_key, SESSION_TTL_SECONDS)
            
            return session_info
        except json.JSONDecodeError as e:
            logger.error(f"会话数据JSON解析失败: {session_id}, 错误: {e}")
            return None
    
    @staticmethod
    def validate_session(session_id: str) -> bool:
        """验证会话是否有效"""
        if not session_id:
            return False
        
        session_info = RedisSessionManager.get_session(session_id, refresh=False)
        return session_info is not None and session_info.get("status") == "active"
    
    @staticmethod
    def delete_session(session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功删除
        """
        if not session_id:
            return False
        
        session_key = RedisSessionManager.get_redis_key(session_id)
        session_data_key = RedisSessionManager.get_session_data_key(session_id)
        
        # 获取会话信息以获取IP地址
        session_info = RedisSessionManager.get_session(session_id, refresh=False)
        
        # 删除会话键 - 使用redis客户端直接删除
        try:
            r = _get_client()
            if r is None:
                return False
            
            # 删除会话键
            deleted = r.delete(session_key)
            
            # 删除会话数据键（如果存在）
            r.delete(session_data_key)
            
            # 更新IP会话计数和删除映射
            if session_info and session_info.get("client_ip"):
                client_ip = session_info["client_ip"]
                ip_key = RedisSessionManager.get_ip_session_count_key(client_ip)
                ip_mapping_key = RedisSessionManager.get_ip_session_mapping_key(client_ip)
                
                # 删除IP映射
                r.delete(ip_mapping_key)
                
                # 更新IP会话计数
                current_count = r.get(ip_key)
                if current_count and int(current_count) > 0:
                    new_count = int(current_count) - 1
                    if new_count > 0:
                        r.set(ip_key, str(new_count))
                        r.expire(ip_key, SESSION_TTL_SECONDS * 2)  # 续期IP计数
                    else:
                        r.delete(ip_key)
            
            if deleted:
                logger.debug(f"删除会话: {session_id}")
            else:
                logger.debug(f"会话不存在或已删除: {session_id}")
            
            return deleted > 0
            
        except Exception as e:
            logger.error(f"删除会话失败: {session_id}, 错误: {e}")
            return False
    
    @staticmethod
    def store_session_data(session_id: str, data_key: str, data: Any, ttl: int = None) -> bool:
        """
        存储会话相关数据
        
        Args:
            session_id: 会话ID
            data_key: 数据键名
            data: 数据内容
            ttl: 过期时间（秒），默认与会话一致
            
        Returns:
            是否成功
        """
        if not session_id or not data_key:
            return False
        
        # 验证会话是否存在
        if not RedisSessionManager.validate_session(session_id):
            logger.warning(f"尝试为无效会话存储数据: {session_id}")
            return False
        
        data_dict = {
            "data": data,
            "stored_at": datetime.now().isoformat(),
            "session_id": session_id,
            "data_key": data_key
        }
        
        # 存储到Redis
        full_key = f"{RedisSessionManager.get_session_data_key(session_id)}:{data_key}"
        redis_set(full_key, json.dumps(data_dict, ensure_ascii=False))
        
        # 设置过期时间
        expire_time = ttl if ttl is not None else SESSION_TTL_SECONDS
        redis_expire(full_key, expire_time)
        
        return True
    
    @staticmethod
    def get_session_data(session_id: str, data_key: str) -> Optional[Any]:
        """
        获取会话数据
        
        Args:
            session_id: 会话ID
            data_key: 数据键名
            
        Returns:
            数据内容，如果不存在返回None
        """
        if not session_id or not data_key:
            return None
        
        # 验证会话是否存在
        if not RedisSessionManager.validate_session(session_id):
            return None
        
        full_key = f"{RedisSessionManager.get_session_data_key(session_id)}:{data_key}"
        data_str = redis_get(full_key)
        
        if not data_str:
            return None
        
        try:
            data_dict = json.loads(data_str)
            return data_dict.get("data")
        except json.JSONDecodeError as e:
            logger.error(f"会话数据JSON解析失败: {session_id}/{data_key}, 错误: {e}")
            return None
    
    @staticmethod
    def cleanup_expired_sessions() -> int:
        """
        清理过期会话（后台任务）
        
        Returns:
            清理的会话数量
        """
        # Redis会自动处理键过期，这里主要清理相关的数据键
        # 在实际应用中，可以添加更复杂的清理逻辑
        logger.debug("Redis会话清理任务运行中...")
        return 0
    
    @staticmethod
    def get_session_stats() -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Returns:
            统计信息字典
        """
        # 注意：获取所有会话键在生产环境中可能很重
        # 这里仅返回基本统计信息
        return {
            "session_ttl_seconds": SESSION_TTL_SECONDS,
            "session_refresh_seconds": SESSION_REFRESH_SECONDS,
            "max_sessions_per_ip": MAX_SESSIONS_PER_IP,
            "storage_backend": "redis",
            "auto_generation_enabled": True
        }


# 全局实例
_session_manager = RedisSessionManager()


def get_session_manager() -> RedisSessionManager:
    """获取会话管理器实例"""
    return _session_manager


async def auto_generate_session_if_needed(session_id: str = None, client_ip: str = None) -> Tuple[str, bool]:
    """
    自动生成会话ID（如果需要）
    
    修正方案：
    1. 当请求不带 session_id 时，查询 Redis 中是否存在有效会话，若存在则复用，否则创建新会话并关联该 IP
    2. 同一个 IP 永远只会有 1 个 session
    
    Args:
        session_id: 现有的会话ID（可能为None）
        client_ip: 客户端IP地址
        
    Returns:
        (session_id, is_new_session)
    """
    if session_id:
        # 验证现有会话
        if _session_manager.validate_session(session_id):
            # 刷新会话访问时间
            _session_manager.get_session(session_id, refresh=True)
            return session_id, False
        else:
            # 会话无效，创建新会话
            logger.debug(f"现有会话无效，创建新会话: {session_id}")
            session_data = await _session_manager.create_session(client_ip)
            new_session_id = session_data[0] if session_data else None
            return new_session_id, True
    else:
        # 没有提供会话ID，检查IP是否有有效会话
        if client_ip:
            # 获取IP对应的session_id
            ip_mapping_key = RedisSessionManager.get_ip_session_mapping_key(client_ip)
            existing_session_id = redis_get(ip_mapping_key)
            
            if existing_session_id and _session_manager.validate_session(existing_session_id):
                # 复用现有会话
                logger.debug(f"复用IP {client_ip} 的现有会话: {existing_session_id}")
                # 刷新会话访问时间
                _session_manager.get_session(existing_session_id, refresh=True)
                return existing_session_id, False
        
        # 没有有效会话，创建新会话
        session_data = await _session_manager.create_session(client_ip)
        new_session_id = session_data[0] if session_data else None
        return new_session_id, True


def get_client_ip(request) -> Optional[str]:
    """
    从请求中获取客户端IP
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        IP地址字符串
    """
    try:
        # 尝试从X-Forwarded-For获取真实IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # 取第一个IP（可能是负载均衡器后的真实客户端IP）
            return forwarded_for.split(",")[0].strip()
        
        # 尝试从X-Real-IP获取
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 使用客户端主机
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None
    except Exception as e:
        logger.warning(f"获取客户端IP失败: {e}")
        return None


if __name__ == "__main__":
    # 简单测试
    print("Redis会话管理器测试...")
    
    # 测试会话创建
    session_id, session_info = _session_manager.create_session("127.0.0.1")
    print(f"创建会话: {session_id}")
    print(f"会话信息: {session_info}")
    
    # 测试会话获取
    retrieved = _session_manager.get_session(session_id)
    print(f"获取会话: {retrieved}")
    
    # 测试会话验证
    valid = _session_manager.validate_session(session_id)
    print(f"会话验证: {valid}")
    
    # 测试会话删除
    deleted = _session_manager.delete_session(session_id)
    print(f"删除会话: {deleted}")
    
    print("测试完成！")