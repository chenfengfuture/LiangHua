"""
stock_services/common/date_utils.py — 日期工具统一封装
"""

import logging
from datetime import date, datetime, timedelta, time
from typing import Any, Dict, List, Optional, Union

from mootdx.utils.holiday import holiday as mootdx_holiday
import pandas as pd
from typing import List
from mootdx.utils.holiday import holidays
from system_service.service_result import success_result, error_result

logger = logging.getLogger(__name__)


# ─── 默认 A 股节假日集合（2026 年已知假期，过渡用） ──────────────
# 通过 HOLIDAYS_PROVIDER hook 可替换为动态加载
_DEFAULT_A_HOLIDAYS: set = {
    date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3),
    date(2026, 2, 16), date(2026, 2, 17), date(2026, 2, 18),
    date(2026, 2, 19), date(2026, 2, 20), date(2026, 2, 21),
    date(2026, 4, 4), date(2026, 4, 5), date(2026, 4, 6),
    date(2026, 5, 1), date(2026, 5, 2), date(2026, 5, 3),
    date(2026, 5, 4), date(2026, 5, 5),
    date(2026, 6, 20), date(2026, 6, 21), date(2026, 6, 22),
    date(2026, 9, 27), date(2026, 9, 28), date(2026, 9, 29),
    date(2026, 9, 30),
    date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3),
    date(2026, 10, 4), date(2026, 10, 5), date(2026, 10, 6),
    date(2026, 10, 7),
}

# 可动态替换的节假日提供者（函数签名：() -> set[date]）
# 设置为 None 时使用 _DEFAULT_A_HOLIDAYS
HOLIDAYS_PROVIDER = None


# ═══════════════════════════════════════════════════════════════════
#  日期解析
# ═══════════════════════════════════════════════════════════════════

def parse_date(date_str: Any, default_delta_days: int = 0) -> date:
    """
    统一日期解析：YYYYMMDD / YYYY-MM-DD / None → date

    替代以下分散实现：
      - mootdx/base_service.py _parse_date()
      - services/stock_indicator_service.py _parse_date()

    Args:
        date_str: 日期字符串或 None
        default_delta_days: None 时往前推 N 天

    Returns:
        解析后的 date 对象
    """
    if not date_str:
        return date.today() - timedelta(days=default_delta_days)

    s = str(date_str).strip().replace("-", "")
    if len(s) == 8:
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except ValueError:
            pass
    return date.today()



def fmt_date(d: date, fmt: str = "%Y-%m-%d") -> str:
    """
    格式化日期，统一入口。

    替代 services/stock_indicator_service.py 的 _fmt_date()。

    Args:
        d: date 对象
        fmt: 日期格式，默认 %Y-%m-%d

    Returns:
        格式化日期字符串
    """
    return d.strftime(fmt)


# ═══════════════════════════════════════════════════════════════════
#  K 线 offset 计算
# ═══════════════════════════════════════════════════════════════════

MINUTE_BARS_OFFSET_DEFAULT = 800

