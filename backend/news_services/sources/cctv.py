"""
news_services/sources/cctv.py — CCTV 新闻联播数据源采集
"""

from datetime import date, datetime
from typing import List

from news_services.utils import parse_datetime, TIME_FMT
from utils.redis_client_compat import (
    get_last_collect_time,
    is_cctv_today_done,
    reset_cctv_today_done,
    set_cctv_today_done,
)


def fetch_cctv(start_time: datetime, end_time: datetime) -> List[dict]:
    """
    CCTV 新闻联播采集（AkShare news_cctv）。
    支持指定日期回补（根据 end_time 确定采集日期）。
    """
    now = datetime.now()
    # 根据 end_time 确定目标日期（非今日或 end_time < now 取 end_time 的日期）
    # end_time 来自上一级采集调度的增量时间范围
    target_date = end_time.date() if end_time and end_time < now else now.date()

    # 非今日采集历史数据，直接放行
    if target_date < date.today():
        print(f"[cctv] 回补采集: {target_date}")
        return _do_fetch(target_date.strftime("%Y%m%d"))

    # 今日数据：跳过已完成标记，开始采集
    if is_cctv_today_done():
        print("[cctv] 跳过: 今日已采集完成")
        return []

    # 跨日重置
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

    return _do_fetch(date.today().strftime("%Y%m%d"))


def _do_fetch(date_param: str) -> List[dict]:
    """核心采集逻辑：调用 AKShare 获取指定日期的新闻联播数据"""
    import akshare as ak

    print(f"[cctv] 开始采集新闻联播 ({date_param})...")

    try:
        df = ak.news_cctv(date=date_param)
    except Exception as e:
        print(f"[cctv] 获取失败: {e}")
        return []

    if df is None or df.empty:
        print(f"[cctv] 无数据 ({date_param})")
        return []

    rows = []
    for _, row in df.iterrows():
        title = str(row.get("title", "")).strip()
        if not title:
            continue

        raw_date = str(row.get("date", ""))
        pub_time = parse_datetime(raw_date, fallback_hour=19)
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

    if rows and date_param >= date.today().strftime("%Y%m%d"):
        set_cctv_today_done()
        print(f"[cctv] 采集完成 {len(rows)} 条，已标记今日完成")

    return rows
