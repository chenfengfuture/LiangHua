"""
stock_services/common/cache.py — 缓存工具统一封装

封装三类重复模式：
1. CacheKeyBuilder — 统一缓存 Key 构建（替代 3 种不同策略）
2. RedisHashHelper — Redis Hash 批量读写工具（复用 kline_redis 模式到其他业务域）

源头文件及涉及的模式：
  | 文件 | 策略 | 差异 |
  |------|------|------|
  | services/basic_services.py | generate_cache_key() | MD5 签名，用于 12 步模板方法 |
  | services/volume_indicator_service.py | _build_cache_key() | 参数字典 MD5 前缀，独立实现 |
  | services/stock_indicator_service.py | 硬编码模板 indicator:{version}:{symbol}:{YYYY} | 完全不同 |
  | mootdx/kline_redis.py | Hash + 压缩存储 | 自定义协议 |
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CacheKeyBuilder:
    """
    统一缓存 Key 构建器。

    将现有 3 种不同策略统一为 1 种灵活模式：
      {prefix}:{version}:{parts...}:{params_md5}

    用法兼容：
      - basic_services.py 的 MD5 签名模式
      - volume_indicator_service.py 的参数字典 MD5 前缀
      - stock_indicator_service.py 的指示器模板
    """

    @staticmethod
    def build(table_name: str, simple: bool = False, params: dict = None) -> str:
        """
        构建缓存 Key。

        Args:
            table_name: 表名
            *parts:   标识部分（symbol, indicator_name, year 等）
            params:   参数 dict，自动排序后取 MD5 前缀（可选）
            simple: 生成的key状态

        Returns:
            缓存 Key 字符串

        Examples:
            >>> CacheKeyBuilder.build("indicator", "000001", params={"ma": [5,10]})
            "indicator:v1:000001:a1b2c3d4e5f6"

            >>> CacheKeyBuilder.build("stock_basic", "volume_breakout", params={"symbol":"000001"})
            "stock_basic:v1:volume_breakout:a1b2c3d4"
        """

        key = table_name
        print(params)
        if simple:
            values = [str(v) for k, v in sorted(params.items())]
            return ":".join([key] + values)
        else:
            if params:
                sorted_params = json.dumps(params, sort_keys=True, ensure_ascii=False)
                md5 = hashlib.md5(sorted_params.encode()).hexdigest()[:12]
                key += f":{md5}"
            return key



    @staticmethod 
    def build_simple(table_name: str, *parts: str) -> str:
        """
        构建简单缓存 Key（不带参数 MD5）。

        用于不需要参数签名的场景，如纯 symbol+year 查询。

        Examples:
            >>> CacheKeyBuilder.build_simple("kline:data", "day", "000001", "2026")
            "kline:data:day:000001:2026"
        """
        return ":".join([table_name] + [str(p) for p in parts])




class RedisHashHelper:
    """
    Redis Hash 批量读写工具。

    复用 mootdx/kline_redis.py 的 Hash 压缩模式到其他业务域。
    该模式将 N 个独立 key 压缩为 1 个 Hash key，减少 Redis 内存开销。
    """

    @staticmethod
    def hget_all(redis_client, key: str,
                 exclude_fields: List[str] = None) -> List[Dict[str, Any]]:
        """
        读取 Redis Hash 全部数据。

        Args:
            redis_client: Redis 客户端实例
            key:          Hash key
            exclude_fields: 排除的元数据字段列表

        Returns:
            解析后的字典列表
        """
        if redis_client is None:
            return []
        exclude = set(exclude_fields or [])
        try:
            data = redis_client.hgetall(key)
            # 过滤元数据字段
            for f in exclude:
                data.pop(f, None)
            result = []
            for field_key, val in data.items():
                try:
                    result.append(json.loads(val))
                except Exception:
                    continue
            return result
        except Exception as e:
            logger.error(f"[RedisHashHelper] HGETALL 失败 {key}: {e}")
            return []

    @staticmethod
    def hset_batch(redis_client, key: str, mapping: dict,
                   ttl: int = None, batch_size: int = 500) -> int:
        """
        分批写入 Redis Hash。

        Args:
            redis_client: Redis 客户端实例
            key:          Hash key
            mapping:      {field: value_dict}
            ttl:          TTL 秒数（None 不设置）
            batch_size:   单次 pipeline 写入数量

        Returns:
            成功写入条数
        """
        if redis_client is None or not mapping:
            return 0

        ok = 0
        items = list(mapping.items())
        try:
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                pipe = redis_client.pipeline(transaction=False)
                for field, val in batch:
                    try:
                        serialized = json.dumps(val, ensure_ascii=False, default=str)
                        pipe.hset(key, field, serialized)
                    except Exception:
                        continue
                if ttl is not None:
                    pipe.expire(key, ttl)
                try:
                    pipe.execute()
                    ok += len(batch)
                except Exception as e:
                    logger.error(f"[RedisHashHelper] HSET 批次失败 {key}: {e}")
        except Exception as e:
            logger.error(f"[RedisHashHelper] hset_batch 异常 {key}: {e}")

        return ok

    @staticmethod
    def hcheck_complete(redis_client, key: str, expected: int,
                        complete_field: str = "__complete__") -> Optional[bool]:
        """
        检查 Hash 数据是否完整（通过特殊字段或 HLEN）。

        Args:
            redis_client:   Redis 客户端实例
            key:            Hash key
            expected:       预期条数
            complete_field: 完整性标记字段名

        Returns:
            True 完整 / False 不完整 / None 无法判断
        """
        if redis_client is None:
            return None
        try:
            val = redis_client.hget(key, complete_field)
            if val is not None:
                stored = int(val)
                return stored >= expected
            # 无标记时检查 HLEN
            hlen = redis_client.hlen(key)
            return hlen >= expected
        except Exception:
            return None


__all__ = [
    "CacheKeyBuilder",
    "RedisHashHelper",
]