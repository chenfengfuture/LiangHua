export type IndicatorValue = number | '-';

export interface OhlcPoint {
  open: number;
  close: number;
  low: number;
  high: number;
  volume: number;
}

export interface MacdResult {
  dif: IndicatorValue[];
  dea: IndicatorValue[];
  histogram: IndicatorValue[];
}

export interface KdjResult {
  k: IndicatorValue[];
  d: IndicatorValue[];
  j: IndicatorValue[];
}

export interface BollResult {
  middle: IndicatorValue[];
  upper: IndicatorValue[];
  lower: IndicatorValue[];
}

const round = (value: number, digits = 4): number => Number(value.toFixed(digits));

export const calcMA = (period: number, values: number[], digits = 2): IndicatorValue[] => {
  return values.map((_, index) => {
    if (index < period - 1) return '-';
    const slice = values.slice(index - period + 1, index + 1);
    const sum = slice.reduce((acc, value) => acc + value, 0);
    return round(sum / period, digits);
  });
};

export const calcEMA = (period: number, values: number[], digits = 4): number[] => {
  const alpha = 2 / (period + 1);
  return values.map((value, index) => {
    if (index === 0) return round(value, digits);
    return round(alpha * value + (1 - alpha) * values.slice(0, index).reduce((ema, current, currentIndex) => {
      if (currentIndex === 0) return current;
      return alpha * current + (1 - alpha) * ema;
    }, values[0]), digits);
  });
};

const calcEMAContinuous = (period: number, values: number[]): number[] => {
  const alpha = 2 / (period + 1);
  const result: number[] = [];
  values.forEach((value, index) => {
    result[index] = index === 0 ? value : alpha * value + (1 - alpha) * result[index - 1];
  });
  return result;
};

export const calcMACD = (closes: number[], fast = 12, slow = 26, signal = 9): MacdResult => {
  const emaFast = calcEMAContinuous(fast, closes);
  const emaSlow = calcEMAContinuous(slow, closes);
  const rawDif = closes.map((_, index) => emaFast[index] - emaSlow[index]);
  const rawDea = calcEMAContinuous(signal, rawDif);

  return {
    dif: rawDif.map((value, index) => (index < slow - 1 ? '-' : round(value, 4))),
    dea: rawDea.map((value, index) => (index < slow - 1 ? '-' : round(value, 4))),
    histogram: rawDif.map((value, index) => (index < slow - 1 ? '-' : round((value - rawDea[index]) * 2, 4))),
  };
};

export const calcKDJ = (points: OhlcPoint[], period = 9, kPeriod = 3, dPeriod = 3): KdjResult => {
  const k: IndicatorValue[] = [];
  const d: IndicatorValue[] = [];
  const j: IndicatorValue[] = [];
  const kWeight = 1 / kPeriod;
  const dWeight = 1 / dPeriod;

  points.forEach((point, index) => {
    if (index < period - 1) {
      k[index] = '-';
      d[index] = '-';
      j[index] = '-';
      return;
    }

    const window = points.slice(index - period + 1, index + 1);
    const highest = Math.max(...window.map((item) => item.high));
    const lowest = Math.min(...window.map((item) => item.low));
    const rsv = highest === lowest ? 50 : ((point.close - lowest) / (highest - lowest)) * 100;
    const prevK = index === period - 1 || k[index - 1] === '-' ? 50 : k[index - 1] as number;
    const prevD = index === period - 1 || d[index - 1] === '-' ? 50 : d[index - 1] as number;
    const curK = (1 - kWeight) * prevK + kWeight * rsv;
    const curD = (1 - dWeight) * prevD + dWeight * curK;

    k[index] = round(curK, 2);
    d[index] = round(curD, 2);
    j[index] = round(3 * curK - 2 * curD, 2);
  });

  return { k, d, j };
};

export const calcRSI = (closes: number[], period: number): IndicatorValue[] => {
  const result: IndicatorValue[] = [];
  let avgGain = 0;
  let avgLoss = 0;

  closes.forEach((close, index) => {
    if (index === 0) {
      result[index] = '-';
      return;
    }

    const change = close - closes[index - 1];
    const gain = Math.max(change, 0);
    const loss = Math.max(-change, 0);

    if (index < period) {
      avgGain += gain;
      avgLoss += loss;
      result[index] = '-';
      return;
    }

    if (index === period) {
      avgGain = (avgGain + gain) / period;
      avgLoss = (avgLoss + loss) / period;
    } else {
      avgGain = (avgGain * (period - 1) + gain) / period;
      avgLoss = (avgLoss * (period - 1) + loss) / period;
    }

    result[index] = avgLoss === 0 ? 100 : round(100 - 100 / (1 + avgGain / avgLoss), 2);
  });

  return result;
};

export const calcBOLL = (closes: number[], period = 20, multiplier = 2): BollResult => {
  const middle: IndicatorValue[] = [];
  const upper: IndicatorValue[] = [];
  const lower: IndicatorValue[] = [];

  closes.forEach((_, index) => {
    if (index < period - 1) {
      middle[index] = '-';
      upper[index] = '-';
      lower[index] = '-';
      return;
    }

    const window = closes.slice(index - period + 1, index + 1);
    const avg = window.reduce((acc, value) => acc + value, 0) / period;
    const variance = window.reduce((acc, value) => acc + (value - avg) ** 2, 0) / period;
    const std = Math.sqrt(variance);

    middle[index] = round(avg, 2);
    upper[index] = round(avg + multiplier * std, 2);
    lower[index] = round(avg - multiplier * std, 2);
  });

  return { middle, upper, lower };
};
