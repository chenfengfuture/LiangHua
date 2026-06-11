"""
news_services/services/news_fetch_service.py — 新闻数据查询服务

迁移自 api/news/fetch_routes.py，承担新闻数据读取的全部业务逻辑：
  - 当日数据从 Redis 读取，无数据时后台触发采集
  - 历史数据从 MySQL 分表读取
  - 多板块并行聚合

api/news/routes.py 仅做参数透传与响应组装，不再包含任何业务函数。
"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.news_models import get_table_name
from utils.db import get_news_conn
from utils.redis_client_compat import (
    NEWS_DATA_KEY_PREFIX,
    _get_client,
)

from news_services.services.base_news_service import BaseNewsService

logger = logging.getLogger("news_fetch_service")


# ═══════════════════════════════════════════════════════════════════
#  常量定义
# ═══════════════════════════════════════════════════════════════════

# 支持的新闻板块（顺序同时影响 fetch_all 并发请求的提交顺序）
NEWS_SECTIONS = ["company", "cls", "global", "report", "cctv"]

# 板块标识 → 中文名映射
SECTION_NAMES = {
    "company": "公司动态",
    "cls":     "财联社",
    "global":  "全球新闻",
    "report":  "研报",
    "cctv":    "新闻联播",
}


class NewsFetchService(BaseNewsService):
    """新闻数据查询服务（Redis + MySQL 双数据源）"""

    def __init__(self):
        super().__init__(service_name="NewsFetchService")
        # 并发采集锁：防止同一板块被重复触发
        self._collect_lock = threading.Lock()
        self._collecting_sections: set = set()

    # ─────────────────────────────────────────────────────────────
    #  日期解析工具
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _get_today_str() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    @staticmethod
    def _get_year_month(date_str: str) -> str:
        return date_str.replace("-", "")[:6]

    def _is_today(self, date_str: str) -> bool:
        return date_str == self._get_today_str()

    def _parse_date(self, date_str: Optional[str]) -> str:
        """
        解析前端传入的日期参数，支持 YYYY-MM-DD / YYYYMMDD / YYYY/MM/DD。
        失败或未传入时返回今天。
        """
        if not date_str:
            return self._get_today_str()
        for fmt in ["%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"]:
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return self._get_today_str()

    # ─────────────────────────────────────────────────────────────
    #  Redis 读取
    # ─────────────────────────────────────────────────────────────

    def _fetch_from_redis(self, section: str, date_str: str, limit: int = 500) -> List[Dict]:
        """
        从 Redis 扫描当日新闻数据。
          1. 根据 section + year_month 生成表名 → scan pattern
          2. SCAN 遍历 news:data:{table_name}:* 的所有 key
          3. 批量 GET，过滤 publish_time 以 date_str 开头的记录
          4. 按 publish_time 倒序返回
        """
        try:
            r = _get_client()
            if r is None:
                return []

            year_month = self._get_year_month(date_str)
            table_name = get_table_name(section, year_month)
            pattern = f"{NEWS_DATA_KEY_PREFIX}{table_name}:*"

            keys = []
            cursor = 0
            while len(keys) < limit * 2:
                cursor, batch = r.scan(cursor=cursor, match=pattern, count=1000)
                keys.extend(batch)
                if cursor == 0:
                    break

            if not keys:
                return []

            news_list = []
            for key in keys[:limit * 2]:
                try:
                    val = r.get(key)
                    if val:
                        data = json.loads(val)
                        publish_time = data.get("publish_time", "")
                        if publish_time and publish_time.startswith(date_str):
                            data["_source"] = "redis"
                            data["_table_name"] = table_name
                            news_list.append(data)
                except Exception:
                    continue

            news_list.sort(key=lambda x: x.get("publish_time", ""), reverse=True)
            return news_list[:limit]

        except Exception as e:
            self.log_exception(f"Redis 获取 {section}", e)
            return []

    # ─────────────────────────────────────────────────────────────
    #  MySQL 读取
    # ─────────────────────────────────────────────────────────────

    def _fetch_from_mysql(self, section: str, date_str: str, limit: int = 500) -> List[Dict]:
        """
        从 MySQL 对应分表读取历史新闻：
          1. 根据 section + year_month 生成表名
          2. 检查表是否存在（不存在返回空）
          3. 按 publish_time DESC 查询，is_deleted=0
        """
        try:
            year_month = self._get_year_month(date_str)
            table_name = get_table_name(section, year_month)

            conn = get_news_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) as cnt FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA = 'news_data' AND TABLE_NAME = %s",
                        (table_name,)
                    )
                    if cur.fetchone()["cnt"] == 0:
                        return []

                    cur.execute(
                        f"SELECT *, %s as `_table_name`, 'mysql' as `_source` "
                        f"FROM `{table_name}` "
                        f"WHERE DATE(publish_time) = %s AND is_deleted = 0 "
                        f"ORDER BY publish_time DESC LIMIT %s",
                        (table_name, date_str, limit)
                    )
                    rows = cur.fetchall()
                    return [dict(row) for row in rows]
            finally:
                conn.close()

        except Exception as e:
            self.log_exception(f"MySQL 获取 {section}", e)
            return []

    # ─────────────────────────────────────────────────────────────
    #  后台触发采集
    # ─────────────────────────────────────────────────────────────

    def _trigger_collect(self, section: str, date_str: str) -> bool:
        """
        后台触发指定板块的采集任务（仅限当日数据）。
        同一板块同时只允许一个后台采集线程。
        """
        if not self._is_today(date_str):
            return False

        with self._collect_lock:
            if section in self._collecting_sections:
                return False
            self._collecting_sections.add(section)

        def _do_collect():
            try:
                self.logger.info(f"[fetch] 触发 {section} 板块采集...")
                # 延迟导入避免循环
                from news_services.services.news_collect_service import news_collect_service
                news_collect_service.collect_section(section)
            except Exception as e:
                self.log_exception(f"采集 {section}", e)
            finally:
                with self._collect_lock:
                    self._collecting_sections.discard(section)

        t = threading.Thread(target=_do_collect, name=f"collect-{section}", daemon=True)
        t.start()
        return True

    # ─────────────────────────────────────────────────────────────
    #  核心路由逻辑
    # ─────────────────────────────────────────────────────────────

    def _fetch_news_data(
        self,
        section: str,
        date_str: str,
        limit: int = 500,
        auto_collect: bool = True,
    ) -> Dict[str, Any]:
        """
        获取指定板块、指定日期的新闻数据。
          当日 → 优先 Redis；Redis 无数据且 auto_collect=True 时触发后台采集
          历史 → 直接查询 MySQL
        """
        is_today = self._is_today(date_str)

        if is_today:
            data = self._fetch_from_redis(section, date_str, limit)
            if data:
                return {"data": data, "source": "redis", "is_collecting": False, "count": len(data)}

            if auto_collect:
                is_collecting = self._trigger_collect(section, date_str)
                return {"data": [], "source": "collect", "is_collecting": is_collecting, "count": 0}

            return {"data": [], "source": "redis", "is_collecting": False, "count": 0}

        else:
            data = self._fetch_from_mysql(section, date_str, limit)
            return {"data": data, "source": "mysql", "is_collecting": False, "count": len(data)}

    # ─────────────────────────────────────────────────────────────
    #  对外接口
    # ─────────────────────────────────────────────────────────────

    def fetch_single_section(
        self,
        section: str,
        date: Optional[str] = None,
        limit: int = 500,
        auto_collect: bool = True,
    ) -> Dict[str, Any]:
        """
        单板块新闻查询（供路由层调用，直接返回完整响应体）
        """
        if section not in NEWS_SECTIONS:
            return {
                "status": "error",
                "section": section,
                "section_name": "未知",
                "date": date or self._get_today_str(),
                "is_today": self._is_today(date or self._get_today_str()),
                "data_source": "none",
                "count": 0,
                "data": [],
                "message": f"不支持的板块: {section}，可用板块: {', '.join(NEWS_SECTIONS)}"
            }

        date_str = self._parse_date(date)
        is_today = self._is_today(date_str)
        result = self._fetch_news_data(section, date_str, limit, auto_collect)

        if result["is_collecting"]:
            status = "collecting"
            message = f"{SECTION_NAMES[section]} 板块数据采集中，请稍后刷新"
        elif result["count"] == 0:
            status = "empty"
            message = f"{SECTION_NAMES[section]} 板块暂无数据"
        else:
            status = "success"
            message = None

        return {
            "status": status,
            "section": section,
            "section_name": SECTION_NAMES[section],
            "date": date_str,
            "is_today": is_today,
            "data_source": result["source"],
            "count": result["count"],
            "data": result["data"],
            "message": message,
        }

    def fetch_all_sections(
        self,
        date: Optional[str] = None,
        sections: Optional[str] = None,
        limit: int = 500,
        auto_collect: bool = True,
    ) -> Dict[str, Any]:
        """
        多板块聚合查询（并行）。
        """
        date_str = self._parse_date(date)
        is_today = self._is_today(date_str)

        if sections:
            section_list = [s.strip() for s in sections.split(",") if s.strip() in NEWS_SECTIONS]
        else:
            section_list = NEWS_SECTIONS

        if not section_list:
            return {
                "status": "error",
                "date": date_str,
                "is_today": is_today,
                "sections": {},
                "total_count": 0,
                "message": "未指定有效的板块",
            }

        results: Dict[str, Dict[str, Any]] = {}
        total_count = 0
        any_collecting = False

        with ThreadPoolExecutor(max_workers=len(section_list)) as executor:
            future_to_section = {
                executor.submit(self._fetch_news_data, section, date_str, limit, auto_collect): section
                for section in section_list
            }

            for future in as_completed(future_to_section):
                section = future_to_section[future]
                try:
                    result = future.result()

                    if result["is_collecting"]:
                        status = "collecting"
                        message = f"{SECTION_NAMES[section]} 板块数据采集中"
                        any_collecting = True
                    elif result["count"] == 0:
                        status = "empty"
                        message = f"{SECTION_NAMES[section]} 板块暂无数据"
                    else:
                        status = "success"
                        message = None

                    results[section] = {
                        "status": status,
                        "section": section,
                        "section_name": SECTION_NAMES[section],
                        "date": date_str,
                        "is_today": is_today,
                        "data_source": result["source"],
                        "count": result["count"],
                        "data": result["data"],
                        "message": message,
                    }
                    total_count += result["count"]

                except Exception as e:
                    self.log_exception(f"获取 {section}", e)
                    results[section] = {
                        "status": "error",
                        "section": section,
                        "section_name": SECTION_NAMES[section],
                        "date": date_str,
                        "is_today": is_today,
                        "data_source": "none",
                        "count": 0,
                        "data": [],
                        "message": f"获取失败: {e}",
                    }

        overall_status = "collecting" if any_collecting else ("success" if total_count > 0 else "empty")

        return {
            "status": overall_status,
            "date": date_str,
            "is_today": is_today,
            "sections": results,
            "total_count": total_count,
            "message": "部分板块采集中，请稍后刷新" if any_collecting else None,
        }

    def get_fetch_status(self) -> Dict[str, Any]:
        """查询当前正在后台采集的板块列表。"""
        with self._collect_lock:
            collecting = list(self._collecting_sections)

        return {
            "status": "ok",
            "collecting_sections": collecting,
            "is_collecting": len(collecting) > 0,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


# ═══════════════════════════════════════════════════════════════════
#  模块级单例
# ═══════════════════════════════════════════════════════════════════

news_fetch_service = NewsFetchService()
