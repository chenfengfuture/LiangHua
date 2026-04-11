"""
utils/akshare.py — 5 大新闻板块采集核心（终极 Redis 三层架构）

基于 AkShare + 直接 API 调用的多源新闻采集器。

5 大板块：
  company — 个股/公司新闻（东方财富 stock_news_em），每小时增量
  cls     — 财联社新闻（财联社 API），实时增量
  global  — 全球新闻（东方财富 API），15 分钟一次
  cctv    — 新闻联播（akshare news_cctv），一天一次，19:30 后
  report  — 研报新闻（东方财富 API），当天深度研报，自动分页200条/次

架构（终极 Redis 三层架构）：
  采集层（4线程）：
    AkShare获取 → 清洗 → 写入MySQL（获取自增id）→ 封装完整JSON写入 news:data:{id}
    → 将 id 推入 news:pending_llm Set（供 LLM 8线程消费）
    → WebSocket 推送原始新闻到前端

  Redis 三层结构：
    Layer 1: news:data:{id}      → Redis String，完整新闻 JSON（永久）
    Layer 2: news:pending_llm    → Redis Set，待 LLM 分析的 id（SPOP 无竞争）
    Layer 3: news:pending_persist→ Redis List，已分析待持久化的 id

采集规则：
  - 所有板块从 Redis 获取上次采集时间，按【上次时间 +1秒】开始增量采集
  - report 只拉当天深度研报，自动分页200条/次
  - 所有时间格式统一 "%Y-%m-%d %H:%M:%S"
  - 全部采集使用多线程并行执行，互不阻塞、互不影响
  - 异常捕获：采集失败、Redis 失败、时间解析失败 → 只打日志，不崩溃
"""

import re
import time
import threading
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict
from concurrent.futures import ThreadPoolExecutor

import requests

from utils.websocket_manager import ws_manager
from utils.redis_client import (
    get_last_collect_time,
    set_last_collect_time,
    seconds_since_last_collect,
    is_cctv_today_done,
    set_cctv_today_done,
    reset_cctv_today_done,
    # 新三层 Redis 架构
    news_data_set,
    pending_llm_add_batch,
)
from models.news_models import (
    insert_news,
    insert_news_return_ids,
    insert_news_with_content_hash,
    ensure_table_exists,
    get_table_name,
    sanitize_text,
)

# 默认关注的个股代码
DEFAULT_SYMBOLS = ["300059", "600519", "300750", "600030", "688981"]

# 统一时间格式
TIME_FMT = "%Y-%m-%d %H:%M:%S"


# ═══════════════════════════════════════════════════════════════════
#  新闻敏感性分析（入库前清洗）
# ═══════════════════════════════════════════════════════════════════

def _need_llm_analyze(title: str, content: str, news_type: str) -> int:
    """
    新闻敏感性判断：决定是否需要 LLM 分析。

    Returns:
        0 = 敏感/高风险（不进 LLM），1 = 正常财经（进 LLM）
    """
    text = (str(title) + str(content)).lower()

    sensitive_words = {
        "政治", "战争", "制裁", "外交", "国家领导人", "示威", "暴乱", "恐怖",
        "疫情", "死亡", "极端", "反动", "台独", "港独", "敏感",
    }

    high_risk_words = {
        "立案", "调查", "处罚", "退市", "破产", "违法", "违规", "造假", "欺诈",
        "强制措施", "风险警示", "内幕交易", "操纵市场",
    }

    if news_type == "cctv":
        return 0

    for w in sensitive_words:
        if w in text:
            return 0
    for w in high_risk_words:
        if w in text:
            return 0

    return 1


def _filter_cctv_policy(title: str, content: str) -> tuple:
    """
    CCTV 新闻二次过滤：判断是否为可解读的产业政策。

    Returns:
        (need_analyze: int, skip_reason: str)
    """
    text = f"{title} {content}".lower()

    policy_whitelist = {
        "新能源", "半导体", "芯片", "高端制造", "生物医药", "创新药",
        "消费", "家电", "汽车", "基建", "新基建", "降准", "降息",
        "乡村振兴", "养老", "医疗", "教育", "数字经济", "人工智能",
        "光伏", "储能", "风电", "新能源车", "国产替代",
    }

    political_blacklist = {
        "中央", "国务院", "领导人", "会议", "讲话", "外交", "国防",
        "国家安全", "意识形态", "宣传", "党建", "反腐",
    }

    for word in political_blacklist:
        if word in text:
            return 0, "CCTV政治通稿，不做板块解读"

    for word in policy_whitelist:
        if word in text:
            return 1, "可解读产业政策"

    return 0, "无明确产业利好，不做解读"


