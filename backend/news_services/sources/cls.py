"""
news_services/sources/cls.py — 财联社数据源采集
"""

import time
from datetime import datetime
from typing import List

from news_services.utils import parse_datetime, TIME_FMT


def fetch_cls(start_time: datetime, end_time: datetime) -> List[dict]:
    """
    财联社新闻采集（AkShare stock_info_global_cls）。
    """
    import akshare as ak

    start_str = start_time.strftime(TIME_FMT)
    end_str = end_time.strftime(TIME_FMT)
    print(f"[AkShare] 开始采集新闻 板块=cls")
    print(f"[cls] 增量采集 {start_str} ~ {end_str}")

    all_rows = []
    seen_titles = set()

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

        date_str = str(row.get("发布日期", "")).strip()
        time_str = str(row.get("发布时间", "")).strip()

        if date_str and time_str:
            pub_time_str = f"{date_str} {time_str}"
        elif date_str:
            pub_time_str = f"{date_str} 00:00:00"
        elif time_str:
            today = datetime.now().strftime("%Y-%m-%d")
            pub_time_str = f"{today} {time_str}"
        else:
            pub_time_str = ""

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
            "source": "财联社",
            "source_category": "财联社",
            "news_type": "cls",
            "publish_time": pub_time,
        })

    print(f"[AkShare] 采集成功 条数={len(all_rows)}")
    return all_rows
