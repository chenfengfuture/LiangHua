"""
stock_llm.py — 上市公司 LLM 分析框架（高性能 + 会话复用 + 自动注销）

核心特性：
1. 异步非阻塞：全链路 async/await，支持高并发
2. 会话上下文复用：每个 session_id 独立维护对话历史，首次自动注入 SYSTEM_PROMPT
3. 智能缓存：30 天有效期，基于 stocks_info 表的 update_time 字段（若股票信息未更新则不重复调用 LLM）
4. 自动注销：内存会话超时清理（默认 30 分钟），后台定期扫描
5. 容错机制：重试（指数退避）、超时控制、JSON 解析降级
6. 数据库连接池：避免频繁创建连接，提升性能
7. 限流保护：可选的并发控制（Semaphore）
8. 数据存储：使用现有的 stocks_info 表存储分析结果，不修改表结构

设计原则：
- 不修改现有 LLM 代码和逻辑，仅调用现有接口
- 不修改现有 stocks_info 表结构，适配现有字段
- 线程安全：所有共享数据结构使用 asyncio.Lock 保护
- 高性能：异步 I/O，批量数据库操作
- 可观测性：结构化日志，性能埋点，错误分类
- 安全性：输入验证，会话 ID 验证，防注入攻击
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from utils.db import get_cursor
from utils.llm import call_llm_with_history

# 配置日志
logger = logging.getLogger(__name__)

# ==================== 常量配置 ====================
# 系统提示词
SYSTEM_PROMPT = """
你是一个专业的股票研究分析师。用户会给你一个股票代码和股票名称。
你需要通过联网搜索功能，深度分析该公司的以下信息：

【必填字段 - 公司核心信息】
1. 主营业务（main_business）：公司最主要的业务是什么，100字以内简明扼要描述
2. 实际控制人（actual_controller）：公司的最终控制方是谁（如无明确控制人则填null）
3. 是否具有国资背景（is_state_owned）：true表示有国资背景，false表示无国资背景

【必填字段 - 财务指标】（请尽可能从最新年报/季报获取精确数字）
4. 营收（revenue）：最新财务年度营业收入，单位为元
5. 净利润（net_profit）：最新财务年度净利润，单位为元
6. 市盈率（pe_ratio）：滚动市盈率 TTM
7. 市净率（pb_ratio）：市净率
8. 净资产收益率（roe）：最新财务年度 ROE，百分比数值（如 15.5 表示 15.5%）
9. 资产负债率（debt_ratio）：最新财务年度资产负债率，百分比数值

【动态信息字段】
10. 所属行业（industry）：公司所属证监会行业分类（如"银行"、"医药生物"、"电子"等）
11. 概念板块（concept）：公司涉及的主要概念板块（如"人工智能"、"新能源"、"芯片"等），多个概念用顿号分隔
12. 国有股权比例（state_share_ratio）：国有资本持股比例，百分比数值（如 35.5 表示 35.5%），若无则填null
13. 转型趋势（transformation_trend）：近期业务转型、战略调整或重大变化，100字以内
14. 所属地区（region）：公司注册地所属省份/直辖市（如"广东"、"北京"、"上海"等）

【输出要求】
- 必须以严格的JSON格式输出，不要包含任何其他解释文字
- 所有数值字段使用number类型，不要使用字符串
- 如果某项信息无法获取，设为null
- 营收、净利润数值较大，单位统一为元（不要加"亿"或"万"后缀）
- 百分比字段使用数值，如 15.5 表示 15.5%