def _clean_news_rows(rows: list) -> list:
    """
    批量清洗新闻数据：设置 need_analyze 字段 + 安全清洗文本。
    """
    text_fields = ("title", "content", "url", "source", "source_category")
    cleaned = []
    for row in rows:
        title = row.get("title", "")
        content = row.get("content", "")
        news_type = row.get("news_type", "")

        for field in text_fields:
            if field in row:
                row[field] = sanitize_text(row[field])

        title = row.get("title") or ""
        content = row.get("content") or ""

        if news_type == "cctv":
            need, reason = _filter_cctv_policy(title, content)
            row["need_analyze"] = need
            row["_skip_reason"] = reason
        else:
            row["need_analyze"] = _need_llm_analyze(title, content, news_type)

        cleaned.append(row)
    return cleaned


# ═══════════════════════════════════════════════════════════════════
#  时间解析工具
# ═══════════════════════════════════════════════════════════════════

def _parse_datetime(raw: str, fallback_hour: int = 0) -> Optional[datetime]:
    """解析各种日期/时间字符串为 datetime。"""
    if not raw or raw in ("None", "nan", "NaT", ""):
        return None

    raw = raw.strip()

    if re.match(r"^\d{14}$", raw):
        try:
            return datetime(
                int(raw[:4]), int(raw[4:6]), int(raw[6:8]),
                int(raw[8:10]), int(raw[10:12]), int(raw[12:14]),
            )
        except ValueError:
            return None

    if re.match(r"^\d{8}$", raw):
        try:
            return datetime(
                int(raw[:4]), int(raw[4:6]), int(raw[6:8]),
                fallback_hour, 0, 0,
            )
        except ValueError:
            return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y.%m.%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.replace(hour=fallback_hour, minute=0, second=0)
        except ValueError:
            continue

    print(f"[akshare] 时间解析失败: '{raw}'")
    return None


def _extract_date_from_url(url: str, target_date: date) -> Optional[datetime]:
    """从 URL 中提取日期。"""
    if not url:
        return None
    match = re.search(r"(\d{4}-\d{2}-\d{2})", url)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    return datetime.combine(target_date, datetime.min.time())


# ═══════════════════════════════════════════════════════════════════
#  Redis 增量时间计算
# ═══════════════════════════════════════════════════════════════════

def _get_incremental_range(news_type: str) -> tuple:
    """
    根据 Redis 中上次采集时间计算增量采集的时间范围。

    兜底规则（Redis 无有效记录时自动触发）：
      - company/cls/report → 当天 00:00:00
      - global              → 当前时间 -24 小时
      - cctv                → 由 _fetch_cctv 内部独立控制
    """
    now = datetime.now()
    last_str = get_last_collect_time(news_type)

    if last_str:
        try:
            last_dt = datetime.strptime(last_str, TIME_FMT)
            start_time = last_dt + timedelta(seconds=1)
            return start_time, now
        except ValueError:
            print(f"[akshare] {news_type} Redis 时间解析失败: {last_str}，进入兜底")

    # 兜底逻辑
    if news_type == "global":
        start_time = now - timedelta(hours=24)
        print(f"[akshare] {news_type} 初始化兜底 → 从 {start_time.strftime(TIME_FMT)} 开始（-24h）")
    else:
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        print(f"[akshare] {news_type} 初始化兜底 → 从 {start_time.strftime(TIME_FMT)} 开始（当天 00:00:00）")

    return start_time, now


# ═══════════════════════════════════════════════════════════════════
#  5 大板块采集函数
# ═══════════════════════════════════════════════════════════════════

