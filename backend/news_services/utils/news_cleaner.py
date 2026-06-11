"""
news_services/utils/news_cleaner.py — 新闻清洗与时间解析

从 utils/akshare.py 中迁移：
  - 新闻敏感性判断
  - CCTV 政策过滤
  - 批量清洗
  - 时间字符串解析
"""

import re
from datetime import date, datetime
from typing import Optional

from models.news_models import sanitize_text

# 统一时间格式
TIME_FMT = "%Y-%m-%d %H:%M:%S"


def need_llm_analyze(title: str, content: str, news_type: str) -> int:
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


def filter_cctv_policy(title: str, content: str) -> tuple:
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


def clean_news_rows(rows: list) -> list:
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
            need, reason = filter_cctv_policy(title, content)
            row["need_analyze"] = need
            row["_skip_reason"] = reason
        else:
            row["need_analyze"] = need_llm_analyze(title, content, news_type)

        cleaned.append(row)
    return cleaned


def parse_datetime(raw: str, fallback_hour: int = 0) -> Optional[datetime]:
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

    print(f"[news_cleaner] 时间解析失败: '{raw}'")
    return None


def extract_date_from_url(url: str, target_date: date) -> Optional[datetime]:
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
