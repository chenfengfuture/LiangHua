"""
utils/redis_client.py — Redis 连接池工具 & 新闻采集状态管理

功能：
  - 使用 redis.ConnectionPool 连接池，支持 host/port/db/password
  - 封装 get / set / exists / expire 通用方法
  - 支持字符串时间读写，支持整数、布尔状态标记
  - 异常捕获，连接失败不影响主程序
  - 新闻采集状态 Key 定义及便捷操作函数
"""

import json
import time
from datetime import datetime
from typing import Any, Optional

import redis

from config import REDIS_DB, REDIS_DECODE, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT

# ═══════════════════════════════════════════════════════════════════
#  新闻采集状态 Redis Key 定义
# ═══════════════════════════════════════════════════════════════════

NEWS_COLLECT_TIME_KEYS = {
    "company": "news:last_collect_time:company",   # 个股/公司新闻
    "cls":     "news:last_collect_time:cls",       # 财联社新闻
    "global":  "news:last_collect_time:global",    # 全球新闻
    "cctv":    "news:last_collect_time:cctv",      # 新闻联播
    "report":  "news:last_collect_time:report",    # 研报新闻
}

NEWS_CCTV_TODONE_KEY = "news:cctv_today_done"





# ═══════════════════════════════════════════════════════════════════
#  Redis 连接池（懒初始化单例）
# ═══════════════════════════════════════════════════════════════════

_pool: Optional[redis.ConnectionPool] = None
_client: Optional[redis.Redis] = None


def _get_client() -> Optional[redis.Redis]:
    """
    获取 Redis 客户端（懒初始化连接池）。
    连接失败时返回 None，不阻塞业务逻辑。

    Returns:
        redis.Redis 实例，或 None（Redis 不可用时）
    """
    global _pool, _client
    if _client is not None:
        try:
            _client.ping()
            return _client
        except Exception:
            _client = None
            _pool = None

    try:
        _pool = redis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
            db=REDIS_DB,
            decode_responses=REDIS_DECODE,
            max_connections=10,
            socket_connect_timeout=3,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        _client = redis.Redis(connection_pool=_pool)
        _client.ping()
        print("[redis] Redis 连接池创建成功")
        return _client
    except Exception as e:
        print(f"[redis] Redis 连接失败（降级为内存模式）: {e}")
        _pool = None
        _client = None
        return None


def close_redis():
    """关闭 Redis 连接池（服务关闭时调用）"""
    global _pool, _client
    if _client is not None:
        try:
            _client.close()
        except Exception:
            pass
        _client = None
    if _pool is not None:
        try:
            _pool.disconnect()
        except Exception:
            pass
        _pool = None
    print("[redis] Redis 连接池已关闭")


# ═══════════════════════════════════════════════════════════════════
#  通用方法
# ═══════════════════════════════════════════════════════════════════

def redis_get(key: str) -> Optional[str]:
    """
    获取 Redis key 的字符串值。

    Args:
        key: Redis key 名称

    Returns:
        字符串值，或 None（key 不存在 / Redis 不可用）
    """
    try:
        r = _get_client()
        if r is None:
            return None
        return r.get(key)
    except Exception as e:
        print(f"[redis] GET {key} 失败: {e}")
        return None