def _fetch_company(start_time: datetime, end_time: datetime) -> List[dict]:
    """
    线程A：个股/公司新闻采集（AkShare stock_news_em）。
    """
    import akshare as ak

    symbols = DEFAULT_SYMBOLS
    all_rows = []
    seen_titles = set()

    start_str = start_time.strftime(TIME_FMT)
    end_str = end_time.strftime(TIME_FMT)
    print(f"[company] 增量采集 {start_str} ~ {end_str}")

    for symbol in symbols:
        try:
            df = ak.stock_news_em(symbol=symbol)
            if df is None or df.empty:
                continue

            for _, row in df.iterrows():
                title = str(row.get("新闻标题", "")).strip()
                if not title or title in seen_titles:
                    continue

                pub_time = _parse_datetime(str(row.get("发布时间", "")))
                if pub_time is None:
                    continue

                if pub_time < start_time:
                    continue

                seen_titles.add(title)
                all_rows.append({
                    "title": title,
                    "content": str(row.get("新闻内容", "")).strip(),
                    "url": str(row.get("新闻链接", "")).strip() or None,
                    "source": str(row.get("文章来源", "东方财富")).strip(),
                    "source_category": "东方财富",
                    "news_type": "company",
                    "publish_time": pub_time,
                })
        except Exception as e:
            print(f"[company] {symbol} 采集失败: {e}")

    return all_rows


def _fetch_cls(start_time: datetime, end_time: datetime) -> List[dict]:
    """
    线程B：财联社新闻采集（AkShare stock_info_global_cls）。
    """
    import akshare as ak

    start_str = start_time.strftime(TIME_FMT)
    end_str = end_time.strftime(TIME_FMT)
    print(f"[AkShare] 开始采集新闻 板块=cls")
    print(f"[cls] 增量采集 {start_str} ~ {end_str}")

    all_rows = []
    seen_titles = set()

    # 重试一次机制
    for attempt in range(2):
        try:
            df = ak.stock_info_global_cls()
            break
        except Exception as e:
            if attempt == 0:
                print(f"[AkShare] 采集失败 cls，重试中: {e}")
                time.sleep(1)
            else:
                print(f"[AkShare] 采集失败 cls（重试后）: {e}")
                return []
    else:
        return []

    if df is None or df.empty:
        print(f"[AkShare] 采集成功 条数=0")
        return []

    for _, row in df.iterrows():
        title = str(row.get("标题", "")).strip()
        if not title or title in seen_titles:
            continue
        content = str(row.get("内容", "")).strip()
        
        # 获取发布日期和发布时间，合并为完整时间字符串
        date_str = str(row.get("发布日期", "")).strip()
        time_str = str(row.get("发布时间", "")).strip()
        
        # 合并日期和时间
        if date_str and time_str:
            pub_time_str = f"{date_str} {time_str}"
        elif date_str:
            pub_time_str = f"{date_str} 00:00:00"
        elif time_str:
            # 只有时间部分，使用今天日期
            today = datetime.now().strftime("%Y-%m-%d")
            pub_time_str = f"{today} {time_str}"
        else:
            pub_time_str = ""
        
        pub_time = _parse_datetime(pub_time_str)
        if pub_time is None:
            continue
        if pub_time < start_time or pub_time > end_time:
            continue

        seen_titles.add(title)
        all_rows.append({
            "title": title,
            "content": content,
            "url": None,
            "source": "财联社",
            "source_category": "财联社",
            "news_type": "cls",
            "publish_time": pub_time,
        })

    print(f"[AkShare] 采集成功 条数={len(all_rows)}")
    print(f"[AkShare] 字段映射完成")
    print(f"[AkShare] 数据格式化完成")
    return all_rows


