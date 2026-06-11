"""
news_services/sources/eastmoney.py — 东方财富数据源采集

涵盖：
  - fetch_company: 个股新闻（stock_news_em）
  - fetch_global:  全球新闻（stock_info_global_ths）
  - fetch_report:  深度研报（stock_research_report_em）
"""

import time
from datetime import date, datetime
from typing import List

from news_services.utils import parse_datetime, TIME_FMT
from news_services.config import COLLECT_SYMBOLS


def fetch_company(start_time: datetime, end_time: datetime) -> List[dict]:
    """
    个股/公司新闻采集（AkShare stock_news_em）。
    """
    import akshare as ak

    symbols = COLLECT_SYMBOLS
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

                pub_time = parse_datetime(str(row.get("发布时间", "")))
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


def fetch_global(start_time: datetime, end_time: datetime) -> List[dict]:
    """
    全球新闻采集（AkShare stock_info_global_ths）。
    """
    import akshare as ak

    start_str = start_time.strftime(TIME_FMT)
    end_str = end_time.strftime(TIME_FMT)
    print(f"[AkShare] 开始采集新闻 板块=global")
    print(f"[global] 增量采集 {start_str} ~ {end_str}")

    all_rows = []
    seen_titles = set()

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
        pub_time = parse_datetime(pub_time_str)
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
    return all_rows


def fetch_report(start_time: datetime, end_time: datetime) -> List[dict]:
    """
    研报新闻采集（AkShare stock_research_report_em）。
    """
    import akshare as ak

    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    print(f"[AkShare] 开始采集新闻 板块=report")
    print(f"[report] 深度研报采集 | 当天: {today_str}")

    all_rows = []
    seen_titles = set()

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
        content = f"[{org}] 评级:{rating} 行业:{industry}"
        pub_time_str = str(row.get("日期", ""))
        pub_time = parse_datetime(pub_time_str, fallback_hour=8)
        if pub_time is None:
            continue
        if pub_time.date() != today:
            continue
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
    return all_rows