def redis_set(key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
    """
    设置 Redis key 的值。

    Args:
        key: Redis key 名称
        value: 要设置的值（会转为字符串）
        expire_seconds: 过期时间（秒），None 表示永不过期

    Returns:
        True 设置成功，False 设置失败
    """
    try:
        r = _get_client()
        if r is None:
            return False
        if expire_seconds is not None:
            r.set(key, str(value), ex=expire_seconds)
        else:
            r.set(key, str(value))
        return True
    except Exception as e:
        print(f"[redis] SET {key}={value} 失败: {e}")
        return False


def redis_exists(key: str) -> bool:
    """
    判断 Redis key 是否存在。

    Args:
        key: Redis key 名称

    Returns:
        True 存在，False 不存在或 Redis 不可用
    """
    try:
        r = _get_client()
        if r is None:
            return False
        return bool(r.exists(key))
    except Exception as e:
        print(f"[redis] EXISTS {key} 失败: {e}")
        return False


def redis_expire(key: str, seconds: int) -> bool:
    """
    设置 Redis key 的过期时间。

    Args:
        key: Redis key 名称
        seconds: 过期秒数

    Returns:
        True 设置成功，False 失败
    """
    try:
        r = _get_client()
        if r is None:
            return False
        r.expire(key, seconds)
        return True
    except Exception as e:
        print(f"[redis] EXPIRE {key} {seconds}s 失败: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════
#  新闻采集状态便捷函数
# ═══════════════════════════════════════════════════════════════════

def get_last_collect_time(news_type: str) -> Optional[str]:
    """
    获取指定新闻类型的上次采集时间。

    返回 None 的情况（全部视为"无记录"，触发初始化兜底）：
      1. key 不存在
      2. 值为 None（Redis 不可用）
      3. 值为空字符串
      4. 值为 "never"（初始化占位）
      5. 时间格式无法解析为 %Y-%m-%d %H:%M:%S

    Args:
        news_type: 采集类型（company/cls/global/cctv/report）

    Returns:
        "%Y-%m-%d %H:%M:%S" 格式时间戳字符串，或 None（触发兜底逻辑）
    """
    key = NEWS_COLLECT_TIME_KEYS.get(news_type)
    if not key:
        return None

    val = redis_get(key)

    # 情况 1: key 不存在 / Redis 不可用 → None
    if val is None:
        return None

    # 情况 2: 空字符串 → 视为不存在
    val_stripped = val.strip()
    if not val_stripped:
        print(f"[redis] {news_type} 上次采集时间为空字符串，触发初始化兜底")
        return None

    # 情况 3: "never" 占位符 → 视为不存在
    if val_stripped == "never":
        return None

    # 情况 4: 格式校验 — 必须能解析为 %Y-%m-%d %H:%M:%S
    try:
        datetime.strptime(val_stripped, "%Y-%m-%d %H:%M:%S")
        return val_stripped
    except ValueError:
        print(f"[redis] {news_type} 时间格式错误: '{val_stripped}'，触发初始化兜底")
        return None


def set_last_collect_time(news_type: str, dt: Optional[datetime] = None) -> bool:
    """
    更新指定新闻类型的上次采集时间。

    Args:
        news_type: 采集类型（company/cls/global/cctv/report）
        dt: 指定时间，默认为当前时间

    Returns:
        True 设置成功，False 失败
    """
    key = NEWS_COLLECT_TIME_KEYS.get(news_type)
    if not key:
        return False
    value = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return redis_set(key, value)


def seconds_since_last_collect(news_type: str) -> Optional[float]:
    """
    获取指定新闻类型距上次采集的秒数。

    Args:
        news_type: 采集类型

    Returns:
        秒数（float），或 None（从未采集 / Redis 不可用）
    """
    time_str = get_last_collect_time(news_type)
    if time_str is None:
        return None
    try:
        last_dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - last_dt).total_seconds()
    except (ValueError, TypeError):
        return None


def should_collect(news_type: str, interval_seconds: float) -> bool:
    """
    判断是否应该采集指定类型的新闻。

    Args:
        news_type: 采集类型
        interval_seconds: 最小采集间隔（秒）

    Returns:
        True = 应该采集（从未采集 或 间隔已过）
    """
    elapsed = seconds_since_last_collect(news_type)
    if elapsed is None:
        return True
    return elapsed >= interval_seconds


def is_cctv_today_done() -> bool:
    """
    判断今天是否已采集过 CCTV 新闻联播。

    Returns:
        True 今日已采集，False 未采集或 Redis 不可用
    """
    val = redis_get(NEWS_CCTV_TODONE_KEY)
    return val == "1"


def set_cctv_today_done() -> bool:
    """
    标记今天 CCTV 已采集完成。

    Returns:
        True 设置成功，False 失败
    """
    return redis_set(NEWS_CCTV_TODONE_KEY, "1")


def reset_cctv_today_done() -> bool:
    """
    重置 CCTV 今日标记为未采集。
    每天 00:00 自动重置时调用。

    Returns:
        True 设置成功，False 失败
    """
    return redis_set(NEWS_CCTV_TODONE_KEY, "0")


def init_news_keys():
    """
    服务启动时初始化所有新闻采集状态 key（仅当 key 不存在时写入默认值）。
    幂等操作，不会覆盖已有的采集时间记录。
    """
    r = _get_client()
    if r is None:
        return
    for key in NEWS_COLLECT_TIME_KEYS.values():
        r.setnx(key, "never")
    r.setnx(NEWS_CCTV_TODONE_KEY, "0")
    print("[redis] 新闻采集状态 key 初始化完成")


def get_all_collect_status() -> dict:
    """
    获取所有新闻采集类型的上次采集时间，返回字典。
    用于管理接口展示或调试。

    Returns:
        {"company": "2026-04-07 12:00:00", "cctv_today_done": "0", ...}
    """
    r = _get_client()
    if r is None:
        return {"error": "Redis 不可用"}
    result = {}
    for news_type, key in NEWS_COLLECT_TIME_KEYS.items():
        val = r.get(key)
        if val and val != "never":
            result[news_type] = val
        else:
            result[news_type] = "never"
    result["cctv_today_done"] = r.get(NEWS_CCTV_TODONE_KEY) or "0"
    return result



# ═══════════════════════════════════════════════════════════════════
#  【新架构】三层 Redis 结构操作
#
#  Layer 1: news:data:{id}      → Redis String，存完整新闻 JSON（永久）
#  Layer 2: news:pending_llm    → Redis Set，待 LLM 分析的 id
#  Layer 3: news:pending_persist→ Redis List，已分析待持久化的 id
# ═══════════════════════════════════════════════════════════════════

NEWS_DATA_KEY_PREFIX = "news:data:"
NEWS_PENDING_LLM_KEY = "news:pending_llm"
NEWS_PENDING_PERSIST_KEY = "news:pending_persist"


# ─── Layer 1: news:data:{id} ─────────────────────────────────────

def _get_news_data_key(news_id: int, table_name: str = None) -> str:
    """
    生成新闻数据的 Redis key。
    如果提供了 table_name，使用 news:data:{table_name}:{id} 格式
    否则使用 news:data:{id} 格式（兼容旧代码）
    """
    if table_name:
        return f"{NEWS_DATA_KEY_PREFIX}{table_name}:{news_id}"
    return f"{NEWS_DATA_KEY_PREFIX}{news_id}"


def news_data_set(news_id: int, data: dict) -> bool:
    """
    将完整新闻 JSON 写入 Redis String（永久保存，不设过期）。
    key = news:data:{table_name}:{news_id} 或 news:data:{news_id}，value = JSON 字符串

    Args:
        news_id: 新闻主键 ID（MySQL 自增 id）
        data: 完整新闻字典（应包含 table_name 字段）

    Returns:
        True 成功，False 失败
    """
    try:
        r = _get_client()
        if r is None:
            return False
        # 使用 table_name 构建 key，避免不同表的 ID 冲突
        table_name = data.get("table_name") if isinstance(data, dict) else None
        key = _get_news_data_key(news_id, table_name)
        r.set(key, json.dumps(data, ensure_ascii=False, default=str))
        return True
    except Exception as e:
        print(f"[redis] news_data_set id={news_id} 失败: {e}")
        return False


def news_data_get(news_id: int, table_name: str = None) -> Optional[dict]:
    """
    从 Redis 读取完整新闻 JSON。

    Args:
        news_id: 新闻主键 ID
        table_name: 表名（可选，用于构建正确的 key）

    Returns:
        新闻字典，或 None（不存在/失败）
    """
    try:
        r = _get_client()
        if r is None:
            return None
        # 优先使用 table_name 构建 key
        key = _get_news_data_key(news_id, table_name)
        val = r.get(key)
        # 如果没找到且没有指定 table_name，尝试旧格式 key（兼容）
        if val is None and not table_name:
            key = f"{NEWS_DATA_KEY_PREFIX}{news_id}"
            val = r.get(key)
        if val is None:
            return None
        return json.loads(val)
    except Exception as e:
        print(f"[redis] news_data_get id={news_id} 失败: {e}")
        return None


def news_data_update(news_id: int, updates: dict) -> bool:
    """
    将 updates 合并写回 news:data:{table_name}:{id}（用于写入 AI 分析结果）。
    读取现有 JSON → 合并 updates → 写回。

    Args:
        news_id: 新闻主键 ID
        updates: 要合并的字段字典（如 ai_result、sentiment 等，应包含 table_name）

    Returns:
        True 成功，False 失败
    """
    try:
        r = _get_client()
        if r is None:
            return False
        # 优先使用 updates 中的 table_name 构建 key
        table_name = updates.get("table_name") if isinstance(updates, dict) else None
        key = _get_news_data_key(news_id, table_name)
        val = r.get(key)
        # 如果没找到且没有指定 table_name，尝试旧格式 key（兼容）
        if val is None and not table_name:
            key = f"{NEWS_DATA_KEY_PREFIX}{news_id}"
            val = r.get(key)
        if val is None:
            return False
        data = json.loads(val)
        data.update(updates)
        r.set(key, json.dumps(data, ensure_ascii=False, default=str))
        return True
    except Exception as e:
        print(f"[redis] news_data_update id={news_id} 失败: {e}")
        return False


def news_data_batch_get(news_ids: list, table_names: list = None) -> list:
    """
    批量从 Redis 读取多条新闻 JSON（MGET 优化，高性能）。
    
    【强制要求】使用 MGET 一次性批量读取所有 key
    
    Args:
        news_ids: 新闻 ID 列表
        table_names: 对应的表名列表（可选，用于构建正确的 key）

    Returns:
        新闻字典列表（跳过不存在的）
    """
    try:
        r = _get_client()
        if r is None:
            return []
        if not news_ids:
            return []
        
        # 拼接 key：news:data:{table_name}:{id} 或 news:data:{id}
        if table_names and len(table_names) == len(news_ids):
            keys = [_get_news_data_key(nid, tname) for nid, tname in zip(news_ids, table_names)]
        else:
            keys = [f"{NEWS_DATA_KEY_PREFIX}{nid}" for nid in news_ids]
        
        # 【高性能优化】使用 MGET 一次性批量读取所有新闻 JSON
        values = r.mget(keys) if len(keys) > 0 else []
        
        result = []
        for idx, val in enumerate(values):
            if val is not None:
                try:
                    data = json.loads(val)
                    # 确保每条数据都有正确的 id 和 table_name
                    if "id" not in data and idx < len(news_ids):
                        data["id"] = news_ids[idx]
                    result.append(data)
                except (json.JSONDecodeError, TypeError):
                    continue
        return result
    except Exception as e:
        print(f"[redis] news_data_batch_get 失败: {e}")
        return []


# ─── Layer 2: news:pending_llm (Redis Set) ────────────────────────

def _pack_pending_item(news_id: int, table_name: str = None) -> str:
    """打包 pending_llm/pending_persist 队列中的项"""
    if table_name and table_name.strip():
        return f"{table_name}:{news_id}"
    return str(news_id)


def _unpack_pending_item(item: str) -> tuple:
    """解包 pending_llm/pending_persist 队列中的项，返回 (news_id, table_name)"""
    if not item:
        return None, None
    
    # 确保 item 是字符串
    item_str = str(item).strip()
    
    if ":" in item_str:
        parts = item_str.split(":")
        if len(parts) == 2:
            try:
                news_id = int(parts[1])
                table_name = parts[0]
                # 如果 table_name 为空字符串，视为 None
                if not table_name or not table_name.strip():
                    table_name = None
                return news_id, table_name
            except ValueError:
                pass
        # 处理 table_name 中包含冒号的情况（如 news:company:202604:123）
        try:
            news_id = int(parts[-1])
            table_name = ":".join(parts[:-1])
            # 如果 table_name 为空字符串，视为 None
            if not table_name or not table_name.strip():
                table_name = None
            return news_id, table_name
        except ValueError:
            pass
    try:
        news_id = int(item_str)
        return news_id, None
    except ValueError:
        return None, None


def pending_llm_add(news_id: int, table_name: str = None) -> bool:
    """
    将新闻 ID 加入 news:pending_llm Set（待 LLM 分析）。

    Args:
        news_id: 新闻主键 ID
        table_name: 表名（可选，用于区分不同表的相同 ID）

    Returns:
        True 成功
    """
    try:
        r = _get_client()
        if r is None:
            return False
        item = _pack_pending_item(news_id, table_name)
        r.sadd(NEWS_PENDING_LLM_KEY, item)
        return True
    except Exception as e:
        print(f"[redis] pending_llm_add id={news_id} 失败: {e}")
        return False


def pending_llm_add_batch(news_ids: list, table_names: list = None) -> int:
    """
    批量将新闻 ID 加入 news:pending_llm Set。

    Args:
        news_ids: 新闻 ID 列表
        table_names: 对应的表名列表（可选，用于区分不同表的相同 ID）

    Returns:
        成功加入的数量
    """
    try:
        r = _get_client()
        if r is None:
            return 0
        if not news_ids:
            return 0
        if table_names and len(table_names) == len(news_ids):
            items = [_pack_pending_item(nid, tname) for nid, tname in zip(news_ids, table_names)]
        else:
            items = [str(nid) for nid in news_ids]
        return r.sadd(NEWS_PENDING_LLM_KEY, *items)
    except Exception as e:
        print(f"[redis] pending_llm_add_batch 失败: {e}")
        return 0


def pending_llm_spop(count: int = 6) -> list:
    """
    从 news:pending_llm Set 中随机弹出最多 count 个项（SPOP，线程安全无竞争）。

    Args:
        count: 最多弹出数量（默认 6）

    Returns:
        项字符串列表，格式为 "table_name:news_id" 或 "news_id"
        使用 _unpack_pending_item() 解包为 (news_id, table_name)
    """
    try:
        r = _get_client()
        if r is None:
            return []
        result = r.spop(NEWS_PENDING_LLM_KEY, count)
        if result is None:
            return []
        # 确保返回字符串列表
        return [item.decode() if isinstance(item, bytes) else item for item in result]
    except Exception as e:
        print(f"[redis] pending_llm_spop 失败: {e}")
        return []


def pending_llm_size() -> int:
    """获取 news:pending_llm Set 的大小（待分析数量）"""
    try:
        r = _get_client()
        if r is None:
            return 0
        return r.scard(NEWS_PENDING_LLM_KEY)
    except Exception:
        return 0


# ─── Layer 3: news:pending_persist (Redis List) ───────────────────

def pending_persist_push(news_id: int, table_name: str = None) -> bool:
    """
    将已分析的新闻 ID 推入 news:pending_persist List（待持久化到 MySQL）。

    Args:
        news_id: 新闻主键 ID
        table_name: 表名（可选，用于区分不同表的相同 ID）

    Returns:
        True 成功
    """
    try:
        r = _get_client()
        if r is None:
            return False
        item = _pack_pending_item(news_id, table_name)
        r.rpush(NEWS_PENDING_PERSIST_KEY, item)
        return True
    except Exception as e:
        print(f"[redis] pending_persist_push id={news_id} 失败: {e}")
        return False


def pending_persist_push_batch(news_ids: list, table_names: list = None) -> int:
    """
    批量推入待持久化 ID。

    Args:
        news_ids: 新闻 ID 列表
        table_names: 对应的表名列表（可选，用于区分不同表的相同 ID）

    Returns:
        推入数量
    """
    try:
        r = _get_client()
        if r is None:
            return 0
        if not news_ids:
            return 0
        if table_names and len(table_names) == len(news_ids):
            items = [_pack_pending_item(nid, tname) for nid, tname in zip(news_ids, table_names)]
        else:
            items = [str(nid) for nid in news_ids]
        r.rpush(NEWS_PENDING_PERSIST_KEY, *items)
        return len(news_ids)
    except Exception as e:
        print(f"[redis] pending_persist_push_batch 失败: {e}")
        return 0


def pending_persist_pop_batch(count: int = 200) -> list:
    """
    原子批量获取并删除 news:pending_persist 中最多 count 个项。
    使用 LRANGE + LTRIM 保证原子性（单线程持久化线程，无竞争）。

    Args:
        count: 最多获取数量（默认 200）

    Returns:
        项字符串列表，格式为 "table_name:news_id" 或 "news_id"
        使用 _unpack_pending_item() 解包为 (news_id, table_name)
    """
    try:
        r = _get_client()
        if r is None:
            return []
        # 原子操作：先 LRANGE 读取，再 LTRIM 删除
        pipe = r.pipeline(transaction=True)
        pipe.lrange(NEWS_PENDING_PERSIST_KEY, 0, count - 1)
        pipe.ltrim(NEWS_PENDING_PERSIST_KEY, count, -1)
        results = pipe.execute()
        items = results[0] if results and results[0] else []
        # 确保返回字符串列表
        return [item.decode() if isinstance(item, bytes) else item for item in items]
    except Exception as e:
        print(f"[redis] pending_persist_pop_batch 失败: {e}")
        return []


def pending_persist_size() -> int:
    """获取 news:pending_persist List 的长度（待持久化数量）"""
    try:
        r = _get_client()
        if r is None:
            return 0
        return r.llen(NEWS_PENDING_PERSIST_KEY)
    except Exception:
        return 0