def _fetch_global(start_time: datetime, end_time: datetime) -> List[dict]:
    """
    线程C：全球新闻采集（AkShare stock_info_global_ths）。
    """
    import akshare as ak

    start_str = start_time.strftime(TIME_FMT)
    end_str = end_time.strftime(TIME_FMT)
    print(f"[AkShare] 开始采集新闻 板块=global")
    print(f"[global] 增量采集 {start_str} ~ {end_str}")

    all_rows = []
    seen_titles = set()

    # 重试一次机制
    for attempt in range(2):
        try:
            df = ak.stock_info_global_ths()
            break
        except Exception as e:
            if attempt == 0:
                print(f"[AkShare] 采集失败 global，重试中: {e}")
                time.sleep(1)
            else:
                print(f"[AkShare] 采集失败 global（重试后）: {e}")
                return []
    else:
        return []

    if df is None or df.empty:
        print(f"[AkShare] 采集成功 条数=0")
        return []

    for _, row in df.iterrows():
        title = str(row.get("标题", "")).strip()
        if not title or title in seen_titles:
            continue
        content = str(row.get("内容", "")).strip()
        pub_time_str = str(row.get("发布时间", ""))
        pub_time = _parse_datetime(pub_time_str)
        if pub_time is None:
            continue
        if pub_time < start_time or pub_time > end_time:
            continue

        seen_titles.add(title)
        all_rows.append({
            "title": title,
            "content": content,
            "url": None,
            "source": "东方财富",
            "source_category": "东方财富全球",
            "news_type": "global",
            "publish_time": pub_time,
        })

    print(f"[AkShare] 采集成功 条数={len(all_rows)}")
    print(f"[AkShare] 字段映射完成")
    print(f"[AkShare] 数据格式化完成")
    return all_rows


def _fetch_cctv(start_time: datetime, end_time: datetime) -> List[dict]:
    """
    线程D：CCTV 新闻联播采集（AkShare news_cctv）。
    一天一次，19:30 后执行。
    """
    now = datetime.now()

    cutoff = now.replace(hour=19, minute=30, second=0, microsecond=0)
    if now < cutoff:
        print(f"[cctv] 跳过: 当前时间 {now.strftime('%H:%M:%S')}，需 19:30 后")
        return []

    if is_cctv_today_done():
        print("[cctv] 跳过: 今日已采集完成")
        return []

    last_cctv_time_str = get_last_collect_time("cctv")
    if last_cctv_time_str:
        try:
            last_cctv_dt = datetime.strptime(last_cctv_time_str, TIME_FMT)
            if last_cctv_dt.date() < date.today():
                reset_cctv_today_done()
                print("[cctv] 检测到跨日，已重置 cctv_today_done 标记")
        except ValueError:
            reset_cctv_today_done()
            print("[cctv] 上次采集时间格式异常，已重置 cctv_today_done 标记")
    else:
        reset_cctv_today_done()
        print("[cctv] Redis 无采集记录，已标记今日未采集")

    import akshare as ak

    today_str = date.today().strftime("%Y%m%d")
    print(f"[cctv] 开始采集新闻联播 ({today_str})...")

    try:
        df = ak.news_cctv(date=today_str)
    except Exception as e:
        print(f"[cctv] 获取失败: {e}")
        return []

    if df is None or df.empty:
        print(f"[cctv] 无数据 ({today_str})")
        return []

    rows = []
    for _, row in df.iterrows():
        title = str(row.get("title", "")).strip()
        if not title:
            continue

        raw_date = str(row.get("date", ""))
        pub_time = _parse_datetime(raw_date, fallback_hour=19)
        if pub_time is None:
            continue

        rows.append({
            "title": title,
            "content": str(row.get("content", "")).strip(),
            "url": None,
            "source": "新闻联播",
            "source_category": "新闻联播",
            "news_type": "cctv",
            "publish_time": pub_time,
        })

    if rows:
        set_cctv_today_done()
        print(f"[cctv] 采集完成 {len(rows)} 条，已标记今日完成")

    return rows


