"""
stock_services/indicators/volume_indicators.py — 成交量指标计算

覆盖三个成交量指标：
  · VWMA         成交量加权移动平均（Volume Weighted Moving Average）
  · VR           成交量变异率（Volume Ratio）
  · Volume Bias  成交量乖离率

所有函数接受 K线列表 [{open,high,low,close,vol,trade_date}, ...]，
返回与输入等长的计算结果列表，每项为 dict。
使用滑动窗口累加器，O(N) 时间复杂度。
"""

from typing import Any, Dict, List, Optional


def calc_vwma(klines: List[Dict], period: int = 20) -> List[Dict]:
    """
    成交量加权移动平均 VWMA。

    VWMA(i) = Σ(close_j × vol_j) / Σ(vol_j)   j ∈ [i-period+1, i]

    滑动窗口累加器实现，O(N)。
    不足周期时以收盘价填充（与通达信习惯一致）。
    Kline 记录需包含 trade_date, close, vol 字段。
    """
    result: List[Dict[str, Any]] = []
    n = len(klines)
    if n == 0:
        return result

    close_arr = [r.get("close", 0.0) or 0.0 for r in klines]
    vol_arr = [r.get("vol", 0.0) or 0.0 for r in klines]

    price_vol_sum = 0.0
    vol_sum = 0.0

    for i in range(n):
        price_vol_sum += close_arr[i] * vol_arr[i]
        vol_sum += vol_arr[i]

        if i >= period - 1:
            vwma = round(price_vol_sum / vol_sum, 4) if vol_sum > 0 else 0.0
            # 滑动窗口：移除窗口最旧元素
            j = i - period + 1
            price_vol_sum -= close_arr[j] * vol_arr[j]
            vol_sum -= vol_arr[j]
        else:
            vwma = round(close_arr[i], 4)  # 不足周期以收盘价填充

        result.append({
            "trade_date": str(klines[i].get("trade_date", "")),
            "vwma": vwma,
        })

    return result


def calc_vr(klines: List[Dict], period: int = 26) -> List[Dict]:
    """
    成交量变异率 VR（Volume Ratio）。

    VR(N) = (A + B/2) / (C + B/2) × 100
      A = 上涨日成交量之和（close_i > close_{i-1})
      B = 平盘日成交量之和（close_i = close_{i-1})
      C = 下跌日成交量之和（close_i < close_{i-1})
    统计区间 [i-N+1, i]。

    滑动窗口累加器实现，O(N)。
    不足周期时返回 VR=100。
    Kline 记录需包含 trade_date, close, vol 字段。
    """
    result: List[Dict[str, Any]] = []
    n = len(klines)
    if n < 1:
        return result

    close_arr = [r.get("close", 0.0) or 0.0 for r in klines]
    vol_arr = [r.get("vol", 0.0) or 0.0 for r in klines]

    a_sum = b_sum = c_sum = 0.0

    for i in range(1, n):  # VR 从第1条开始（需与前一条比较涨跌方向）
        vol_i = vol_arr[i]
        if close_arr[i] > close_arr[i - 1]:
            a_sum += vol_i
        elif close_arr[i] < close_arr[i - 1]:
            c_sum += vol_i
        else:
            b_sum += vol_i

        if i >= period:
            denominator = c_sum + b_sum / 2.0
            vr = round(100 * (a_sum + b_sum / 2.0) / denominator, 2) if denominator != 0 else 999.0

            # 滑动窗口：移除最旧元素（索引 i - period + 1）
            j = i - period + 1
            remove_vol = vol_arr[j]
            if close_arr[j] > close_arr[j - 1]:
                a_sum -= remove_vol
            elif close_arr[j] < close_arr[j - 1]:
                c_sum -= remove_vol
            else:
                b_sum -= remove_vol
        else:
            vr = 100.0  # 不足周期使用默认值

        result.append({
            "trade_date": str(klines[i].get("trade_date", "")),
            "vr": vr,
        })

    return result


def calc_volume_bias(klines: List[Dict], periods: Optional[List[int]] = None) -> List[Dict]:
    """
    成交量乖离率 Volume Bias。

    Volume_Bias_N(i) = (vol_i - MA(vol, N, i)) / MA(vol, N, i) × 100
    MA(vol, N, i) 为近 N 日平均成交量。

    支持多周期并行计算，O(N×P)，P 通常 ≤3。
    Kline 记录需包含 trade_date, vol 字段。
    """
    if periods is None:
        periods = [5, 10, 20]

    result: List[Dict[str, Any]] = []
    n = len(klines)
    if n == 0:
        return result

    vol_arr = [r.get("vol", 0.0) or 0.0 for r in klines]

    for i in range(n):
        vol_val = vol_arr[i]
        entry: Dict[str, Any] = {"trade_date": str(klines[i].get("trade_date", ""))}

        for p in periods:
            if i >= p - 1:
                # P ≤ 3 且 p ≤ 20, 直接切片计算更简洁
                window = vol_arr[i - p + 1:i + 1]
                ma = sum(window) / p
                bias = round((vol_val - ma) / ma * 100, 2) if ma != 0 else 0.0
                entry[f"volume_bias_{p}"] = bias
            else:
                entry[f"volume_bias_{p}"] = 0.0

        result.append(entry)

    return result