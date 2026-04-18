"""
utils/full_news_get.py — 全球新闻全量补全服务（独立，不修改原有代码）

功能：
  - 使用新版东方财富全球快讯API补全历史全球新闻
  - 支持指定日期范围补全
  - 自动分页、增量过滤、content_hash去重
  - 兼容现有三层管道架构（入库 → Redis → LLM队列）
  - 支持手动/自动双模式

接口来源：
  - API: https://np-weblist.eastmoney.com/comm/web/getFastNewsList
  - fastColumn=102 → 全球快讯（7*24小时全球财经）
  - 分页：使用 sortEnd 翻页
  - pageSize=200，最多25页
"""

import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from models.news_models import (
    ensure_table_exists,
    insert_news_with_content_hash,
)
from utils.redis_client import (
    news_data_set,
    pending_llm_add_batch,
)
from utils.websocket_utils import ws_send_news_batch

# 统一时间格式
TIME_FMT = "%Y-%m-%d %H:%M:%S"


def _parse_datetime(pub_time_str: str) -> Optional[datetime]:
    """
    解析东方财富返回的发布时间。
    支持格式："2026-04-10 12:34"
    """
    if not pub_time_str or not pub_time_str.strip():
        return None

    pub_time_str = pub_time_str.strip()

    # 标准格式: "YYYY-MM-DD HH:MM"
    try:
        return datetime.strptime(pub_time_str, "%Y-%m-%d %H:%M")
    except ValueError:
        pass

    # 其他格式尝试
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(pub_time_str, fmt)
        except ValueError:
            continue

    return None


def _calc_content_hash(title: str, content: str) -> str:
    """计算内容哈希用于去重"""
    combined = (title.strip() + (content or "").strip()).encode("utf-8")
    return hashlib.md5(combined).hexdigest()


def _fetch_global_full(
    start_time: datetime,
    end_time: datetime,
) -> List[Dict]:
    """
    从东方财富API分页获取全球新闻全量数据。

    Args:
        start_time: 开始时间（只返回此时间之后的新闻）
        end_time: 结束时间（只返回此时间之前的新闻）

    Returns:
        清洗后的新闻列表，每条包含完整字段

    强化稳定性：
    - 所有网络请求完整try-except
    - 空数据直接跳过
    - 时间解析失败跳过单条，不中断
    - 有效条数为0立即退出循环，防止死循环
    - sortEnd为空立即结束
    - 全页早于start_time立即中止
    - 最多25页限制
    """
    api_url = "https://np-weblist.eastmoney.com/comm/web/getFastNewsList"

    all_rows: List[Dict] = []
    seen_content_hash = set()
    sort_end = ""
    page_num = 0
    max_pages = 25

    start_str = start_time.strftime(TIME_FMT)
    end_str = end_time.strftime(TIME_FMT)
    print(f"[full-global] 开始全量获取 {start_str} ~ {end_str}")

    while True:
        params = {
            "client": "web",
            "biz": "web_724",
            "fastColumn": "102",
            "sortEnd": str(sort_end),
            "pageSize": "200",
            "req_trace": f"{int(time.time() * 1000)}",
        }

        # 请求当前页
        try:
            print(f"[full-global] 请求第{page_num + 1}页 ... sortEnd={sort_end[:20]}...")
            r = requests.get(api_url, params=params, timeout=15)
            r.encoding = "utf-8"
            data = r.json()
        except Exception as e:
            print(f"[full-global] 第{page_num + 1}页请求失败: {e}")
            break

        # 提取新闻列表
        items = data.get("data", {}).get("fastNewsList", [])
        if not items:
            print(f"[full-global] 第{page_num + 1}页无数据，结束")
            break

        # 获取下一页sortEnd
        new_sort_end = data.get("data", {}).get("sortEnd", "")
        if not new_sort_end:
            print(f"[full-global] sortEnd为空，结束")
            break

        page_valid_count = 0
        page_early_count = 0

        for item in items:
            title = str(item.get("title", "")).strip()
            if not title:
                continue

            content = str(item.get("summary", "")).strip()
            content_hash = _calc_content_hash(title, content)

            # 内容去重
            if content_hash in seen_content_hash:
                continue
            seen_content_hash.add(content_hash)

            # 解析时间
            pub_time = _parse_datetime(str(item.get("showTime", "")))
            if pub_time is None:
                continue

            # 时间范围过滤
            if pub_time < start_time:
                page_early_count += 1
                continue
            if pub_time > end_time:
                continue

            code = str(item.get("code", "")).strip()
            news_url = f"https://finance.eastmoney.com/a/{code}.html" if code else None

            page_valid_count += 1
            all_rows.append({
                "title": title,
                "content": content,
                "url": news_url,
                "source": "东方财富",
                "source_category": "东方财富全球",
                "news_type": "global",
                "publish_time": pub_time,
                "content_hash": content_hash,
            })

        page_num += 1
        print(f"[full-global] 第{page_num}页: 获取={len(items)}条 有效增量={page_valid_count}条 累计={len(all_rows)}条")

        # 如果本页没有有效增量数据，提前中止
        if page_valid_count == 0:
            print(f"[full-global] 本页无有效增量数据，结束")
            break

        # 如果本页全部都早于start_time，说明已经翻到更早的新闻了，提前中止
        if page_early_count == len(items):
            print(f"[full-global] 本页全部新闻早于开始时间，结束翻页")
            break

        # 达到最大页数限制
        if page_num >= max_pages:
            print(f"[full-global] 达到最大页数限制 ({max_pages}页)，结束")
            break

        # 更新sortEnd准备下一页
        sort_end = new_sort_end

        # 分页间隔，避免请求过快
        time.sleep(0.3)

    print(f"[full-global] 全量获取完成，共 {len(all_rows)} 条有效新闻")
    return all_rows