def _fetch_report(start_time: datetime, end_time: datetime) -> List[dict]:
    """
    线程E：研报新闻采集（AkShare stock_research_report_em）。
    """
    import akshare as ak

    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    print(f"[AkShare] 开始采集新闻 板块=report")
    print(f"[report] 深度研报采集 | 当天: {today_str}")

    all_rows = []
    seen_titles = set()

    # 重试一次机制
    for attempt in range(2):
        try:
            df = ak.stock_research_report_em()
            break
        except Exception as e:
            if attempt == 0:
                print(f"[AkShare] 采集失败 report，重试中: {e}")
                time.sleep(1)
            else:
                print(f"[AkShare] 采集失败 report（重试后）: {e}")
                return []
    else:
        return []

    if df is None or df.empty:
        print(f"[AkShare] 采集成功 条数=0")
        return []

    for _, row in df.iterrows():
        report_name = str(row.get("报告名称", "")).strip()
        if not report_name or report_name in seen_titles:
            continue
        org = str(row.get("机构", "")).strip()
        rating = str(row.get("东财评级", "")).strip()
        industry = str(row.get("行业", "")).strip()
        # 构建内容字符串
        content = f"[{org}] 评级:{rating} 行业:{industry}"
        pub_time_str = str(row.get("日期", ""))
        pub_time = _parse_datetime(pub_time_str, fallback_hour=8)
        if pub_time is None:
            continue
        # 只保留当天发布的研报
        if pub_time.date() != today:
            continue
        # 二次确认：publish_time >= 今天 00:00
        today_start = datetime(today.year, today.month, today.day, 0, 0, 0)
        if pub_time < today_start:
            continue

        seen_titles.add(report_name)
        all_rows.append({
            "title": report_name,
            "content": content,
            "url": None,
            "source": "东方财富",
            "source_category": "东方财富研报",
            "news_type": "report",
            "publish_time": pub_time,
        })

    print(f"[AkShare] 采集成功 条数={len(all_rows)}")
    print(f"[AkShare] 字段映射完成")
    print(f"[AkShare] 数据格式化完成")
    return all_rows


# ═══════════════════════════════════════════════════════════════════
#  新三层 Redis 架构：采集入库后写 Redis + 推入 pending_llm
# ═══════════════════════════════════════════════════════════════════

def _push_news_to_redis_v2(news_type: str, year_month: str, rows: list) -> int:
    """
    新版采集入库函数：基于content_hash的去重逻辑（严格按照新要求实现）。
    
    流程：
      1. 对每条新闻计算 content_hash = md5(title + content)
      2. 调用 insert_news_with_content_hash：去重 → 唯一 → 写入 → 获取id
      3. 重复新闻：不写入MySQL，不写入Redis，直接丢弃
      4. 唯一新闻：写入MySQL，获取id → 写入Redis news:data:{id} → 推入news:pending_llm
    
    Args:
        news_type:  新闻类型（company/cls/global/cctv/report）
        year_month: 月份字符串（如 202604）
        rows:       已清洗的新闻字典列表（含 need_analyze 字段）
    
    Returns:
        成功写入 Redis 的唯一新闻数量
    """
    if not rows:
        return 0

    try:
        # Step 1: 调用新的去重插入函数
        inserted_records = insert_news_with_content_hash(news_type, year_month, rows)
        if not inserted_records:
            print(f"[redis_push_v2] {news_type} 无有效入库记录（可能全部重复）")
            return 0

        pending_ids = []
        written = 0

        for record in inserted_records:
            news_id = record.get("id")
            if not news_id:
                continue

            # Step 2: 写入 news:data:{id}（Redis String，完整 JSON）
            redis_data = {
                **record,
                "table_name": get_table_name(news_type, year_month),
                "news_type": record.get("news_type", news_type),
            }
            # datetime 转字符串（JSON 序列化）
            if isinstance(redis_data.get("publish_time"), datetime):
                redis_data["publish_time"] = redis_data["publish_time"].strftime(TIME_FMT)
            if isinstance(redis_data.get("collect_time"), datetime):
                redis_data["collect_time"] = str(redis_data["collect_time"])

            if news_data_set(news_id, redis_data):
                written += 1
                # Step 3: 需要 LLM 分析的才推入 pending_llm
                if record.get("need_analyze", 1) == 1:
                    pending_ids.append(news_id)

        # 批量推入 news:pending_llm（Redis Set）
        if pending_ids:
            # 构建 table_names 列表（与 pending_ids 一一对应）
            table_names = [get_table_name(news_type, year_month)] * len(pending_ids)
            pushed = pending_llm_add_batch(pending_ids, table_names)
            print(f"[redis_push_v2] {news_type} → 去重后唯一新闻:{written} | news:data 写入:{written} | news:pending_llm 推入:{pushed}")
        else:
            print(f"[redis_push_v2] {news_type} → 去重后唯一新闻:{written} | news:data 写入:{written} | 无待分析新闻")

        return written

    except Exception as e:
        print(f"[redis_push_v2] {news_type} _push_news_to_redis_v2 异常: {e}")
        return 0


