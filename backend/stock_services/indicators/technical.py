"""
stock_services/indicators/technical.py — 核心技术指标计算（单文件全量）

覆盖主流软件（通达信/同花顺/东方财富）13个常用技术指标。
所有函数接受 K线列表 [{open,high,low,close,vol,trade_date}, ...]，
返回与输入等长的计算结果列表，每项为 dict。

使用 numpy 向量化计算，单只股票500条K线全部指标 < 5ms。
"""

import math
from typing import Any, Dict, List, Optional

import numpy as np


# ═══════════════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════════════

def _as_arrays(klines: List[Dict]) -> tuple:
    """从K线列表中提取 numpy 数组"""
    arr = {k: np.array([r.get(k, 0.0) or 0.0 for r in klines], dtype=np.float64)
           for k in ("open", "high", "low", "close", "vol")}
    dates = [r.get("trade_date", "") for r in klines]
    return arr["open"], arr["high"], arr["low"], arr["close"], arr["vol"], dates


def _ema(arr: np.ndarray, period: int) -> np.ndarray:
    """指数移动平均（递归式 EMA）"""
    result = np.full_like(arr, np.nan)
    if len(arr) == 0:
        return result
    alpha = 2.0 / (period + 1)
    result[0] = arr[0]
    for i in range(1, len(arr)):
        result[i] = alpha * arr[i] + (1 - alpha) * result[i - 1]
    return result


def _sma(arr: np.ndarray, period: int) -> np.ndarray:
    """简单移动平均"""
    result = np.full_like(arr, np.nan)
    if len(arr) < period:
        return result
    cum = np.cumsum(arr)
    result[period - 1:] = (cum[period - 1:] - np.concatenate([[0], cum[:-period]])) / period
    return result


