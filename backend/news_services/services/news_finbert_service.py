"""
news_services/services/news_finbert_service.py — FinBERT 金融情感分析服务

在 LLM 分析层与持久化层之间插入的一层金融领域细粒度情感分析。
复用 DDL 已预留的 4 个扩展字段（不需要 ALTER TABLE）：
  title_sentiment       ← FinBERT 综合得分 = pos - neg
  title_sentiment_label ← FinBERT 三分类（1=正/0=中/-1=负）
  sentiment_confidence  ← FinBERT 主类置信度 = max(p) （同时作为完成标记）
  sentiment_volatility  ← FinBERT 概率分布归一化熵

【工作流程（每个线程独立循环）】
  1. LRANGE+LTRIM news:pending_finbert  → 原子弹出最多 BATCH_SIZE 个待分析项
  2. GET news:data:{table}:{id}         → 批量读取完整新闻 JSON
  3. 过滤：ai_analyze_time 为空（LLM 未完成）→ 放回 pending_finbert
         sentiment_confidence 已有值（已分析）→ 跳过
  4. 拼接 title + content 喂 FinBERT 模型
  5. news_data_update(id, {4 个字段}) → 回写 Redis
  6. RPUSH news:pending_persist        → 衔接下游持久化

【线程安全】
  - 多线程 LRANGE+LTRIM 之间存在窄竞态窗口，靠 sentiment_confidence 幂等过滤兜底
  - FinbertClient 内部对 model.forward 加 _infer_lock，避免多线程同时挤压模型
  - event.wait 空闲休眠
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional

from utils.redis_client_compat import (
    _unpack_pending_item,
    news_data_batch_get,
    news_data_update,
    pending_finbert_pop_batch,
    pending_finbert_push,
    pending_finbert_push_batch,
    pending_finbert_size,
    pending_persist_push_batch,
    pending_persist_size,
)

from news_services.config import (
    FINBERT_BATCH_SIZE,
    FINBERT_ENABLED,
    FINBERT_IDLE_WAIT,
    FINBERT_MAX_RETRIES,
    FINBERT_THREADS,
)
from news_services.services.base_news_service import BaseNewsService
from news_services.utils.finbert_client import FinbertClient


logger = logging.getLogger("news_finbert_service")


# ═══════════════════════════════════════════════════════════════════
#  字段校验（与 LLM 输出对齐，再做一次范围钳位防御）
# ═══════════════════════════════════════════════════════════════════

def _validate_single(data: dict) -> dict:
    """钳位 FinBERT 输出到合法范围"""
    cleaned: Dict[str, Any] = {}
    try:
        ts = data.get("title_sentiment")
        if ts is not None:
            ts = float(ts)
            cleaned["title_sentiment"] = max(-1.0, min(1.0, ts))
    except (TypeError, ValueError):
        pass

    try:
        tsl = data.get("title_sentiment_label")
        if tsl is not None:
            tsl = int(tsl)
            cleaned["title_sentiment_label"] = max(-1, min(1, tsl))
    except (TypeError, ValueError):
        pass

    try:
        sc = data.get("sentiment_confidence")
        if sc is not None:
            sc = float(sc)
            cleaned["sentiment_confidence"] = max(0.0, min(1.0, sc))
    except (TypeError, ValueError):
        pass

    try:
        sv = data.get("sentiment_volatility")
        if sv is not None:
            sv = float(sv)
            cleaned["sentiment_volatility"] = max(0.0, min(1.0, sv))
    except (TypeError, ValueError):
        pass

    return cleaned


# ═══════════════════════════════════════════════════════════════════
#  FinBERT 批量调用（带重试）
# ═══════════════════════════════════════════════════════════════════

def _call_finbert_batch_with_retry(finbert_client: FinbertClient, texts: List[str]) -> List[dict]:
    if finbert_client is None or not texts:
        return []

    last_error = ""
    for attempt in range(1, FINBERT_MAX_RETRIES + 2):
        try:
            result = finbert_client.predict_batch(texts)
            if result and any(result):
                if attempt > 1:
                    logger.info("[finbert] 第%d次尝试成功 | batch_size=%d", attempt, len(texts))
                return result
            last_error = "FinBERT 返回空结果"
        except Exception as e:
            last_error = str(e)
            logger.warning("[finbert] 第%d次尝试失败: %s | batch_size=%d", attempt, e, len(texts))
        if attempt <= FINBERT_MAX_RETRIES:
            time.sleep(1)

    logger.error("[finbert] 重试后仍失败: %s | batch_size=%d", last_error, len(texts))
    return []


# ═══════════════════════════════════════════════════════════════════
#  服务类
# ═══════════════════════════════════════════════════════════════════

class NewsFinbertService(BaseNewsService):
    """FinBERT 情感分析服务（多线程消费 pending_finbert，写回 4 字段后推入 pending_persist）"""

    def __init__(self):
        super().__init__(service_name="NewsFinbertService")
        self._client: Optional[FinbertClient] = None
        self._threads: List[threading.Thread] = []
        self._stop_event = threading.Event()
        self._initialized = False
        self._init_lock = threading.Lock()

    # ─────────────────────────────────────────────────────────────
    #  客户端初始化
    # ─────────────────────────────────────────────────────────────

    def _init_client(self):
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            try:
                self._client = FinbertClient()
                ok = self._client.warmup()
                self._initialized = True
                if ok and self._client.is_available():
                    self.logger.info("[news_finbert] FinBERT 客户端初始化完成（单例）")
                else:
                    self.logger.warning(
                        "[news_finbert] FinBERT 模型加载失败，服务将以旁路模式运行"
                        "（pending_finbert 数据直接转入 pending_persist，不影响主流水线）"
                    )
            except Exception as e:
                self.logger.error("[news_finbert] FinBERT 客户端初始化失败: %s", e)
                self._client = None
                self._initialized = True

    # ─────────────────────────────────────────────────────────────
    #  线程主循环
    # ─────────────────────────────────────────────────────────────

    def _worker_loop(self, thread_id: int):
        self.logger.info("[news_finbert] 线程 %d 启动", thread_id)
        while not self._stop_event.is_set():
            try:
                processed = self._process_once(thread_id)
                if processed == 0:
                    self._stop_event.wait(timeout=FINBERT_IDLE_WAIT)
            except Exception as e:
                self.logger.error("[news_finbert] 线程 %d 异常（继续运行）: %s", thread_id, e)
                self._stop_event.wait(timeout=FINBERT_IDLE_WAIT)
        self.logger.info("[news_finbert] 线程 %d 已停止", thread_id)

    def _process_once(self, thread_id: int) -> int:
        # Step 1: 原子批量弹出（"table:news_id" 或 "news_id"）
        raw_items = pending_finbert_pop_batch(FINBERT_BATCH_SIZE)
        if not raw_items:
            return 0

        id_table_pairs: List[tuple] = []
        for item in raw_items:
            news_id, table_name = _unpack_pending_item(item)
            if news_id is not None:
                id_table_pairs.append((news_id, table_name))

        if not id_table_pairs:
            return 0

        ids = [p[0] for p in id_table_pairs]
        table_names = [p[1] for p in id_table_pairs]

        # ★ 旁路模式：模型不可用时，直接把已 LLM 完成的记录推入 pending_persist，不阻塞流水线
        if self._client is None or not self._client.is_available():
            # 仍需读取 Redis 校验 LLM 是否完成
            news_list = news_data_batch_get(ids, table_names)
            forward_ids: List[int] = []
            forward_tables: List[str] = []
            rollback_ids: List[int] = []
            rollback_tables: List[str] = []
            for record in news_list or []:
                nid = record.get("id")
                if not nid:
                    continue
                ai_t = record.get("ai_analyze_time")
                tname = record.get("table_name") or ""
                if not ai_t or str(ai_t).strip() in ("", "None", "null"):
                    rollback_ids.append(int(nid))
                    rollback_tables.append(tname)
                else:
                    forward_ids.append(int(nid))
                    forward_tables.append(tname)
            if rollback_ids:
                try:
                    pending_finbert_push_batch(rollback_ids, rollback_tables)
                except Exception:
                    pass
            if forward_ids:
                try:
                    pending_persist_push_batch(forward_ids, forward_tables)
                    self.logger.info(
                        "[news_finbert] 线程%d: 旁路模式 | 取:%d 转发persist:%d 回滚:%d",
                        thread_id, len(id_table_pairs), len(forward_ids), len(rollback_ids),
                    )
                except Exception as e:
                    self.logger.warning("[news_finbert] 旁路转发失败: %s", e)
            return len(forward_ids)

        # Step 2: 批量读取 Redis
        news_list = news_data_batch_get(ids, table_names)
        if not news_list:
            self.logger.warning(
                "[news_finbert] 线程%d: Redis 批量读取为空，id前5=%s", thread_id, ids[:5]
            )
            return 0

        # Step 3: 过滤
        valid_items: List[Dict[str, Any]] = []
        rollback_ids: List[int] = []
        rollback_tables: List[str] = []

        for record in news_list:
            news_id = record.get("id")
            if not news_id:
                continue

            table_name = record.get("table_name") or ""

            # LLM 还没完成 → 放回 pending_finbert
            ai_analyze_time = record.get("ai_analyze_time")
            if not ai_analyze_time or str(ai_analyze_time).strip() in ("", "None", "null"):
                rollback_ids.append(int(news_id))
                rollback_tables.append(table_name)
                continue

            # 已分析过 → 直接跳过（幂等）
            sc = record.get("sentiment_confidence")
            if sc is not None and str(sc).strip() not in ("", "None", "null"):
                # 但要确保下游持久化能继续，把它推到 pending_persist
                continue

            title = (record.get("title") or "").strip()
            content = (record.get("content") or "").strip()
            text = (title + "。" + content).strip("。 ").strip()
            if not text:
                continue

            valid_items.append({
                "id":         int(news_id),
                "table_name": table_name,
                "text":       text,
            })

        # 把"LLM 未完成"的 id 放回 pending_finbert
        if rollback_ids:
            try:
                pending_finbert_push_batch(rollback_ids, rollback_tables)
                self.logger.debug(
                    "[news_finbert] 线程%d: %d 条 LLM 未完成，已放回 pending_finbert",
                    thread_id, len(rollback_ids),
                )
            except Exception as e:
                self.logger.warning("[news_finbert] 放回 pending_finbert 失败: %s", e)

        if not valid_items:
            return 0

        # Step 4: 调用 FinBERT
        texts = [it["text"] for it in valid_items]
        self.logger.info(
            "[news_finbert] 线程%d: 开始 FinBERT 分析 %d 条", thread_id, len(texts)
        )
        results = _call_finbert_batch_with_retry(self._client, texts)

        if not results or len(results) != len(valid_items):
            self.logger.warning(
                "[news_finbert] 线程%d: FinBERT 返回不匹配（got=%d, need=%d），回滚",
                thread_id, len(results) if results else 0, len(valid_items),
            )
            # 整批回滚
            try:
                pending_finbert_push_batch(
                    [it["id"] for it in valid_items],
                    [it["table_name"] for it in valid_items],
                )
            except Exception:
                pass
            return 0

        # Step 5: 写回 Redis
        success_ids: List[int] = []
        success_tables: List[str] = []
        for it, raw in zip(valid_items, results):
            cleaned = _validate_single(raw or {})
            if not cleaned or "sentiment_confidence" not in cleaned:
                # 单条失败，回滚到队列
                try:
                    pending_finbert_push(it["id"], it["table_name"])
                except Exception:
                    pass
                continue

            cleaned["table_name"] = it["table_name"]
            if news_data_update(it["id"], cleaned):
                success_ids.append(it["id"])
                success_tables.append(it["table_name"])

        # Step 6: 推入 pending_persist
        if success_ids:
            pushed = pending_persist_push_batch(success_ids, success_tables)
            self.logger.info(
                "[news_finbert] 线程%d: 完成 | 取:%d 有效:%d 成功:%d 推入persist:%d",
                thread_id, len(id_table_pairs), len(valid_items), len(success_ids), pushed,
            )

        return len(success_ids)

    # ─────────────────────────────────────────────────────────────
    #  对外接口
    # ─────────────────────────────────────────────────────────────

    def start(self) -> Dict[str, Any]:
        if not FINBERT_ENABLED:
            self.logger.info(
                "[news_finbert] FINBERT_ENABLED=False，跳过启动；"
                "LLM 服务会直接推入 pending_persist，本服务不参与流水线"
            )
            return self.wrap_success(message="finbert disabled by config")
        try:
            self._init_client()
            # 模型不可用也允许启动（线程会进入旁路模式：仅做队列搬运）
            if self._client is None:
                self.logger.warning(
                    "[news_finbert] FinBERT 客户端不存在，仍启动旁路线程把 pending_finbert 转发到 pending_persist"
                )
            elif not self._client.is_available():
                self.logger.warning(
                    "[news_finbert] FinBERT 模型不可用（网络/依赖问题），启动旁路线程把 pending_finbert 转发到 pending_persist；"
                    "可调用 finbert_client.reset_and_retry() 在网络恢复后重试加载"
                )

            alive_count = sum(1 for t in self._threads if t.is_alive())
            if alive_count >= FINBERT_THREADS:
                self.logger.info(
                    "[news_finbert] 后台线程已全部运行（%d线程），跳过", alive_count
                )
                return self.wrap_success(message=f"already running with {alive_count} threads")

            self._stop_event.clear()
            self._threads = []
            for i in range(FINBERT_THREADS):
                t = threading.Thread(
                    target=self._worker_loop,
                    args=(i + 1,),
                    name=f"news-finbert-{i + 1}",
                    daemon=True,
                )
                t.start()
                self._threads.append(t)
            self.logger.info("[news_finbert] %d 条 FinBERT 分析线程已启动", FINBERT_THREADS)
            return self.wrap_success(message=f"started with {FINBERT_THREADS} threads")
        except Exception as e:
            self.log_exception("启动 FinBERT 引擎", e)
            return self.wrap_error(f"启动失败: {e}")

    def stop(self) -> Dict[str, Any]:
        try:
            self._stop_event.set()
            for t in self._threads:
                if t.is_alive():
                    t.join(timeout=5)
            self._threads = []
            self.logger.info("[news_finbert] 所有 FinBERT 线程已停止")
            return self.wrap_success(message="stopped")
        except Exception as e:
            self.log_exception("停止 FinBERT 引擎", e)
            return self.wrap_error(f"停止失败: {e}")

    def get_status(self) -> Dict[str, Any]:
        alive_threads = [t.name for t in self._threads if t.is_alive()]
        return self.wrap_success(data={
            "enabled":              FINBERT_ENABLED,
            "initialized":          self._initialized,
            "num_threads":          FINBERT_THREADS,
            "alive_threads":        len(alive_threads),
            "thread_names":         alive_threads,
            "pending_finbert_size": pending_finbert_size(),
            "pending_persist_size": pending_persist_size(),
            "batch_size":           FINBERT_BATCH_SIZE,
            "idle_wait_seconds":    FINBERT_IDLE_WAIT,
        })

    def get_pending_count(self) -> int:
        try:
            return pending_finbert_size()
        except Exception as e:
            self.log_exception("获取 pending_finbert_size", e)
            return 0


# ═══════════════════════════════════════════════════════════════════
#  模块级单例
# ═══════════════════════════════════════════════════════════════════

news_finbert_service = NewsFinbertService()