# ═══════════════════════════════════════════════════════════════════
#  板块调度：频率控制 + 增量采集 + 入库 + 入Redis队列
# ═══════════════════════════════════════════════════════════════════

def _collect_company() -> int:
    """个股/公司新闻：采集 → 清洗 → 入库+写Redis → WS推送"""
    try:
        # 频率控制：每小时最多一次
        elapsed = seconds_since_last_collect("company")
        if elapsed is not None and elapsed < 3600:
            print(f"[company] 跳过: 距上次采集 {elapsed:.0f}s < 3600s (1小时)")
            return 0
        
        start_time, end_time = _get_incremental_range("company")
        rows = _fetch_company(start_time, end_time)
        if not rows:
            print("[company] 无增量数据")
            return 0
        rows = _clean_news_rows(rows)
        for row in rows:
            row.pop("_skip_reason", None)
        year_month = date.today().strftime("%Y%m")
        ensure_table_exists("company", year_month)
        count = _push_news_to_redis_v2("company", year_month, rows)
        set_last_collect_time("company")
        print(f"[company] 完成 | 拉取:{len(rows)} Redis写入:{count}")
        if count > 0:
            _push_news_to_ws("company", rows)
        return count
    except Exception as e:
        print(f"[company] 采集异常: {e}")
        return 0


def _collect_cls() -> int:
    """财联社新闻：采集 → 清洗 → 入库+写Redis → WS推送"""
    try:
        # 频率控制：每小时最多一次
        elapsed = seconds_since_last_collect("cls")
        if elapsed is not None and elapsed < 3600:
            print(f"[cls] 跳过: 距上次采集 {elapsed:.0f}s < 3600s (1小时)")
            return 0
        
        start_time, end_time = _get_incremental_range("cls")
        rows = _fetch_cls(start_time, end_time)
        if not rows:
            print("[cls] 无增量数据")
            return 0
        rows = _clean_news_rows(rows)
        for row in rows:
            row.pop("_skip_reason", None)
        year_month = date.today().strftime("%Y%m")
        ensure_table_exists("cls", year_month)
        count = _push_news_to_redis_v2("cls", year_month, rows)
        set_last_collect_time("cls")
        print(f"[cls] 完成 | 拉取:{len(rows)} Redis写入:{count}")
        if count > 0:
            _push_news_to_ws("cls", rows)
        return count
    except Exception as e:
        print(f"[cls] 采集异常: {e}")
        return 0


def _collect_global() -> int:
    """全球新闻：15分钟频率控制 → 采集 → 清洗 → 入库+写Redis → WS推送"""
    try:
        elapsed = seconds_since_last_collect("global")
        if elapsed is not None and elapsed < 900:
            print(f"[global] 跳过: 距上次采集 {elapsed:.0f}s < 900s (15分钟)")
            return 0

        start_time, end_time = _get_incremental_range("global")
        rows = _fetch_global(start_time, end_time)
        if not rows:
            print("[global] 无增量数据")
            set_last_collect_time("global")
            return 0
        rows = _clean_news_rows(rows)
        for row in rows:
            row.pop("_skip_reason", None)
        year_month = date.today().strftime("%Y%m")
        ensure_table_exists("global", year_month)
        count = _push_news_to_redis_v2("global", year_month, rows)
        set_last_collect_time("global")
        print(f"[global] 完成 | 拉取:{len(rows)} Redis写入:{count}")
        if count > 0:
            _push_news_to_ws("global", rows)
        return count
    except Exception as e:
        print(f"[global] 采集异常: {e}")
        return 0


