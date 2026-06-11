"""
stock_services/indicators/ — 技术指标计算包

导出 compute_all() 统一入口，接收K线列表返回全部指标。
"""

from .technical import compute_all, INDICATOR_VERSION

__all__ = ["compute_all", "INDICATOR_VERSION"]