def _push_to_system(
    news_list: List[Dict],
    year_month: str,
    push_to_ws: bool = False,
) -> int:
    """
    将获取到的新闻推入系统：去重 → 入库 → Redis缓存 → LLM队列。

    Args:
        news_list: 新闻列表，来自 _fetch_global_full
        year_month: 年月，用于分表（格式 YYYYMM）
        push_to_ws: 是否推送WebSocket给前端（自动补全=False，手动补全=True）

    Returns:
        成功推入的条数
    
    说明：
    去重、清洗、入库、Redis、LLM全部沿用现有逻辑，不修改现有代码。
    WebSocket推送仅在手动模式push_to_ws=True时执行，自动模式不推送。
    """
    if not news_list:
        return 0

    # 确保分表存在
    ensure_table_exists("global", year_month)
    table_name = f"news_global_{year_month}"

    pushed_count = 0
    for news in news_list:
        title = news.get("title", "")
        content = news.get("content", "")
        url = news.get("url")
        source = news.get("source", "东方财富")
        source_category = news.get("source_category", "东方财富全球")
        news_type = news.get("news_type", "global")
        content_hash = news.get("content_hash", "")
        publish_time = news.get("publish_time")

        # 格式化publish_time
        publish_time_str = publish_time.strftime(TIME_FMT) if publish_time else ""

        # 插入数据库（自动去重基于content_hash）
        news_id = insert_news_with_content_hash(
            table_name=table_name,
            title=title,
            content=content,
            url=url,
            source=source,
            source_category=source_category,
            news_type=news_type,
            content_hash=content_hash,
            publish_time=publish_time_str,
        )

        if news_id is None:
            # 重复或插入失败
            continue

        # 写入 Redis String（包含完整数据供LLM分析）
        redis_data = {
            "id": news_id,
            "title": title,
            "content": content,
            "url": url,
            "source": source,
            "source_category": source_category,
            "news_type": news_type,
            "table_name": table_name,
            "need_analyze": 1,
        }
        news_data_set(news_id, redis_data, table_name)

        # 推入 LLM 分析队列 → 沿用现有逻辑，不修改现有LLM代码
        pending_llm_add_batch([news_id], table_name)
        pushed_count += 1

    print(f"[full-global] 推入系统完成: 成功={pushed_count}/{len(news_list)}")

    # WebSocket推送 → 仅手动推送，自动不推送
    if push_to_ws and pushed_count > 0:
        try:
            ws_send_news_batch([
                {
                    "news_id": news_id,
                    "data": {
                        "title": news["title"],
                        "source": news["source"],
                        "publish_time": news["publish_time"].strftime(TIME_FMT),
                    },
                }
                for news in news_list[:pushed_count]
            ])
        except Exception as e:
            print(f"[full-global] WebSocket推送失败: {e}")

    return pushed_count