def _collect_cctv() -> int:
    """CCTV 新闻联播：19:30后 → 采集 → 清洗 → 入库+写Redis → WS推送"""
    try:
        start_time, end_time = _get_incremental_range("cctv")
        rows = _fetch_cctv(start_time, end_time)
        if not rows:
            return 0
        rows = _clean_news_rows(rows)
        for row in rows:
            row.pop("_skip_reason", None)
        year_month = date.today().strftime("%Y%m")
        ensure_table_exists("cctv", year_month)
        count = _push_news_to_redis_v2("cctv", year_month, rows)
        set_last_collect_time("cctv")
        print(f"[cctv] 完成 | 拉取:{len(rows)} Redis写入:{count}")
        if count > 0:
            _push_news_to_ws("cctv", rows)
            # CCTV need_analyze=0，不进入 LLM 分析（已在 _push_news_to_redis 内部过滤）
        return count
    except Exception as e:
        print(f"[cctv] 采集异常: {e}")
        return 0


def _collect_report() -> int:
    """研报新闻：当天深度研报 → 采集 → 清洗 → 入库+写Redis → WS推送"""
    try:
        # 频率控制：每天最多一次
        elapsed = seconds_since_last_collect("report")
        if elapsed is not None and elapsed < 86400:
            print(f"[report] 跳过: 距上次采集 {elapsed:.0f}s < 86400s (24小时)")
            return 0
        
        start_time, end_time = _get_incremental_range("report")
        rows = _fetch_report(start_time, end_time)
        if not rows:
            print("[report] 无增量数据")
            set_last_collect_time("report")
            return 0
        rows = _clean_news_rows(rows)
        for row in rows:
            row.pop("_skip_reason", None)
        year_month = date.today().strftime("%Y%m")
        ensure_table_exists("report", year_month)
        count = _push_news_to_redis_v2("report", year_month, rows)
        set_last_collect_time("report")
        print(f"[report] 完成 | 拉取:{len(rows)} Redis写入:{count}")
        if count > 0:
            _push_news_to_ws("report", rows)
        return count
    except Exception as e:
        print(f"[report] 采集异常: {e}")
        return 0


def _collect_daily() -> int:
    """
    每日新闻采集：从 api.cjiot.cc 获取每日新闻摘要。
    频率控制：每天最多一次。
    """
    try:
        # 导入模块（避免循环导入）
        from utils.daily_news_skill import collect_daily_news, NEWS_TYPE
        
        # 频率控制：每天最多一次
        elapsed = seconds_since_last_collect(NEWS_TYPE)
        if elapsed is not None and elapsed < 86400:
            print(f"[daily] 跳过: 距上次采集 {elapsed:.0f}s < 86400s (24小时)")
            return 0
        
        # 调用每日新闻采集函数
        count = collect_daily_news()
        
        # 注意：collect_daily_news 内部已经调用了 set_last_collect_time
        print(f"[daily] 完成 | 采集:{count} 条")
        return count
    except Exception as e:
        print(f"[daily] 采集异常: {e}")
        return 0


# ═══════════════════════════════════════════════════════════════════
#  多线程并行采集入口（纯采集，不含 LLM）
# ═══════════════════════════════════════════════════════════════════

def collect_all_news() -> Dict[str, int]:
    """
    5 大板块并行采集（纯采集+入库+入Redis队列+WS推送）。
    不包含 LLM 分析——LLM 由独立消费者线程从 Redis 队列消费。

    Returns:
        {"company": 10, "cls": 5, "global": 8, "cctv": 3, "report": 2}
    """
    results = {}
    results_lock = threading.Lock()

    def _run(collect_func: callable, name: str):
        try:
            count = collect_func()
            with results_lock:
                results[name] = count
        except Exception as e:
            print(f"[{name}] 线程异常: {e}")
            with results_lock:
                results[name] = 0

    tasks = [
        (_collect_company, "company"),
        (_collect_cls, "cls"),
        (_collect_global, "global"),
        (_collect_cctv, "cctv"),
        (_collect_report, "report"),
        (_collect_daily, "daily"),
    ]

    print(f"[akshare] 启动 4 线程新闻板块并行采集...")

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for collect_func, name in tasks:
            future = executor.submit(_run, collect_func, name)
            futures.append(future)

        for future in futures:
            try:
                future.result(timeout=300)
            except Exception as e:
                print(f"[akshare] 线程等待异常: {e}")

    total = sum(results.values())
    print(f"[akshare] 5 大板块采集完成: {results}, 共 {total} 条")
    return results


# ═══════════════════════════════════════════════════════════════════
#  WebSocket 推送：入库后广播原始新闻
# ═══════════════════════════════════════════════════════════════════

