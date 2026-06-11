"""
news_services/sources/ — 数据源层

按数据源拆分采集函数：
  - eastmoney: 个股/全球/研报（东方财富）
  - cls:       财联社
  - cctv:      新闻联播
"""

from .eastmoney import fetch_company, fetch_global, fetch_report
from .cls import fetch_cls
from .cctv import fetch_cctv

__all__ = [
    "fetch_company",
    "fetch_global",
    "fetch_report",
    "fetch_cls",
    "fetch_cctv",
]
