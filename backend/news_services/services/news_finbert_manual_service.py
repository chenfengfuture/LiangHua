"""
news_services/services/news_finbert_manual_service.py — 手动批量 FinBERT 情感分析服务

提供一个**完全独立**于后台流水线的批量重分析接口：
  1. 直接扫描 MySQL 分表，按条件捞出已 LLM 分析但未做过 FinBERT 的新闻
  2. 调用 FinbertClient 单例做批量推理
  3. 同时更新 Redis（news:data:*）和 MySQL（CASE 批量 UPDATE）

设计要点：
  - 不依赖 / 不污染 news:pending_finbert 队列，避免与后台 NewsFinbertService 争抢
  - 复用 FinbertClient 单例（线程安全），不会重复加载模型
  - 复用 news_persist_service 的 batch_update_ai_case 高性能 CASE 批量更新
  - 即使 Redis 中缺少 news:data:{table}:{id} 也照样写 MySQL（兼容历史数据）
  - 幂等：默认仅处理 sentiment_confidence IS NULL 的记录；force=True 时强制重算

调用流程：
  POST /api/news/finbert/manual_batch?news_type=company,cctv&year_month=202605&limit=500
"""

import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from utils.db import get_news_conn
from utils.redis_client_compat import news_data_update

from models.news_models import NEWS_DB_NAME, NEWS_TYPES, batch_update_ai_case
from news_services.config import FINBERT_BATCH_SIZE
from news_services.services.base_news_service import BaseNewsService
from news_services.services.news_finbert_service import (
    _call_finbert_batch_with_retry,
    _validate_single,
)
from news_services.utils.finbert_client import FinbertClient


logger = logging.getLogger("news_finbert_manual_service")


# 单次扫描每张分表最多条数上限（防止内存爆掉）
_MAX_LIMIT_PER_TABLE = 5000