def _push_news_to_ws(news_type: str, rows: list) -> int:
    """采集入库后通过 WebSocket 广播原始新闻到 news 频道。"""
    try:
        from utils.websocket_utils import ws_send_news_batch

        items = []
        for row in rows:
            if row.get("need_analyze") == 1:
                items.append({
                    "title": row.get("title", ""),
                    "content": (row.get("content", "") or "")[:200],
                    "url": row.get("url"),
                    "source": row.get("source", ""),
                    "news_type": news_type,
                    "publish_time": str(row.get("publish_time", "")),
                })

        if not items:
            return 0

        payload = {
            "type": "news_collected",
            "news_type": news_type,
            "count": len(items),
            "items": items,
            "timestamp": datetime.now().strftime(TIME_FMT),
        }
        ws_manager.broadcast_sync("news", payload)
        print(f"[ws] 推送 {news_type} 原始新闻 {len(items)} 条")
        return len(items)
    except Exception as e:
        print(f"[ws] 推送原始新闻失败: {e}")
        return 0


# ═══════════════════════════════════════════════════════════════════
#  单板块采集接口（供 fetch_routes 调用）
# ═══════════════════════════════════════════════════════════════════

# 板块采集函数映射
SECTION_COLLECTORS = {
    "company": _collect_company,
    "cls": _collect_cls,
    "global": _collect_global,
    "cctv": _collect_cctv,
    "report": _collect_report,
    "daily": _collect_daily,
}


def collect_section(section: str) -> int:
    """
    采集指定板块的新闻（供 fetch_routes 按需触发采集）。
    
    Args:
        section: 板块名称（company/cls/global/cctv/report/daily）
        
    Returns:
        采集到的新闻条数
    """
    if section not in SECTION_COLLECTORS:
        print(f"[collect_section] 未知板块: {section}")
        return 0
    
    collect_func = SECTION_COLLECTORS[section]
    try:
        count = collect_func()
        print(f"[collect_section] {section} 采集完成: {count} 条")
        return count
    except Exception as e:
        print(f"[collect_section] {section} 采集异常: {e}")
        return 0


# ═══════════════════════════════════════════════════════════════════
#  完整工作流：采集 → 入库 → WS推送 → 入Redis队列 → LLM消费
# ═══════════════════════════════════════════════════════════════════

def collect_and_analyze(limit: int = 20) -> Dict[str, dict]:
    """
    完整新闻采集工作流（终极三层 Redis 架构）。

    采集层职责（本函数）：
      - 5 大板块并行采集 → 清洗 → 写入 MySQL → 写入 news:data:{id} → 推入 news:pending_llm

    LLM 分析层职责（独立 8 线程，由 routes.py 启动时常驻运行）：
      - 从 news:pending_llm SPOP → 过滤 → 批量 LLM → 写回 news:data:{id} → 推入 news:pending_persist

    持久化层职责（独立定时线程）：
      - 每 5 秒 LRANGE+LTRIM 批量取 news:pending_persist → 读 Redis JSON → CASE 批量更新 MySQL

    Args:
        limit: 预留参数（兼容旧调用，新架构不使用）

    Returns:
        {"collect": {"company": 10, "cls": 5, ...}}
    """
    result = {}

    try:
        collect_result = collect_all_news()
        result["collect"] = collect_result
    except Exception as e:
        print(f"[workflow] 采集阶段异常: {e}")
        result["collect"] = {"error": str(e)}

    total_collect = sum(v for v in result.get("collect", {}).values() if isinstance(v, int))
    pending = 0
    try:
        from utils.redis_client import pending_llm_size
        pending = pending_llm_size()
    except Exception:
        pass
    print(f"[workflow] 采集完成 | 写入Redis:{total_collect}条 | 待LLM分析:{pending}条")

    return result


# ─── 命令行入口 ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="5 大新闻板块采集器")
    parser.add_argument("--date", type=str, default=None, help="目标日期 YYYY-MM-DD（预留）")
    args = parser.parse_args()

    results = collect_all_news()
    print(f"\n采集结果: {results}")
    print(f"合计: {sum(results.values())} 条")