JSON格式如下：
{
  "main_business": "string（主营业务描述，100字以内）",
  "is_state_owned": boolean（是否有国资背景）,
  "actual_controller": "string or null（实际控制人）",
  "revenue": number or null（营业收入，元）,
  "net_profit": number or null（净利润，元）,
  "pe_ratio": number or null（滚动市盈率）,
  "pb_ratio": number or null（市净率）,
  "roe": number or null（净资产收益率，百分比数值）,
  "debt_ratio": number or null（资产负债率，百分比数值）,
  "industry": "string or null（所属行业分类）",
  "concept": "string or null（概念板块，顿号分隔）",
  "state_share_ratio": number or null（国有股权比例，百分比数值）,
  "transformation_trend": "string or null（转型趋势描述）",
  "region": "string or null（所属省份/直辖市）"
}
"""

# 缓存配置
CACHE_TTL_DAYS = 90  # 缓存有效期（天）

# 会话配置
SESSION_TIMEOUT_SEC = 1800  # 会话超时时间（秒，30分钟）
SESSION_CLEANUP_INTERVAL_SEC = 300  # 会话清理间隔（秒，5分钟）
MAX_HISTORY_PAIRS = 20  # 最大历史对话对数（user+assistant为一对）

# LLM 调用配置
LLM_TIMEOUT_SEC = 45  # LLM调用总超时（秒）
LLM_MAX_RETRIES = 2  # 最大重试次数
LLM_RETRY_BACKOFF_BASE = 1.0  # 指数退避基础时间（秒）
LLM_MAX_CONCURRENT = 10  # 最大并发LLM调用数

# 安全性配置
MAX_SYMBOL_LENGTH = 20  # 股票代码最大长度
MAX_NAME_LENGTH = 50  # 股票名称最大长度
SESSION_ID_PATTERN = r'^[a-zA-Z0-9\-_]+$'  # 会话ID正则（允许字母数字下划线减号）

# ==================== 字段映射配置 ====================
# LLM分析结果字段到 stocks_info 表字段的映射
FIELD_MAPPING = {
    # 核心信息
    "main_business": "main_business",  # 主营业务
    "is_state_owned": "is_state_owned",  # 是否国企
    "actual_controller": "actual_controller",  # 实际控制人
    # 财务指标
    "revenue": "revenue",  # 营收
    "net_profit": "net_profit",  # 净利润
    "pe_ratio": "pe_ttm",  # 市盈率 -> 滚动市盈率
    "pb_ratio": "pb",  # 市净率
    "roe": "roe",  # 净资产收益率
    "debt_ratio": "debt_ratio",  # 资产负债率
    # 动态信息
    "industry": "industry",  # 所属行业
    "concept": "concept",  # 概念板块
    "state_share_ratio": "state_share_ratio",  # 国有股权比例
    "transformation_trend": "introduction",  # 转型趋势 -> 公司简介
    "region": "region",  # 所属地区
}

# ==================== 全局数据结构 ====================
# 会话存储：session_id -> {"history": List[Dict], "last_access": float}
_sessions: Dict[str, Dict[str, Any]] = {}
_session_lock = asyncio.Lock()  # 保护 _sessions 的锁

# LLM并发限制器
_llm_semaphore = asyncio.Semaphore(LLM_MAX_CONCURRENT)

# 清理任务句柄
_cleanup_task: Optional[asyncio.Task] = None

# ==================== 工具函数 ====================
def validate_session_id(session_id: str) -> bool:
    """验证会话ID格式"""
    if not session_id or len(session_id) > 100:
        return False
    return bool(re.match(SESSION_ID_PATTERN, session_id))

def validate_symbol_and_name(symbol: str, name: str) -> Tuple[bool, Optional[str]]:
    """验证股票代码和名称"""
    if not symbol or len(symbol) > MAX_SYMBOL_LENGTH:
        return False, f"股票代码长度不能超过{MAX_SYMBOL_LENGTH}字符"
    if not name or len(name) > MAX_NAME_LENGTH:
        return False, f"股票名称长度不能超过{MAX_NAME_LENGTH}字符"
    return True, None

def sanitize_json_response(raw_text: str) -> Dict[str, Any]:
    """
    清洗LLM返回的JSON响应，处理markdown代码块等格式
    
    Args:
        raw_text: LLM返回的原始文本
        
    Returns:
        解析后的JSON字典
    """
    if not raw_text:
        return {"error": "LLM返回空响应"}
    
    text = raw_text.strip()
    
    # 去除markdown代码块
    if text.startswith("```json"):
        text = text[7:]  # 移除 ```json
    elif text.startswith("```"):
        text = text[3:]  # 移除 ```
    
    if text.endswith("```"):
        text = text[:-3]  # 移除结尾的 ```
    
    text = text.strip()
    
    # 尝试提取JSON对象（最外层的{}）
    start = text.find("{")
    end = text.rfind("}")
    
    if start != -1 and end != -1 and end > start:
        json_str = text[start:end+1]
    else:
        json_str = text
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失败，原始文本: {raw_text[:200]}..., 错误: {e}")
        # 尝试修复常见的JSON格式问题
        try:
            # 替换单引号为双引号
            json_str = json_str.replace("'", '"')
            # 移除尾随逗号
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            return json.loads(json_str)
        except:
            return {"error": f"JSON解析失败: {str(e)}", "raw_response": raw_text[:500]}

# ==================== 股票信息管理器 ====================
class StockInfoManager:
    """股票信息管理器（使用现有的stocks_info表）"""
    
    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """
        规范化股票代码，确保有交易所后缀
        
        Args:
            symbol: 原始股票代码，如 '000001' 或 '000001.SZ'
            
        Returns:
            规范化后的股票代码，如 '000001.SZ'
        """
        # 如果已经有后缀，直接返回
        if '.' in symbol:
            return symbol
        
        # 根据股票代码前缀添加后缀
        if symbol.startswith('6'):
            return f"{symbol}.SH"
        elif symbol.startswith('0') or symbol.startswith('3'):
            return f"{symbol}.SZ"
        elif symbol.startswith('4') or symbol.startswith('8'):
            return f"{symbol}.BJ"
        else:
            # 未知格式，返回原样
            return symbol
    
    @staticmethod
    async def get_cached_analysis(stock_code: str) -> Optional[Dict[str, Any]]:
        """
        从stocks_info表获取缓存的LLM分析结果
        
        Args:
            stock_code: 股票代码
            
        Returns:
            缓存的LLM分析结果字典，如果缓存不存在或已过期则返回None
        """
        try:
            # 规范化股票代码，确保有交易所后缀
            normalized_code = StockInfoManager.normalize_symbol(stock_code)
            with get_cursor() as cur:
                # 查询stocks_info表，检查update_time是否在缓存有效期内
                cur.execute(
                    "SELECT main_business, is_state_owned, actual_controller, "
                    "introduction, revenue, net_profit, pe_ttm, pb, roe, debt_ratio, "
                    "industry, concept, state_share_ratio, region, update_time "
                    "FROM stocks_info WHERE symbol = %s",
                    (normalized_code,)
                )
                row = cur.fetchone()
                
                if row and row.get("update_time"):
                    update_time = row["update_time"]
                    if isinstance(update_time, str):
                        update_time = datetime.fromisoformat(update_time.replace('Z', '+00:00'))
                    
                    # 检查是否在缓存有效期内
                    cache_expiry_time = update_time + timedelta(days=CACHE_TTL_DAYS)
                    if datetime.now() < cache_expiry_time:
                        # 构建LLM分析结果格式（包含所有扩展字段）
                        result = {
                            # 核心信息
                            "main_business": row.get("main_business"),
                            "is_state_owned": bool(row.get("is_state_owned")) if row.get("is_state_owned") is not None else None,
                            "actual_controller": row.get("actual_controller"),
                            # 财务指标
                            "revenue": float(row.get("revenue")) if row.get("revenue") is not None else None,
                            "net_profit": float(row.get("net_profit")) if row.get("net_profit") is not None else None,
                            "pe_ratio": float(row.get("pe_ttm")) if row.get("pe_ttm") is not None else None,
                            "pb_ratio": float(row.get("pb")) if row.get("pb") is not None else None,
                            "roe": float(row.get("roe")) if row.get("roe") is not None else None,
                            "debt_ratio": float(row.get("debt_ratio")) if row.get("debt_ratio") is not None else None,
                            # 动态信息
                            "industry": row.get("industry"),
                            "concept": row.get("concept"),
                            "state_share_ratio": float(row.get("state_share_ratio")) if row.get("state_share_ratio") is not None else None,
                            "transformation_trend": row.get("introduction"),  # 转型趋势使用公司简介字段
                            "region": row.get("region"),
                        }
                        
                        # 检查关键字段是否有足够的数据，如果数据不足则不使用缓存
                        # 关键字段检查：需要至少2个关键字段有值才认为是有效缓存
                        # 关键字段包括：main_business, revenue, pe_ratio, actual_controller, industry
                        key_fields = ["main_business", "revenue", "pe_ratio", "actual_controller", "industry"]
                        valid_field_count = sum(1 for field in key_fields if result.get(field) is not None)
                        
                        # 检查是否有足够的数据：至少2个关键字段有值
                        has_enough_data = valid_field_count >= 2
                        
                        if has_enough_data:
                            logger.debug(f"股票 {stock_code}（规范化为 {normalized_code}）缓存有效，{valid_field_count}个关键字段有数据")
                            return result
                        else:
                            logger.debug(f"股票 {stock_code}（规范化为 {normalized_code}）的缓存数据不足（只有{valid_field_count}个关键字段有数据），将触发LLM重新分析")
                    else:
                        logger.debug(f"股票 {stock_code}（规范化为 {normalized_code}）的LLM分析缓存已过期")
        except Exception as e:
            logger.error(f"查询股票缓存失败: {e}")
        
        return None
    
    @staticmethod
    async def update_stock_info(stock_code: str, llm_result: Dict[str, Any]):
        """
        将LLM分析结果更新到stocks_info表（异步后台执行）

        Args:
            stock_code: 股票代码
            llm_result: LLM分析结果
        """
        try:
            # 规范化股票代码，确保有交易所后缀
            normalized_code = StockInfoManager.normalize_symbol(stock_code)
            
            # 构建更新SQL，只更新有值的字段
            update_fields = []
            update_values = []
            
            # 先获取现有简介（如果存在转型趋势字段）
            existing_intro = ""
            if "transformation_trend" in llm_result and llm_result["transformation_trend"] is not None:
                try:
                    with get_cursor() as cur:
                        cur.execute(
                            "SELECT introduction FROM stocks_info WHERE symbol = %s",
                            (normalized_code,)
                        )
                        existing_intro_row = cur.fetchone()
                        if existing_intro_row:
                            existing_intro = existing_intro_row.get("introduction", "")
                except Exception as e:
                    logger.warning(f"获取现有简介失败: {e}")
            
            for llm_field, db_field in FIELD_MAPPING.items():
                if llm_field in llm_result and llm_result[llm_field] is not None:
                    # 特殊处理转型趋势字段，合并到公司简介
                    if llm_field == "transformation_trend":
                        transformation = llm_result[llm_field]
                        if transformation and transformation.strip():
                            new_intro = f"{existing_intro}\n\n近期转型趋势：{transformation}".strip()
                            update_fields.append(f"{db_field} = %s")
                            update_values.append(new_intro)
                    else:
                        update_fields.append(f"{db_field} = %s")
                        update_values.append(llm_result[llm_field])
            
            if update_fields:
                with get_cursor(commit=True) as cur:
                    sql = f"UPDATE stocks_info SET {', '.join(update_fields)} WHERE symbol = %s"
                    update_values.append(normalized_code)
                    cur.execute(sql, tuple(update_values))
                
                logger.debug(f"股票信息已更新: {stock_code}（规范化为 {normalized_code}），更新了 {len(update_fields)} 个字段")
            else:
                logger.debug(f"没有需要更新的字段: {stock_code}（规范化为 {normalized_code}）")
                
        except Exception as e:
            logger.error(f"更新股票信息失败: {e}")
    
    @staticmethod
    async def get_stock_update_time(stock_code: str) -> Optional[datetime]:
        """
        获取股票信息的最后更新时间

        Args:
            stock_code: 股票代码

        Returns:
            最后更新时间，如果股票不存在则返回None
        """
        try:
            # 规范化股票代码，确保有交易所后缀
            normalized_code = StockInfoManager.normalize_symbol(stock_code)
            with get_cursor() as cur:
                cur.execute(
                    "SELECT update_time FROM stocks_info WHERE symbol = %s",
                    (normalized_code,)
                )
                row = cur.fetchone()
                if row and row.get("update_time"):
                    update_time = row["update_time"]
                    if isinstance(update_time, str):
                        update_time = datetime.fromisoformat(update_time.replace('Z', '+00:00'))
                    return update_time
        except Exception as e:
            logger.error(f"查询股票更新时间失败: {e}")

        return None

# ==================== 会话管理 ====================
class SessionManager:
    """会话管理器"""
    
    @staticmethod
    async def get_or_create_session(session_id: str) -> Dict[str, Any]:
        """
        获取或创建会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话字典 {"history": List[Dict], "last_access": float}
        """
        async with _session_lock:
            now = time.time()
            if session_id not in _sessions:
                # 创建新会话，注入系统提示词
                _sessions[session_id] = {
                    "history": [
                        {"role": "system", "content": SYSTEM_PROMPT}
                    ],
                    "last_access": now
                }
                logger.debug(f"创建新会话: {session_id}")
            else:
                # 更新最后访问时间
                _sessions[session_id]["last_access"] = now
            
            return _sessions[session_id]
    
    @staticmethod
    async def cleanup_expired_sessions():
        """
        清理过期会话（后台任务）
        """
        async with _session_lock:
            now = time.time()
            expired_count = 0
            to_delete = []
            
            for session_id, session_data in _sessions.items():
                last_access = session_data["last_access"]
                if now - last_access > SESSION_TIMEOUT_SEC:
                    to_delete.append(session_id)
            
            for session_id in to_delete:
                del _sessions[session_id]
                expired_count += 1
            
            if expired_count > 0:
                logger.info(f"清理了 {expired_count} 个过期会话")
    
    @staticmethod
    async def get_session_count() -> int:
        """获取当前活跃会话数量"""
        async with _session_lock:
            return len(_sessions)
    
    @staticmethod
    async def clear_session(session_id: str) -> bool:
        """
        主动清除指定会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功清除
        """
        async with _session_lock:
            if session_id in _sessions:
                del _sessions[session_id]
                logger.debug(f"主动清除会话: {session_id}")
                return True
            return False

# ==================== LLM 调用管理 ====================
class LLMManager:
    """LLM调用管理器"""
    
    @staticmethod
    async def analyze_stock_with_retry(symbol: str, name: str, history: List[Dict]) -> Dict[str, Any]:
        """
        调用LLM分析股票信息（带重试机制）
        
        Args:
            symbol: 股票代码
            name: 股票名称
            history: 历史对话记录（包含系统提示词）
            
        Returns:
            分析结果字典
        """
        user_message = f"股票代码：{symbol}，股票名称：{name}"
        
        for attempt in range(LLM_MAX_RETRIES):
            try:
                # 使用信号量控制并发
                async with _llm_semaphore:
                    # 设置超时
                    result = await asyncio.wait_for(
                        asyncio.to_thread(
                            call_llm_with_history,
                            message=user_message,
                            history=history,
                            temperature=0.1,  # 低温度保证JSON稳定性
                            max_tokens=1024
                        ),
                        timeout=LLM_TIMEOUT_SEC
                    )
                
                # 解析响应
                parsed = sanitize_json_response(result)

                # 如果解析成功且没有error字段，返回结果
                if "error" not in parsed:
                    # 确保返回格式符合要求
                    expected_fields = ["main_business", "is_state_owned", "actual_controller", 
                                     "revenue", "net_profit", "pe_ratio", "pb_ratio",
                                     "roe", "debt_ratio", "industry", "concept", 
                                     "state_share_ratio", "transformation_trend", "region"]
                    
                    for field in expected_fields:
                        if field not in parsed:
                            parsed[field] = None
                    
                    return parsed
                else:
                    logger.warning(f"LLM返回错误: {parsed.get('error')}")
                    # 如果是最后一次尝试，返回错误
                    if attempt == LLM_MAX_RETRIES - 1:
                        return parsed
            
            except asyncio.TimeoutError:
                logger.warning(f"LLM调用超时（第{attempt+1}次尝试）")
                if attempt == LLM_MAX_RETRIES - 1:
                    return {"error": "LLM调用超时"}
            except Exception as e:
                logger.error(f"LLM调用异常（第{attempt+1}次尝试）: {e}")
                if attempt == LLM_MAX_RETRIES - 1:
                    return {"error": f"LLM调用异常: {str(e)}"}
            
            # 指数退避
            if attempt < LLM_MAX_RETRIES - 1:
                delay = LLM_RETRY_BACKOFF_BASE * (2 ** attempt)
                await asyncio.sleep(delay)
        
        return {"error": "LLM调用失败，达到最大重试次数"}

# ==================== 主服务类 ====================
class StockLLMAnalyzer:
    """股票LLM分析服务主类"""
    
    def __init__(self):
        self.stock_info_manager = StockInfoManager()
        self.session_manager = SessionManager()
        self.llm_manager = LLMManager()
        self._initialized = False
    
    async def initialize(self):
        """初始化服务（启动清理任务）"""
        if self._initialized:
            return
        
        try:
            # 注意：不再需要创建独立的缓存表，直接使用现有的stocks_info表
            
            # 启动会话清理任务
            global _cleanup_task
            if _cleanup_task is None or _cleanup_task.done():
                _cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self._initialized = True
            logger.info("StockLLMAnalyzer 初始化完成（使用现有stocks_info表）")
        except Exception as e:
            logger.error(f"StockLLMAnalyzer 初始化失败: {e}")
            raise
    
    async def _cleanup_loop(self):
        """后台清理循环"""
        while True:
            try:
                await asyncio.sleep(SESSION_CLEANUP_INTERVAL_SEC)
                await self.session_manager.cleanup_expired_sessions()
                
                # 监控日志：记录当前会话数量
                session_count = await self.session_manager.get_session_count()
                if session_count > 10000:
                    logger.warning(f"活跃会话数量超过阈值: {session_count}")
                
            except Exception as e:
                logger.error(f"清理循环异常: {e}")
                # 继续运行，避免因单次异常退出
    
    async def analyze_stock(self, session_id: str, symbol: str, name: str) -> Dict[str, Any]:
        """
        分析股票信息（主入口）
        
        Args:
            session_id: 会话ID
            symbol: 股票代码
            name: 股票名称
            
        Returns:
            统一格式的结果字典
        """
        start_time = time.time()
        
        # 1. 参数验证
        if not validate_session_id(session_id):
            return {
                "success": False,
                "data": None,
                "error": "无效的会话ID格式",
                "session_id": session_id,
                "symbol": symbol,
                "latency_ms": int((time.time() - start_time) * 1000)
            }
        
        valid, error_msg = validate_symbol_and_name(symbol, name)
        if not valid:
            return {
                "success": False,
                "data": None,
                "error": error_msg,
                "session_id": session_id,
                "symbol": symbol,
                "latency_ms": int((time.time() - start_time) * 1000)
            }
        
        # 2. 获取或创建会话
        try:
            session = await self.session_manager.get_or_create_session(session_id)
            history = session["history"]
        except Exception as e:
            logger.error(f"获取会话失败: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"会话管理失败: {str(e)}",
                "session_id": session_id,
                "symbol": symbol,
                "latency_ms": int((time.time() - start_time) * 1000)
            }
        
        # 3. 检查缓存（从stocks_info表）
        cache_hit = False
        cache_start = time.time()
        cached_result = await self.stock_info_manager.get_cached_analysis(symbol)
        cache_latency = int((time.time() - cache_start) * 1000)
        
        if cached_result and "error" not in cached_result:
            cache_hit = True
            result = cached_result
            llm_latency = 0
            logger.debug(f"缓存命中: {symbol}")
        else:
            # 4. 调用LLM
            llm_start = time.time()
            result = await self.llm_manager.analyze_stock_with_retry(symbol, name, history)
            llm_latency = int((time.time() - llm_start) * 1000)
            
            # 5. 更新会话历史（如果成功）
            if "error" not in result:
                # 添加用户消息
                user_message = f"股票代码：{symbol}，股票名称：{name}"
                history.append({"role": "user", "content": user_message})
                
                # 添加助手回复
                history.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})
                
                # 限制历史长度（保留系统提示词后最多20对对话）
                if len(history) > 1 + MAX_HISTORY_PAIRS * 2:  # +1 是系统提示词
                    # 保留系统提示词和最近的MAX_HISTORY_PAIRS对对话
                    history = [history[0]] + history[-(MAX_HISTORY_PAIRS * 2):]
                
                # 异步更新stocks_info表
                asyncio.create_task(self.stock_info_manager.update_stock_info(symbol, result))
        
        # 6. 构建响应
        total_latency = int((time.time() - start_time) * 1000)
        
        response = {
            "success": "error" not in result,
            "data": result if "error" not in result else None,
            "error": result.get("error") if "error" in result else None,
            "session_id": session_id,
            "symbol": symbol,
            "cache_hit": cache_hit,
            "latency_ms": total_latency,
            "cache_latency_ms": cache_latency,
            "llm_latency_ms": llm_latency
        }
        
        # 7. 记录日志
        log_data = {
            "session_id": session_id,
            "symbol": symbol,
            "cache_hit": cache_hit,
            "success": response["success"],
            "latency_ms": total_latency,
            "cache_latency_ms": cache_latency,
            "llm_latency_ms": llm_latency,
            "error": response["error"]
        }
        logger.info(f"股票分析完成: {json.dumps(log_data, ensure_ascii=False)}")
        
        return response
    
    async def clear_session(self, session_id: str) -> Dict[str, Any]:
        """
        主动清除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            操作结果
        """
        success = await self.session_manager.clear_session(session_id)
        return {
            "success": success,
            "data": {"session_id": session_id, "cleared": success},
            "error": None if success else "会话不存在"
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        获取服务统计信息
        
        Returns:
            统计信息字典
        """
        session_count = await self.session_manager.get_session_count()
        
        return {
            "success": True,
            "data": {
                "active_sessions": session_count,
                "llm_concurrent_limit": LLM_MAX_CONCURRENT,
                "cache_ttl_days": CACHE_TTL_DAYS,
                "session_timeout_min": SESSION_TIMEOUT_SEC // 60,
                "cleanup_interval_min": SESSION_CLEANUP_INTERVAL_SEC // 60,
                "storage_table": "stocks_info",  # 使用现有表
                "field_mapping": FIELD_MAPPING  # 字段映射关系
            },
            "error": None
        }

# ==================== 全局单例 ====================
_analyzer_instance: Optional[StockLLMAnalyzer] = None

def get_analyzer() -> StockLLMAnalyzer:
    """获取全局单例"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = StockLLMAnalyzer()
    return _analyzer_instance

# ==================== 异步初始化 ====================
async def initialize_service():
    """初始化服务（应用启动时调用）"""
    analyzer = get_analyzer()
    await analyzer.initialize()

