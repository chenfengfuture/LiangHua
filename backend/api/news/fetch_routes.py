"""
================================================================================
api/news/fetch_routes.py — 新闻数据查询接口
================================================================================

【模块职责】
  为前端提供统一的新闻数据读取接口，自动根据请求日期选择数据源：
    - 当日数据  → 优先从 Redis（news:data:{table_name}:{id}）读取
                  Redis 无数据时自动触发板块采集（后台执行）
    - 历史数据  → 直接查询 MySQL 对应分表（不触发采集）

【数据流向】
  ┌─────────────────┐     is_today?     ┌──────────────────┐
  │   前端 GET 请求  │ ─────────────────▶│  Redis SCAN 读取  │ → 有数据直接返回
  │  date 参数可选  │       YES         │ news:data:{tbl}:* │ → 无数据触发采集
  └─────────────────┘                   └──────────────────┘
           │
           │ NO (历史日期)
           ▼
    ┌──────────────────┐
    │  MySQL 分表查询  │ → 直接返回（不触发采集）
    │ news_{type}_YYYYMM│
    └──────────────────┘

【Redis Key 格式说明】
  新闻数据 Key：news:data:{table_name}:{id}
    例如：news:data:news_company_202604:1001
  扫描模式：  news:data:{table_name}:*

【REST 接口一览】
  GET /api/news/fetch               — 全量拉取（多板块并行聚合）
  GET /api/news/fetch/{section}     — 单板块独立获取
  GET /api/news/fetch/status        — 查看当前正在采集的板块列表

【支持的板块】
  company → 公司动态   cls → 财联社   global → 全球新闻
  report  → 研报       cctv → 新闻联播

【统一响应格式（所有接口一致）】
  单板块响应 NewsFetchResponse：
    status        → success / empty / collecting / error
    section       → 板块标识
    section_name  → 板块中文名
    date          → 查询日期
    is_today      → 是否当日数据
    data_source   → redis / mysql / collect / none
    count         → 返回数据条数
    data          → 新闻列表
    message       → 附加说明

【依赖关系】
  utils/redis_client.py   → Redis 扫描 + 批量读取
  models/news_models.py   → get_table_name() 表名生成
  utils/db.py             → MySQL 分表查询
  utils/akshare.py        → collect_section() 单板块采集触发
================================================================================
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from utils.redis_client import (
    _get_client,
    NEWS_DATA_KEY_PREFIX,
)
from models.news_models import get_table_name
from utils.db import get_news_conn
from utils.akshare import collect_section

router = APIRouter(prefix="/api/news", tags=["news-fetch"])


# ═══════════════════════════════════════════════════════════════════
#  常量定义
# ═══════════════════════════════════════════════════════════════════

# 支持的新闻板块（顺序同时影响 fetch_all 并发请求的提交顺序）
NEWS_SECTIONS = ["company", "cls", "global", "report", "cctv"]

# 板块标识 → 中文名映射（用于响应体中的 section_name 字段）
SECTION_NAMES = {
    "company": "公司动态",
    "cls":     "财联社",
    "global":  "全球新闻",
    "report":  "研报",
    "cctv":    "新闻联播",
}

# 并发采集锁：防止同一板块被重复触发（前端轮询时常见场景）
_collect_lock = threading.Lock()
_collecting_sections: set = set()  # 当前正在后台采集的板块集合


# ═══════════════════════════════════════════════════════════════════
#  响应数据模型
# ═══════════════════════════════════════════════════════════════════

class NewsFetchResponse(BaseModel):
    """单板块新闻查询统一响应格式"""
    status:       str                   = Field(...,  description="success/error/empty/collecting")
    section:      str                   = Field(...,  description="板块标识")
    section_name: str                   = Field(...,  description="板块中文名")
    date:         str                   = Field(...,  description="查询日期 YYYY-MM-DD")
    is_today:     bool                  = Field(...,  description="是否为当日数据")
    data_source:  str                   = Field(...,  description="数据来源: redis/mysql/collect/none")
    count:        int                   = Field(0,    description="返回数据条数")
    data:         List[Dict[str, Any]]  = Field(default_factory=list, description="新闻数据列表")
    message:      Optional[str]         = Field(None, description="附加信息（如采集中提示）")


class NewsFetchAllResponse(BaseModel):
    """全量多板块聚合查询统一响应格式"""
    status:      str                        = Field(...,  description="success/error/empty/collecting")
    date:        str                        = Field(...,  description="查询日期 YYYY-MM-DD")
    is_today:    bool                       = Field(...,  description="是否为当日数据")
    sections:    Dict[str, NewsFetchResponse] = Field(..., description="各板块响应数据，key 为板块标识")
    total_count: int                        = Field(0,    description="所有板块数据总条数")
    message:     Optional[str]              = Field(None, description="附加信息")


# ═══════════════════════════════════════════════════════════════════
#  内部工具函数
# ═══════════════════════════════════════════════════════════════════

def _get_today_str() -> str:
    """获取今天日期字符串（YYYY-MM-DD）"""
    return datetime.now().strftime("%Y-%m-%d")


def _get_year_month(date_str: str) -> str:
    """从日期字符串 YYYY-MM-DD 提取年月 YYYYMM（用于分表名）"""
    return date_str.replace("-", "")[:6]


def _is_today(date_str: str) -> bool:
    """判断给定日期是否为今天"""
    return date_str == _get_today_str()


def _parse_date(date_str: Optional[str]) -> str:
    """
    解析前端传入的日期参数，支持 YYYY-MM-DD / YYYYMMDD / YYYY/MM/DD 格式。
    解析失败或未传入时默认返回今天。
    """
    if not date_str:
        return _get_today_str()
    for fmt in ["%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return _get_today_str()


def _fetch_from_redis(section: str, date_str: str, limit: int = 500) -> List[Dict]:
    """
    从 Redis 扫描当日新闻数据。

    策略：
      1. 根据 section + year_month 生成 table_name，构造 scan pattern
      2. SCAN 遍历 news:data:{table_name}:* 的所有 key
      3. 批量 GET，过滤 publish_time 以 date_str 开头的记录
      4. 按 publish_time 倒序排序后返回

    Args:
        section:  板块标识（company/cls/global/report/cctv）
        date_str: 目标日期 YYYY-MM-DD
        limit:    返回上限条数

    Returns:
        符合条件的新闻列表，每条附加 _source="redis" 和 _table_name 字段
    """
    try:
        r = _get_client()
        if r is None:
            return []

        year_month = _get_year_month(date_str)
        table_name = get_table_name(section, year_month)
        pattern = f"{NEWS_DATA_KEY_PREFIX}{table_name}:*"

        # SCAN 遍历（一次多扫一些用于后续日期过滤）
        keys = []
        cursor = 0
        while len(keys) < limit * 2:
            cursor, batch = r.scan(cursor=cursor, match=pattern, count=1000)
            keys.extend(batch)
            if cursor == 0:
                break

        if not keys:
            return []

        # 批量读取并过滤
        news_list = []
        for key in keys[:limit * 2]:
            try:
                val = r.get(key)
                if val:
                    data = json.loads(val)
                    publish_time = data.get("publish_time", "")
                    # 只保留 publish_time 与目标日期匹配的记录
                    if publish_time and publish_time.startswith(date_str):
                        data["_source"] = "redis"
                        data["_table_name"] = table_name
                        news_list.append(data)
            except Exception:
                continue

        # 按发布时间倒序排列
        news_list.sort(key=lambda x: x.get("publish_time", ""), reverse=True)
        return news_list[:limit]

    except Exception as e:
        print(f"[fetch_routes] Redis 获取失败 section={section}: {e}")
        return []


def _fetch_from_mysql(section: str, date_str: str, limit: int = 500) -> List[Dict]:
    """
    从 MySQL 对应分表读取历史新闻数据。

    查询逻辑：
      1. 根据 section + year_month 生成表名（如 news_company_202604）
      2. 检查表是否存在（information_schema），不存在则返回空
      3. 按 publish_time DESC 查询，过滤 is_deleted=0 的记录

    Returns:
        新闻字典列表，每条附加 _source="mysql" 和 _table_name 字段
    """
    try:
        year_month = _get_year_month(date_str)
        table_name = get_table_name(section, year_month)

        conn = get_news_conn()
        try:
            with conn.cursor() as cur:
                # 先确认分表存在
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = 'news_data' AND TABLE_NAME = %s",
                    (table_name,)
                )
                if cur.fetchone()["cnt"] == 0:
                    return []

                # 按日期过滤查询
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
        print(f"[fetch_routes] MySQL 获取失败 section={section}: {e}")
        return []


def _trigger_collect(section: str, date_str: str) -> bool:
    """
    后台触发指定板块的采集任务（仅限当日数据，不阻塞接口返回）。

    并发保护：同一板块同时只允许一个采集后台线程，重复触发直接返回 False。

    Returns:
        True  → 成功触发（新启动了一个后台采集线程）
        False → 未触发（非当日 / 已在采集中）
    """
    if not _is_today(date_str):
        return False  # 历史数据不触发采集

    with _collect_lock:
        if section in _collecting_sections:
            return False  # 该板块已有采集任务正在执行
        _collecting_sections.add(section)

    def _do_collect():
        try:
            print(f"[fetch_routes] 触发 {section} 板块采集...")
            collect_section(section)
        except Exception as e:
            print(f"[fetch_routes] 采集失败 {section}: {e}")
        finally:
            with _collect_lock:
                _collecting_sections.discard(section)

    t = threading.Thread(target=_do_collect, name=f"collect-{section}", daemon=True)
    t.start()
    return True


def _fetch_news_data(
    section: str,
    date_str: str,
    limit: int = 500,
    auto_collect: bool = True
) -> Dict[str, Any]:
    """
    获取指定板块、指定日期的新闻数据（核心路由逻辑）。

    数据源选择策略：
      当日：优先 Redis → Redis 无数据时（auto_collect=True）触发后台采集
      历史：直接查询 MySQL

    Returns:
        {
            "data":         List[Dict],             # 新闻列表
            "source":       "redis"/"mysql"/"collect",
            "is_collecting": bool,                  # 是否刚触发了后台采集
            "count":        int
        }
    """
    is_today = _is_today(date_str)

    if is_today:
        # 当日：优先 Redis
        data = _fetch_from_redis(section, date_str, limit)
        if data:
            return {"data": data, "source": "redis", "is_collecting": False, "count": len(data)}

        # Redis 无数据，按需触发后台采集
        if auto_collect:
            is_collecting = _trigger_collect(section, date_str)
            return {"data": [], "source": "collect", "is_collecting": is_collecting, "count": 0}

        return {"data": [], "source": "redis", "is_collecting": False, "count": 0}

    else:
        # 历史：直接 MySQL
        data = _fetch_from_mysql(section, date_str, limit)
        return {"data": data, "source": "mysql", "is_collecting": False, "count": len(data)}


# ═══════════════════════════════════════════════════════════════════
#  REST 接口
# ═══════════════════════════════════════════════════════════════════

@router.get("/fetch/{section}", response_model=NewsFetchResponse)
def fetch_single_section(
    section: str,
    date: Optional[str] = Query(None, description="日期，格式 YYYY-MM-DD，默认今天"),
    limit: int = Query(500, ge=1, le=1000, description="返回条数限制（1-1000）"),
    auto_collect: bool = Query(True, description="当日无数据时是否自动触发采集"),
):
    """
    单板块新闻查询接口。

    GET /api/news/fetch/{section}

    **路径参数：**
    - section: 板块标识（company / cls / global / report / cctv）

    **查询参数：**
    - date:         日期 YYYY-MM-DD，默认今天
    - limit:        返回条数限制 1~1000，默认 500
    - auto_collect: 当日无数据时是否后台触发采集，默认 True

    **当日数据** → 从 Redis 读取，无数据且 auto_collect=True 时触发采集并返回 status=collecting
    **历史数据** → 从 MySQL 分表读取，不触发采集
    """
    # 验证板块合法性
    if section not in NEWS_SECTIONS:
        return NewsFetchResponse(
            status="error",
            section=section,
            section_name="未知",
            date=date or _get_today_str(),
            is_today=_is_today(date or _get_today_str()),
            data_source="none",
            count=0,
            data=[],
            message=f"不支持的板块: {section}，可用板块: {', '.join(NEWS_SECTIONS)}"
        )

    date_str = _parse_date(date)
    is_today = _is_today(date_str)
    result = _fetch_news_data(section, date_str, limit, auto_collect)

    # 根据结果确定 status 和 message
    if result["is_collecting"]:
        status = "collecting"
        message = f"{SECTION_NAMES[section]} 板块数据采集中，请稍后刷新"
    elif result["count"] == 0:
        status = "empty"
        message = f"{SECTION_NAMES[section]} 板块暂无数据"
    else:
        status = "success"
        message = None

    return NewsFetchResponse(
        status=status,
        section=section,
        section_name=SECTION_NAMES[section],
        date=date_str,
        is_today=is_today,
        data_source=result["source"],
        count=result["count"],
        data=result["data"],
        message=message,
    )


@router.get("/fetch", response_model=NewsFetchAllResponse)
def fetch_all_sections(
    date: Optional[str] = Query(None, description="日期，格式 YYYY-MM-DD，默认今天"),
    sections: Optional[str] = Query(None, description="板块列表，逗号分隔，默认全部"),
    limit: int = Query(500, ge=1, le=1000, description="每板块返回条数限制"),
    auto_collect: bool = Query(True, description="当日无数据时是否自动触发采集"),
):
    """
    多板块聚合查询接口（并行拉取所有板块数据）。

    GET /api/news/fetch

    **查询参数：**
    - date:         日期 YYYY-MM-DD，默认今天
    - sections:     板块列表，逗号分隔（如 company,cls,global），默认全部5个板块
    - limit:        每板块返回条数限制 1~1000，默认 500
    - auto_collect: 当日无数据时是否后台触发采集，默认 True

    **示例：**
    ```
    GET /api/news/fetch                                   # 今日全部板块
    GET /api/news/fetch?date=2026-04-07                   # 历史某天全部板块
    GET /api/news/fetch?sections=company,cls&limit=100    # 指定板块
    ```
    """
    date_str = _parse_date(date)
    is_today = _is_today(date_str)

    # 解析并验证板块列表
    if sections:
        section_list = [s.strip() for s in sections.split(",") if s.strip() in NEWS_SECTIONS]
    else:
        section_list = NEWS_SECTIONS

    if not section_list:
        return NewsFetchAllResponse(
            status="error",
            date=date_str,
            is_today=is_today,
            sections={},
            total_count=0,
            message="未指定有效的板块"
        )

    # 并行获取各板块（每个板块一个 Future）
    results: Dict[str, NewsFetchResponse] = {}
    total_count = 0
    any_collecting = False

    with ThreadPoolExecutor(max_workers=len(section_list)) as executor:
        future_to_section = {
            executor.submit(_fetch_news_data, section, date_str, limit, auto_collect): section
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

                results[section] = NewsFetchResponse(
                    status=status,
                    section=section,
                    section_name=SECTION_NAMES[section],
                    date=date_str,
                    is_today=is_today,
                    data_source=result["source"],
                    count=result["count"],
                    data=result["data"],
                    message=message,
                )
                total_count += result["count"]

            except Exception as e:
                print(f"[fetch_routes] 获取 {section} 失败: {e}")
                results[section] = NewsFetchResponse(
                    status="error",
                    section=section,
                    section_name=SECTION_NAMES[section],
                    date=date_str,
                    is_today=is_today,
                    data_source="none",
                    count=0,
                    data=[],
                    message=f"获取失败: {e}",
                )

    overall_status = "collecting" if any_collecting else ("success" if total_count > 0 else "empty")

    return NewsFetchAllResponse(
        status=overall_status,
        date=date_str,
        is_today=is_today,
        sections=results,
        total_count=total_count,
        message="部分板块采集中，请稍后刷新" if any_collecting else None,
    )


@router.get("/fetch/status")
def fetch_status():
    """
    查询当前正在后台采集的板块列表。

    GET /api/news/fetch/status

    前端可通过此接口判断是否需要继续轮询等待数据。
    """
    with _collect_lock:
        collecting = list(_collecting_sections)

    return {
        "status": "ok",
        "collecting_sections": collecting,
        "is_collecting": len(collecting) > 0,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