class NewsFinbertManualService(BaseNewsService):
    """手动批量 FinBERT 分析服务（一次性同步执行，不开后台线程）"""

    def __init__(self):
        super().__init__(service_name="NewsFinbertManualService")
        self._client: Optional[FinbertClient] = None

    # ─────────────────────────────────────────────────────────────
    #  内部工具
    # ─────────────────────────────────────────────────────────────

    def _ensure_client(self) -> bool:
        """懒加载 FinbertClient 单例并预热"""
        if self._client is None:
            self._client = FinbertClient()
        if not self._client.is_available():
            self._client.warmup()
        return self._client.is_available()

    def _resolve_target_tables(
        self, news_types: Optional[List[str]], year_month: Optional[str]
    ) -> List[str]:
        """
        根据 news_type / year_month 计算目标分表列表。
        - news_types 为空 → 默认所有 NEWS_TYPES
        - year_month 为空 → 通配所有月份
        最终通过 information_schema 校验真实存在的表。
        """
        types = news_types if news_types else list(NEWS_TYPES)
        types = [t.strip() for t in types if t and t.strip()]
        if not types:
            types = list(NEWS_TYPES)

        ym = (year_month or "").strip()

        conn = get_news_conn()
        try:
            with conn.cursor() as cur:
                tables: List[str] = []
                for nt in types:
                    pattern = f"news_{nt}_{ym}" if ym else f"news_{nt}_20%%"
                    cur.execute(
                        "SELECT TABLE_NAME FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME LIKE %s",
                        (NEWS_DB_NAME, pattern),
                    )
                    for row in cur.fetchall():
                        tname = row["TABLE_NAME"]
                        if tname not in tables:
                            tables.append(tname)
                return tables
        finally:
            conn.close()

    def _fetch_candidates(
        self, table_name: str, limit: int, force: bool
    ) -> List[Dict[str, Any]]:
        """
        从单张分表中拉取候选记录：
          - 必须已完成 LLM（ai_analyze_time IS NOT NULL）
          - 默认仅取 sentiment_confidence IS NULL；force=True 时取全部
          - 仅取 FinBERT 推理需要的字段
        """
        where_clauses = ["ai_analyze_time IS NOT NULL"]
        if not force:
            where_clauses.append("sentiment_confidence IS NULL")
        where_sql = " AND ".join(where_clauses)

        sql = (
            f"SELECT id, title, content, sentiment_confidence "
            f"FROM `{table_name}` "
            f"WHERE {where_sql} "
            f"ORDER BY id DESC "
            f"LIMIT %s"
        )
        conn = get_news_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (limit,))
                rows = cur.fetchall() or []
            return list(rows)
        except Exception as e:
            self.logger.error("[manual_finbert] 扫描表 %s 失败: %s", table_name, e)
            return []
        finally:
            conn.close()

    def _process_batch(
        self,
        table_name: str,
        valid_items: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """
        对一批候选执行 FinBERT 推理 + Redis 更新 + MySQL CASE 批量更新。

        Args:
            table_name:  分表名（同一批必须同表）
            valid_items: [{"id": int, "text": str}, ...]
        """
        stats = {"requested": len(valid_items), "ok": 0, "redis_updated": 0, "mysql_updated": 0}
        if not valid_items:
            return stats

        texts = [it["text"] for it in valid_items]
        results = _call_finbert_batch_with_retry(self._client, texts)

        if not results or len(results) != len(valid_items):
            self.logger.warning(
                "[manual_finbert] %s: FinBERT 返回不匹配（got=%d, need=%d）",
                table_name, len(results) if results else 0, len(valid_items),
            )
            return stats

        # 整理待持久化结构 + 同步更新 Redis
        persist_items: List[Dict[str, Any]] = []
        for it, raw in zip(valid_items, results):
            cleaned = _validate_single(raw or {})
            if not cleaned or "sentiment_confidence" not in cleaned:
                continue

            stats["ok"] += 1

            # 更新 Redis（若 key 不存在 news_data_update 会在内部判断）
            redis_payload = dict(cleaned)
            redis_payload["table_name"] = table_name
            try:
                if news_data_update(it["id"], redis_payload):
                    stats["redis_updated"] += 1
            except Exception as e:
                self.logger.debug(
                    "[manual_finbert] %s id=%d Redis 更新失败（忽略）: %s",
                    table_name, it["id"], e,
                )

            persist_items.append({
                "table_name": table_name,
                "news_id":    int(it["id"]),
                "result":     cleaned,
            })

        # MySQL CASE 批量 UPDATE（同一表内一次 SQL 完成）
        if persist_items:
            try:
                mysql_count = batch_update_ai_case(persist_items)
                stats["mysql_updated"] = mysql_count
            except Exception as e:
                self.logger.error(
                    "[manual_finbert] %s: batch_update_ai_case 异常: %s",
                    table_name, e,
                )

        return stats

    # ─────────────────────────────────────────────────────────────
    #  对外主入口（同步执行）
    # ─────────────────────────────────────────────────────────────

    def run_manual_batch(
        self,
        news_type: Optional[str] = None,
        year_month: Optional[str] = None,
        limit: int = 500,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        手动批量执行 FinBERT 分析（同步阻塞，结果直接返回）。

        Args:
            news_type:  逗号分隔的新闻类型；为空则扫描全部
            year_month: 月份字符串（如 202605）；为空则不限月份
            limit:     每张分表最多取多少条候选（1 <= limit <= 5000）
            force:     是否强制重算（True 时忽略 sentiment_confidence 已有值）

        Returns:
            {
                "success": True,
                "data": {
                    "tables_scanned": int,
                    "candidates":     int,
                    "analyzed":       int,
                    "redis_updated":  int,
                    "mysql_updated":  int,
                    "skip_empty_text": int,
                    "per_table": [{"table": str, "candidates": int, "ok": int, ...}, ...],
                    "started_at":  iso,
                    "finished_at": iso,
                    "elapsed_seconds": float
                }
            }
        """
        started = datetime.now()

        # 参数校验
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 500
        limit = max(1, min(_MAX_LIMIT_PER_TABLE, limit))

        types_list: Optional[List[str]] = None
        if news_type:
            types_list = [s.strip() for s in news_type.split(",") if s.strip()]

        # 模型可用性检查
        if not self._ensure_client():
            return self.wrap_error(
                "FinBERT 模型当前不可用（可能模型未下载或网络异常），"
                "请检查 news_services/utils/finbert_client.py 并稍后重试"
            )

        # 解析目标分表
        tables = self._resolve_target_tables(types_list, year_month)
        if not tables:
            return self.wrap_success(
                data={
                    "tables_scanned": 0,
                    "candidates":     0,
                    "analyzed":       0,
                    "redis_updated":  0,
                    "mysql_updated":  0,
                    "skip_empty_text": 0,
                    "per_table":      [],
                    "started_at":     started.isoformat(),
                    "finished_at":    datetime.now().isoformat(),
                    "elapsed_seconds": 0.0,
                },
                message="未匹配到任何新闻分表",
            )

        # 汇总统计
        total_candidates = 0
        total_analyzed = 0
        total_redis_updated = 0
        total_mysql_updated = 0
        total_skip_empty = 0
        per_table_stats: List[Dict[str, Any]] = []

        self.logger.info(
            "[manual_finbert] 启动 | tables=%d | year_month=%s | types=%s | limit=%d | force=%s",
            len(tables), year_month or "*", types_list or "*", limit, force,
        )

        for table_name in tables:
            rows = self._fetch_candidates(table_name, limit, force)
            if not rows:
                per_table_stats.append({
                    "table":         table_name,
                    "candidates":    0,
                    "analyzed":      0,
                    "redis_updated": 0,
                    "mysql_updated": 0,
                    "skip_empty":    0,
                })
                continue

            # 构建有效项（拼接 text）
            valid_items: List[Dict[str, Any]] = []
            skip_empty = 0
            for r in rows:
                title = (r.get("title") or "").strip()
                content = (r.get("content") or "").strip()
                text = (title + "。" + content).strip("。 ").strip()
                if not text:
                    skip_empty += 1
                    continue
                valid_items.append({"id": int(r["id"]), "text": text})

            table_candidates = len(rows)
            total_candidates += table_candidates
            total_skip_empty += skip_empty

            tbl_analyzed = 0
            tbl_redis = 0
            tbl_mysql = 0

            # 分批推理（与后台一致使用 FINBERT_BATCH_SIZE）
            for i in range(0, len(valid_items), FINBERT_BATCH_SIZE):
                batch = valid_items[i:i + FINBERT_BATCH_SIZE]
                stats = self._process_batch(table_name, batch)
                tbl_analyzed += stats["ok"]
                tbl_redis += stats["redis_updated"]
                tbl_mysql += stats["mysql_updated"]

            total_analyzed += tbl_analyzed
            total_redis_updated += tbl_redis
            total_mysql_updated += tbl_mysql

            per_table_stats.append({
                "table":         table_name,
                "candidates":    table_candidates,
                "analyzed":      tbl_analyzed,
                "redis_updated": tbl_redis,
                "mysql_updated": tbl_mysql,
                "skip_empty":    skip_empty,
            })

            self.logger.info(
                "[manual_finbert] %s 完成 | 候选:%d 分析:%d Redis:%d MySQL:%d 空文本跳过:%d",
                table_name, table_candidates, tbl_analyzed, tbl_redis, tbl_mysql, skip_empty,
            )

        finished = datetime.now()
        elapsed = (finished - started).total_seconds()

        self.logger.info(
            "[manual_finbert] 全部完成 | 表:%d 候选:%d 分析:%d Redis:%d MySQL:%d 耗时:%.1fs",
            len(tables), total_candidates, total_analyzed,
            total_redis_updated, total_mysql_updated, elapsed,
        )

        return self.wrap_success(
            data={
                "tables_scanned":  len(tables),
                "candidates":      total_candidates,
                "analyzed":        total_analyzed,
                "redis_updated":   total_redis_updated,
                "mysql_updated":   total_mysql_updated,
                "skip_empty_text": total_skip_empty,
                "per_table":       per_table_stats,
                "started_at":      started.isoformat(),
                "finished_at":     finished.isoformat(),
                "elapsed_seconds": round(elapsed, 2),
                "params": {
                    "news_type":  types_list,
                    "year_month": year_month,
                    "limit":      limit,
                    "force":      force,
                },
            },
            message=f"完成 {total_analyzed}/{total_candidates} 条 FinBERT 分析",
        )


# ═══════════════════════════════════════════════════════════════════
#  模块级单例
# ═══════════════════════════════════════════════════════════════════

news_finbert_manual_service = NewsFinbertManualService()


# ═══════════════════════════════════════════════════════════════════
#  定时批量调度（供 routes.py 的 start_scheduler 调用）
# ═══════════════════════════════════════════════════════════════════

_scheduler: Optional[BackgroundScheduler] = None
_scheduler_lock = threading.Lock()


def start_scheduled_batch() -> None:
    """
    启动 FinBERT 定时批量分析任务（每15分钟执行一次）。
    独立于 HTTP 接口，后台静默执行，结果只记日志。
    """
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None and _scheduler.running:
            logger.info("[finbert_scheduled] 定时任务已在运行，跳过")
            return

        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.add_job(
            func=_run_scheduled_job,
            trigger=CronTrigger(minute="*/15"),
            id="finbert_scheduled_batch",
            name="FinBERT 定时批量情感分析（每15分钟）",
            replace_existing=True,
            misfire_grace_time=120,
        )
        _scheduler.start()
        logger.info("[finbert_scheduled] 定时批量任务已启动（每15分钟）")


def stop_scheduled_batch() -> None:
    """停止定时批量任务"""
    global _scheduler
    with _scheduler_lock:
        if _scheduler is not None:
            try:
                _scheduler.shutdown(wait=False)
            except Exception:
                pass
            _scheduler = None
            logger.info("[finbert_scheduled] 定时批量任务已停止")


def _run_scheduled_job() -> None:
    """定时执行体：扫描所有类型，处理最近未完成 FinBERT 的数据"""
    started = datetime.now()
    logger.info("[finbert_scheduled] 开始执行...")
    try:
        result = news_finbert_manual_service.run_manual_batch(
            news_type=None,
            year_month=None,
            limit=500,
            force=False,
        )
        data = result.get("data", {})
        elapsed = (datetime.now() - started).total_seconds()
        logger.info(
            "[finbert_scheduled] 完成 | 表:%d 候选:%d 分析:%d Redis:%d MySQL:%d 耗时:%.1fs",
            data.get("tables_scanned", 0),
            data.get("candidates", 0),
            data.get("analyzed", 0),
            data.get("redis_updated", 0),
            data.get("mysql_updated", 0),
            elapsed,
        )
    except Exception as e:
        logger.error("[finbert_scheduled] 执行异常: %s", e)
