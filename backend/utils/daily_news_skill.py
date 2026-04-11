"""
utils/daily_news_skill.py — 每日新闻技能模块（转发层）

功能：
  - 转发到 full_news_get.py 中的对应函数
  - 保持与 routes.py 的兼容性

注意：
  - 这是一个转发层，实际功能在 full_news_get.py 中实现
  - 保持原有接口不变，确保现有代码正常运行
"""

from .full_news_get import (
    repair_daily_news_func as repair_daily_news,
    _fetch_global_full as fetch_daily_news_by_date,
    _push_to_system as push_news_to_system,
)

# 导出函数，保持与原有导入兼容
__all__ = [
    'fetch_daily_news_by_date',
    'push_news_to_system',
    'repair_daily_news',
]