def calc_offset(start_d: date, end_d: date, freq_code: int) -> int:
    """
    计算 mootdx bars() 所需 offset。

    替代 mootdx/base_service.py _calc_offset()。

    Args:
        start_d:   起始日期
        end_d:     结束日期
        freq_code: 频率编码（9=day, 7=week, 8=month, 0/1/2/3/4=分钟）

    Returns:
        offset 整数值
    """
    today = date.today()
    days_ago = (today - start_d).days

    if freq_code == 9:      # day
        return max(int(days_ago * 1.5), 10)
    elif freq_code == 7:    # week
        return max(days_ago // 7 + 10, 10)
    elif freq_code == 8:    # month
        return max(days_ago // 30 + 5, 5)
    else:                   # minute
        return MINUTE_BARS_OFFSET_DEFAULT


# ═══════════════════════════════════════════════════════════════════
#  交易日判断
# ═══════════════════════════════════════════════════════════════════

def is_trading_day(d: date) -> bool:
    """
    判断某天是否为 A 股交易日。

    优先级：
      1. 周末（非交易日）
      2. mootdx 网络接口查询
      3. 接口失败 → 回退本地 _DEFAULT_A_HOLIDAYS 硬编码

    Args:
        d: 待判断日期

    Returns:
        True 为交易日，False 为休市日
    """
    # 1. 周末直接排除
    if d.weekday() >= 5:
        return False

    # 2. 优先通过 mootdx 网络接口判断
    try:
        return not mootdx_holiday(d.strftime('%Y-%m-%d'))
    except Exception as e:
        logger.warning(f"[is_trading_day] mootdx holiday 接口调用失败，回退本地硬编码: {e}")

    return d not in _DEFAULT_A_HOLIDAYS



def ensure_trading_day(d: date, fallback_prev: bool = False) -> Optional[date]:
    """
    获取指定日期的交易日版本。

    Args:
        d:            待判断日期
        fallback_prev: 如果 d 非交易日，是否回退到上一个交易日

    Returns:
        - 如果 d 是交易日，返回 d
        - 如果 d 不是交易日且 fallback_prev=True，往前查找最近的交易日
        - 如果 d 不是交易日且 fallback_prev=False，返回 None
    """
    if is_trading_day(d):
        return d

    if not fallback_prev:
        return None

    # 往前逐个回退，最多查找 30 天（防止死循环）
    for i in range(1, 31):
        prev = d - timedelta(days=i)
        if is_trading_day(prev):
            return prev

    logger.warning(f"[ensure_trading_day] 在 {d} 前 30 天内未找到交易日")
    return None


def is_market_closed() -> bool:
    """判断当前是否已收盘（>=15:00）"""
    return datetime.now().time() >= time(15, 0, 0)

def get_stock_market(symbol: str) -> str:
    """
    根据股票代码判断所属市场
    返回：SH / SZ / BJ / None
    Args:
        symbol:

    Returns:

    """
    if not isinstance(symbol, str) or not symbol:
        return None
    symbol = symbol.strip()
    # 前缀 -> 市场代码
    prefix_map = {
        ('600', '601', '603', '605', '688', '689'): 'SH',
        ('000', '001', '002', '003', '300', '301'): 'SZ',
        ('8', '43'): 'BJ',
        ('900',): 'SHB',
        ('200',): 'SZB',
    }
    for prefixes, market in prefix_map.items():
        if symbol.startswith(prefixes):
            return market
    return None


def get_trading_days(start_date, end_date) -> dict:
    """
    获取 时间周期内的 交易日 以及判定是否为交易日
    Args:
        start_date: 起始日期
        end_date:  结束日期

    Returns:

    """

    def to_date(d):
        if isinstance(d, date):
            return d
        if isinstance(d, str):
            # 支持 "2026-06-01" 或 "20260601"
            for fmt in ("%Y-%m-%d", "%Y%m%d"):
                try:
                    return datetime.strptime(d, fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"日期字符串格式错误，应为 YYYY-MM-DD 或 YYYYMMDD: {d}")
        raise TypeError(f"参数类型错误，应为 date 或 str，实际为 {type(d)}")

    start_date = to_date(start_date)
    if end_date is None:
        end_date = start_date
    else:
        end_date = to_date(end_date)

    all_trading_df = holidays()  # 注意：这个函数名虽然叫 holidays，但返回的是交易日
    all_trading_df['date'] = pd.to_datetime(all_trading_df['date'])

    # 筛选 start_date 到 end_date 之间的交易日
    mask = (all_trading_df['date'] >= pd.to_datetime(start_date)) & (all_trading_df['date'] <= pd.to_datetime(end_date))
    trading_days = all_trading_df.loc[mask, 'date'].dt.date.tolist()
    num = len(trading_days) if trading_days else 0
    result = {'count': num, 'trading_day': trading_days }
    return success_result(data=result)




# def get_trading_days(start_d: date, end_d: date) -> List[date]:
#     """
#     获取 [start_d, end_d] 范围内的所有交易日。
#
#     替代 mootdx/base_service.py get_trading_days()。
#
#     Args:
#         start_d: 起始日期（含）
#         end_d:   结束日期（含）
#
#     Returns:
#         交易日列表
#     """
#     days = []
#     cur = start_d
#     while cur <= end_d:
#         if is_trading_day(cur):
#             days.append(cur)
#         cur += timedelta(days=1)
#     return days
#

def validate_date_range(
    start_d: date,
    end_d: date,
    freq: str = "day",
) -> tuple:
    """
    校验日期范围，过滤非交易日。

    替代 mootdx/base_service.py _validate_date_range()。

    Args:
        start_d: 起始日期
        end_d:   结束日期
        freq:    频率（day/week/month）

    Returns:
        (有效起始日, 有效结束日, 跳过天数)
        若非交易日区间，返回 (None, None, skipped)
    """
    if freq in ("week", "month"):
        return start_d, end_d, 0

    total_days = (end_d - start_d).days + 1
    trading_result = get_trading_days(start_d, end_d)
    trading_days = trading_result.get('data', {}).get('trading_day', [])
    skipped = total_days - len(trading_days)

    if not trading_days:
        return None, None, skipped

    return trading_days[0], trading_days[-1], skipped


# ═══════════════════════════════════════════════════════════════════
#  批量日期字段填充（来自 utils/board_field_mapper.py）
# ═══════════════════════════════════════════════════════════════════

def add_stat_date(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    为每条记录添加统计日期字段（stat_date）。

    替代 utils/board_field_mapper.py add_stat_date()。

    此函数在 10+ 个 unity service 文件中被调用，
    封装到此处可减少重复代码约 60 行。
    """
    today = date.today().isoformat()
    for item in result:
        if "stat_date" not in item:
            item["stat_date"] = today
    return result


def add_rank_date(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    为每条记录添加排名日期字段（rank_date）。

    替代 utils/board_field_mapper.py add_rank_date()。
    """
    today = date.today().isoformat()
    for item in result:
        if "rank_date" not in item:
            item["rank_date"] = today
    return result


def add_change_date(result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    为每条记录添加异动日期字段（change_date）。

    替代 utils/board_field_mapper.py add_change_date()。
    """
    today = date.today().isoformat()
    for item in result:
        if "change_date" not in item:
            item["change_date"] = today
    return result


# ═══════════════════════════════════════════════════════════════════
#  日期字符串验证（来自 utils/validate_params.py）
# ═══════════════════════════════════════════════════════════════════

def validate_date_format(date_str: str, date_format: str = "%Y-%m-%d") -> tuple:
    """
    验证日期字符串格式。

    Args:
        date_str:    日期字符串
        date_format: 期望格式

    Returns:
        (success: bool, message: str)
    """
    if not date_str:
        return False, "日期不能为空"
    try:
        datetime.strptime(date_str, date_format)
        return True, ""
    except ValueError:
        return False, f"日期格式不正确: {date_str}，期望 {date_format}"


def validate_date_range_str(start_date: str, end_date: str,
                            date_format: str = "%Y-%m-%d") -> tuple:
    """
    验证日期范围字符串（结束不早于开始）。

    Args:
        start_date: 开始日期字符串
        end_date:   结束日期字符串
        date_format: 日期格式

    Returns:
        (success: bool, message: str)
    """
    ok, msg = validate_date_format(start_date, date_format)
    if not ok:
        return False, msg
    ok, msg = validate_date_format(end_date, date_format)
    if not ok:
        return False, msg

    start_dt = datetime.strptime(start_date, date_format)
    end_dt = datetime.strptime(end_date, date_format)

    if end_dt < start_dt:
        return False, f"结束日期 {end_date} 不能早于开始日期 {start_date}"

    return True, ""


__all__ = [
    "parse_date",
    "fmt_date",
    "calc_offset",
    "is_trading_day",
    "ensure_trading_day",
    "get_trading_days",
    "validate_date_range",
    "add_stat_date",
    "add_rank_date",
    "add_change_date",
    "validate_date_format",
    "validate_date_range_str",
    "HOLIDAYS_PROVIDER",
]