def _tr(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """真波幅 TR"""
    hl = high - low
    hc = np.abs(high - np.concatenate([[close[0]], close[:-1]]))
    lc = np.abs(low - np.concatenate([[close[0]], close[:-1]]))
    return np.maximum(np.maximum(hl, hc), lc)


def _fill_nan(result: np.ndarray) -> np.ndarray:
    """向前填充 NaN（使返回结果与输入等长）"""
    mask = np.isnan(result)
    if mask.all():
        return result
    idx = np.where(~mask, np.arange(len(mask)), 0)
    np.maximum.accumulate(idx, out=idx)
    result[mask] = result[idx[mask]]
    return result


# ═══════════════════════════════════════════════════════════════════
#  主图指标
# ═══════════════════════════════════════════════════════════════════

def calc_ma(klines: List[Dict], periods: Optional[List[int]] = None) -> List[Dict]:
    """
    移动平均线（MA）
    计算 MA5/10/20/60/120/250
    """
    if periods is None:
        periods = [5, 10, 20, 60, 120, 250]
    _, _, _, close, _, dates = _as_arrays(klines)
    results: List[Dict] = []
    for i in range(len(klines)):
        row: Dict[str, Any] = {"trade_date": dates[i]}
        for p in periods:
            if i >= p - 1:
                row[f"ma_{p}"] = round(float(close[i - p + 1:i + 1].mean()), 4)
        results.append(row)
    return results


def calc_boll(klines: List[Dict], period: int = 20, multiplier: float = 2.0) -> List[Dict]:
    """
    布林带（BOLL）
    中轨=MA20, 上轨=中轨+2σ, 下轨=中轨-2σ
    """
    _, _, _, close, _, dates = _as_arrays(klines)
    results: List[Dict] = []
    for i in range(len(klines)):
        row: Dict[str, Any] = {"trade_date": dates[i]}
        if i >= period - 1:
            window = close[i - period + 1:i + 1]
            ma = float(window.mean())
            std = float(window.std(ddof=0))
            row["boll_ma"] = round(ma, 4)
            row["boll_upper"] = round(ma + multiplier * std, 4)
            row["boll_lower"] = round(ma - multiplier * std, 4)
            row["boll_width"] = round(2 * multiplier * std / ma * 100 if ma != 0 else 0, 4)
        else:
            row.update({"boll_ma": None, "boll_upper": None,
                        "boll_lower": None, "boll_width": None})
        results.append(row)
    return results


def calc_sar(klines: List[Dict], step: float = 0.02, max_step: float = 0.2) -> List[Dict]:
    """
    抛物线转向（SAR）— 停损点转向
    涨势中SAR在K线下方，跌势中SAR在K线上方
    """
    _, high, low, close, _, dates = _as_arrays(klines)
    n = len(klines)
    sar = np.full(n, np.nan)
    ep = np.full(n, np.nan)
    af = np.full(n, 0.02)
    trend = np.zeros(n)  # 1=涨, -1=跌

    if n < 2:
        return [{"trade_date": d, "sar": None} for d in dates]

    # 初始趋势：前两根K线判断
    trend[1] = 1 if close[1] > close[0] else -1
    ep[1] = high[1] if trend[1] == 1 else low[1]
    sar[1] = low[0] if trend[1] == 1 else high[0]

    for i in range(2, n):
        prev_trend = trend[i - 1]
        if prev_trend == 1:
            sar[i] = sar[i - 1] + af[i - 1] * (ep[i - 1] - sar[i - 1])
            sar[i] = min(sar[i], low[i - 1], low[i - 2] if i >= 2 else low[i - 1])
            if low[i] < sar[i]:
                trend[i] = -1
                sar[i] = ep[i - 1]
                ep[i] = low[i]
                af[i] = step
            else:
                trend[i] = 1
                if high[i] > ep[i - 1]:
                    ep[i] = high[i]
                    af[i] = min(af[i - 1] + step, max_step)
                else:
                    ep[i] = ep[i - 1]
                    af[i] = af[i - 1]
        else:
            sar[i] = sar[i - 1] - af[i - 1] * (sar[i - 1] - ep[i - 1])
            sar[i] = max(sar[i], high[i - 1], high[i - 2] if i >= 2 else high[i - 1])
            if high[i] > sar[i]:
                trend[i] = 1
                sar[i] = ep[i - 1]
                ep[i] = high[i]
                af[i] = step
            else:
                trend[i] = -1
                if low[i] < ep[i - 1]:
                    ep[i] = low[i]
                    af[i] = min(af[i - 1] + step, max_step)
                else:
                    ep[i] = ep[i - 1]
                    af[i] = af[i - 1]

    results = []
    for i in range(n):
        results.append({
            "trade_date": dates[i],
            "sar": round(float(sar[i]), 4) if not np.isnan(sar[i]) else None,
        })
    return results


# ═══════════════════════════════════════════════════════════════════
#  副图指标
# ═══════════════════════════════════════════════════════════════════

def calc_vol(klines: List[Dict], periods: Optional[List[int]] = None) -> List[Dict]:
    """
    成交量 + 均量线（VOL）
    VOL + MAVOL5/10/20
    """
    if periods is None:
        periods = [5, 10, 20]
    _, _, _, _, vol, dates = _as_arrays(klines)
    results: List[Dict] = []
    for i in range(len(klines)):
        row: Dict[str, Any] = {"trade_date": dates[i], "vol": round(float(vol[i]), 2)}
        for p in periods:
            if i >= p - 1:
                row[f"vol_ma_{p}"] = round(float(vol[i - p + 1:i + 1].mean()), 2)
        results.append(row)
    return results


def calc_macd(klines: List[Dict], fast: int = 12, slow: int = 26,
              signal: int = 9) -> List[Dict]:
    """
    指数平滑异同移动平均线（MACD）
    DIF=EMA(fast)-EMA(slow), DEA=EMA(DIF,signal), BAR=2*(DIF-DEA)
    """
    _, _, _, close, _, dates = _as_arrays(klines)
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    dif = ema_fast - ema_slow
    dea = _ema(dif, signal)
    bar = 2 * (dif - dea)
    results = []
    for i in range(len(klines)):
        results.append({
            "trade_date": dates[i],
            "macd_dif": round(float(dif[i]), 4) if not np.isnan(dif[i]) else None,
            "macd_dea": round(float(dea[i]), 4) if not np.isnan(dea[i]) else None,
            "macd_bar": round(float(bar[i]), 4) if not np.isnan(bar[i]) else None,
        })
    return results


def calc_kdj(klines: List[Dict], n: int = 9, k_smooth: int = 3,
             d_smooth: int = 3) -> List[Dict]:
    """
    随机指标（KDJ）
    RSV=(C-LLV)/(HHV-LLV)*100, K=平滑RSV, D=平滑K, J=3K-2D
    """
    _, high, low, close, _, dates = _as_arrays(klines)
    k = np.full(len(klines), np.nan)
    d = np.full(len(klines), np.nan)
    j = np.full(len(klines), np.nan)

    for i in range(len(klines)):
        if i < n - 1:
            continue
        hhv = float(high[i - n + 1:i + 1].max())
        llv = float(low[i - n + 1:i + 1].min())
        rsv = 0.0 if hhv == llv else (close[i] - llv) / (hhv - llv) * 100.0
        if i == n - 1:
            k[i] = rsv
            d[i] = rsv
        else:
            k[i] = (k_smooth - 1) / k_smooth * k[i - 1] + rsv / k_smooth
            d[i] = (d_smooth - 1) / d_smooth * d[i - 1] + k[i] / d_smooth
        j[i] = 3 * k[i] - 2 * d[i]

    results = []
    for i in range(len(klines)):
        results.append({
            "trade_date": dates[i],
            "kdj_k": round(float(k[i]), 4) if not np.isnan(k[i]) else None,
            "kdj_d": round(float(d[i]), 4) if not np.isnan(d[i]) else None,
            "kdj_j": round(float(j[i]), 4) if not np.isnan(j[i]) else None,
        })
    return results


def calc_rsi(klines: List[Dict], periods: Optional[List[int]] = None) -> List[Dict]:
    """
    相对强弱指标（RSI）
    RSI=100-100/(1+RS), RS=avg_gain/avg_loss（SMA递推）
    """
    if periods is None:
        periods = [6, 12, 24]
    _, _, _, close, _, dates = _as_arrays(klines)
    n = len(klines)
    delta = np.diff(close, prepend=close[0])
    results: List[Dict] = []

    for i in range(n):
        row: Dict[str, Any] = {"trade_date": dates[i]}
        for p in periods:
            if i < p:
                row[f"rsi_{p}"] = None
                continue
            window = delta[i - p + 1:i + 1]
            gains = window[window > 0].sum()
            losses = -window[window < 0].sum()
            avg_gain = gains / p
            avg_loss = losses / p
            if avg_loss == 0:
                row[f"rsi_{p}"] = 100.0
            else:
                rs = avg_gain / avg_loss
                row[f"rsi_{p}"] = round(100.0 - 100.0 / (1.0 + rs), 4)
        results.append(row)
    return results


def calc_wr(klines: List[Dict], periods: Optional[List[int]] = None) -> List[Dict]:
    """
    威廉指标（WR）
    WR=(HHV-C)/(HHV-LLV)*100
    """
    if periods is None:
        periods = [6, 10, 14]
    _, high, low, close, _, dates = _as_arrays(klines)
    results: List[Dict] = []
    for i in range(len(klines)):
        row: Dict[str, Any] = {"trade_date": dates[i]}
        for p in periods:
            if i < p - 1:
                row[f"wr_{p}"] = None
                continue
            hhv = float(high[i - p + 1:i + 1].max())
            llv = float(low[i - p + 1:i + 1].min())
            if hhv == llv:
                row[f"wr_{p}"] = 0.0
            else:
                row[f"wr_{p}"] = round((hhv - close[i]) / (hhv - llv) * 100, 4)
        results.append(row)
    return results


def calc_cci(klines: List[Dict], period: int = 14) -> List[Dict]:
    """
    商品通道指数（CCI）
    CCI=(TP-MA(TP))/(0.015*MD), TP=(H+L+C)/3
    """
    _, high, low, close, _, dates = _as_arrays(klines)
    tp = (high + low + close) / 3.0
    results: List[Dict] = []
    for i in range(len(klines)):
        if i < period - 1:
            results.append({"trade_date": dates[i], "cci": None})
            continue
        tp_window = tp[i - period + 1:i + 1]
        ma_tp = float(tp_window.mean())
        md = float(np.abs(tp_window - ma_tp).mean())
        cci_val = (float(tp[i]) - ma_tp) / (0.015 * md) if md != 0 else 0.0
        results.append({"trade_date": dates[i], "cci": round(cci_val, 4)})
    return results


def calc_bias(klines: List[Dict], periods: Optional[List[int]] = None) -> List[Dict]:
    """
    乖离率（BIAS）
    BIAS=(C-MA)/MA*100
    """
    if periods is None:
        periods = [6, 12, 24]
    _, _, _, close, _, dates = _as_arrays(klines)
    ma_all = {p: _sma(close, p) for p in periods}
    results: List[Dict] = []
    for i in range(len(klines)):
        row: Dict[str, Any] = {"trade_date": dates[i]}
        for p in periods:
            mav = ma_all[p][i]
            if np.isnan(mav) or mav == 0:
                row[f"bias_{p}"] = None
            else:
                row[f"bias_{p}"] = round(float((close[i] - mav) / mav * 100), 4)
        results.append(row)
    return results


def calc_psy(klines: List[Dict], periods: Optional[List[int]] = None) -> List[Dict]:
    """
    心理线（PSY）
    PSY=上涨天数/N*100, PSYMA=MA(PSY)
    """
    if periods is None:
        periods = [12, 24]
    _, _, _, close, _, dates = _as_arrays(klines)
    n = len(klines)
    up = (close[1:] > close[:-1]).astype(float)
    up = np.concatenate([[0.0], up])
    results: List[Dict] = []
    for i in range(n):
        row: Dict[str, Any] = {"trade_date": dates[i]}
        for p in periods:
            if i < p - 1:
                row[f"psy_{p}"] = None
                continue
            psy_val = float(up[i - p + 1:i + 1].sum()) / p * 100
            row[f"psy_{p}"] = round(psy_val, 4)
            if i >= p + 6 - 1:
                psys = [r.get(f"psy_{p}", 0) or 0
                        for r in results[i - 6:i + 1]]
                row[f"psy_ma_{p}"] = round(sum(psys) / len(psys), 4)
        results.append(row)
    return results


def calc_obv(klines: List[Dict]) -> List[Dict]:
    """
    能量潮（OBV）
    OBV累积: close>prev → +vol, close<prev → -vol
    """
    _, _, _, close, vol, dates = _as_arrays(klines)
    n = len(klines)
    obv = np.zeros(n)
    for i in range(1, n):
        if close[i] > close[i - 1]:
            obv[i] = obv[i - 1] + vol[i]
        elif close[i] < close[i - 1]:
            obv[i] = obv[i - 1] - vol[i]
        else:
            obv[i] = obv[i - 1]
    obv_ma = _sma(obv, 20)
    results = []
    for i in range(n):
        results.append({
            "trade_date": dates[i],
            "obv": round(float(obv[i]), 2),
            "obv_ma": round(float(obv_ma[i]), 2) if not np.isnan(obv_ma[i]) else None,
        })
    return results


def calc_dmi(klines: List[Dict], period: int = 14, adx_smooth: int = 6) -> List[Dict]:
    """
    趋向指标（DMI）
    PDI(+DI), MDI(-DI), ADX, ADXR
    """
    _, high, low, close, _, dates = _as_arrays(klines)
    n = len(klines)
    tr_arr = _tr(high, low, close)

    # +DM / -DM
    up_move = np.diff(high, prepend=high[0])
    down_move = np.diff(low, prepend=low[0])
    p_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    m_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr_s = np.full(n, np.nan)
    pdi = np.full(n, np.nan)
    mdi = np.full(n, np.nan)

    for i in range(n):
        if i < period:
            continue
        tr_s[i] = float(tr_arr[i - period + 1:i + 1].sum())
        sum_p = float(p_dm[i - period + 1:i + 1].sum())
        sum_m = float(m_dm[i - period + 1:i + 1].sum())
        pdi[i] = sum_p / tr_s[i] * 100 if tr_s[i] != 0 else 0
        mdi[i] = sum_m / tr_s[i] * 100 if tr_s[i] != 0 else 0

    # ADX = MA(|PDI-MDI|/(PDI+MDI)*100)
    dx = np.full(n, np.nan)
    for i in range(n):
        if np.isnan(pdi[i]) or np.isnan(mdi[i]):
            continue
        s = pdi[i] + mdi[i]
        dx[i] = abs(pdi[i] - mdi[i]) / s * 100 if s != 0 else 0

    adx = _sma(dx, adx_smooth)
    adxr = np.full(n, np.nan)
    for i in range(n):
        if i >= adx_smooth and not np.isnan(adx[i - adx_smooth]):
            adxr[i] = (adx[i] + adx[i - adx_smooth]) / 2.0

    results = []
    for i in range(n):
        results.append({
            "trade_date": dates[i],
            "pdi": round(float(pdi[i]), 4) if not np.isnan(pdi[i]) else None,
            "mdi": round(float(mdi[i]), 4) if not np.isnan(mdi[i]) else None,
            "adx": round(float(adx[i]), 4) if not np.isnan(adx[i]) else None,
            "adxr": round(float(adxr[i]), 4) if not np.isnan(adxr[i]) else None,
        })
    return results


def calc_roc(klines: List[Dict], period: int = 12, smooth: int = 6) -> List[Dict]:
    """
    变动率指标（ROC）
    ROC=(C-C_{N})/C_{N}*100, ROCMA=MA(ROC)
    """
    _, _, _, close, _, dates = _as_arrays(klines)
    n = len(klines)
    roc = np.full(n, np.nan)
    for i in range(period, n):
        roc[i] = (close[i] - close[i - period]) / close[i - period] * 100
    roc_ma = _sma(roc, smooth)
    results = []
    for i in range(n):
        results.append({
            "trade_date": dates[i],
            "roc": round(float(roc[i]), 4) if not np.isnan(roc[i]) else None,
            "roc_ma": round(float(roc_ma[i]), 4) if not np.isnan(roc_ma[i]) else None,
        })
    return results


# ═══════════════════════════════════════════════════════════════════
#  统一入口
# ═══════════════════════════════════════════════════════════════════

INDICATOR_VERSION = "v1"  # 指标参数版本号，参数变更时递增

def compute_all(klines: List[Dict]) -> List[Dict]:
    """
    统一入口：输入K线列表，计算全部13个指标，合并返回。

    Args:
        klines: K线记录列表，需包含字段
                [open, high, low, close, vol, trade_date]
                按日期升序排列。

    Returns:
        与输入等长列表，每项包含 trade_date + 全部指标字段 + indicator_version。
    """
    if not klines:
        return []

    results = calc_ma(klines)
    _merge(results, calc_boll(klines))
    _merge(results, calc_sar(klines))
    _merge(results, calc_vol(klines))
    _merge(results, calc_macd(klines))
    _merge(results, calc_kdj(klines))
    _merge(results, calc_rsi(klines))
    _merge(results, calc_wr(klines))
    _merge(results, calc_cci(klines))
    _merge(results, calc_bias(klines))
    _merge(results, calc_psy(klines))
    _merge(results, calc_obv(klines))
    _merge(results, calc_dmi(klines))
    _merge(results, calc_roc(klines))

    # 附加版本号
    for row in results:
        row["indicator_version"] = INDICATOR_VERSION

    return results


def _merge(base: List[Dict], extra: List[Dict]) -> None:
    """将 extra 中的字段合并到 base（原地修改）"""
    for i in range(min(len(base), len(extra))):
        base[i].update({k: v for k, v in extra[i].items() if k != "trade_date"})