def repair_global_news_date_range(
    start_date: str,
    end_date: str = None,
    is_manual: bool = False,
) -> Dict:
    """
    补全指定日期范围的全球新闻（支持手动/自动双模式）。

    模式说明：
    - **手动模式** (`is_manual=True`, API调用时):
      获取新闻 → 清洗 → 入库 → Redis → LLM队列 → WebSocket推送前端
      完全遵循现有的实时新闻获取-入库-推送完整流程
    
    - **自动模式** (`is_manual=False`, 默认):
      获取新闻 → 清洗 → 入库 → Redis → LLM队列（不推送WebSocket）
      项目启动自动补全时静默执行，不干扰前端
    
    约束：
    - 禁止修改现有实时新闻相关代码，本封装只复用数据处理逻辑
    - 去重、清洗、入库、Redis、LLM全部沿用现有逻辑，不修改现有代码
    - 全量补全时间字段独立，不影响现有实时采集时间

    Args:
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD，默认与开始日期相同
        is_manual: 
            - True = 手动模式，推送WebSocket到前端
            - False = 自动模式，不推送WebSocket，默认 False

    Returns:
        统计结果字典
    """
    # 解析日期范围
    if end_date is None:
        end_date = start_date

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        print(f"[full-global] 日期格式错误: {e}")
        return {
            "success": False,
            "error": f"日期格式错误: {e}",
            "total_fetched": 0,
            "total_pushed": 0,
        }

    # 转换为完整时间范围
    start_time = start_dt
    end_time = datetime(
        end_dt.year,
        end_dt.month,
        end_dt.day,
        23,
        59,
        59,
    )

    # 获取年月用于分表
    year_month = start_dt.strftime("%Y%m")

    try:
        # 分页获取全量数据
        news_list = _fetch_global_full(start_time, end_time)

        if not news_list:
            return {
                "success": True,
                "start_date": start_date,
                "end_date": end_date,
                "total_days": (end_dt - start_dt).days + 1,
                "total_fetched": 0,
                "total_pushed": 0,
                "message": "指定日期范围内无新闻",
            }

        # 推入系统（入库 → Redis → LLM）
        pushed = _push_to_system(news_list, year_month, push_to_ws=is_manual)

        return {
            "success": True,
            "start_date": start_date,
            "end_date": end_date,
            "total_days": (end_dt - start_dt).days + 1,
            "total_fetched": len(news_list),
            "total_pushed": pushed,
            "message": f"成功获取 {len(news_list)} 条，推入系统 {pushed} 条",
        }

    except Exception as e:
        print(f"[full-global] 补全失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_fetched": 0,
            "total_pushed": 0,
        }


def repair_global_news_single_date(
    date: str,
    is_manual: bool = False,
) -> Dict:
    """补全单个日期的全球新闻"""
    return repair_global_news_date_range(date, date, is_manual)


def repair_daily_news_func(
    start_date: str,
    end_date: str = None,
    is_manual: bool = False,
) -> Dict:
    """
    修复历史每日新闻（复用全球新闻补全逻辑，支持手动/自动双模式）。

    模式说明：
    - **手动模式** (`is_manual=True`, API调用时):
      获取新闻 → 清洗 → 入库 → Redis → LLM队列 → WebSocket推送前端
      完全遵循现有的实时新闻获取-入库-推送完整流程
    
    - **自动模式** (`is_manual=False`, 默认):
      获取新闻 → 清洗 → 入库 → Redis → LLM队列（不推送WebSocket）
      项目启动自动补全时静默执行，不干扰前端
    
    约束：
    - 禁止修改现有实时新闻相关代码，本封装只复用数据处理逻辑
    - 去重、清洗、入库、Redis、LLM全部沿用现有逻辑，不修改现有代码
    - 时间戳记录独立，不影响现有实时采集时间记录

    Args:
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD，默认与开始日期相同
        is_manual: 
            - True = 手动模式，推送WebSocket到前端
            - False = 自动模式，不推送WebSocket，默认 False

    Returns:
        统计结果字典，格式与 `repair_global_news_date_range` 完全一致
    """
    # 完全复用全球新闻补全逻辑，只增加推送控制
    push_to_ws = is_manual  # 手动模式=推送WebSocket，自动模式=不推送
    return repair_global_news_date_range(
        start_date=start_date,
        end_date=end_date,
        is_manual=is_manual,
    )
