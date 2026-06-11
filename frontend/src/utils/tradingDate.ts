/**
 * 交易日工具
 *
 * A 股交易日规则：
 *   - 周一 ~ 周五（不含法定节假日）
 *   - 收盘后龙虎榜数据约 18:00 出，前端取 17:00 作为分界
 *
 * 默认日期计算规则（getDefaultTradingDate）：
 *   - 当前时间 >= 17:00 且当天是交易日 → 返回当天
 *   - 否则                          → 返回上一个交易日
 *
 * 注：本工具不感知中国法定节假日，仅按"工作日"近似处理。
 * 若需精确节假日支持，应由后端提供交易日历接口；前端这里做近似已足够覆盖龙虎榜默认日期需求。
 */

import dayjs, { Dayjs } from 'dayjs';

/** 龙虎榜数据出榜时间分界：当天 17:00 */
export const LHB_DATA_HOUR = 17;

/**
 * 判断 dayjs 是否是 A 股交易日（仅按工作日近似）
 * @param d 待判断日期
 * @returns true=交易日（周一~周五）
 */
export const isTradingDay = (d: Dayjs): boolean => {
  const wd = d.day(); // 0=Sun 6=Sat
  return wd >= 1 && wd <= 5;
};

/**
 * 取上一个交易日（不含传入日期本身）
 * @param from 起点日期
 * @returns 起点日期之前最近的一个交易日
 */
export const getPrevTradingDay = (from: Dayjs): Dayjs => {
  let d = from.subtract(1, 'day');
  while (!isTradingDay(d)) {
    d = d.subtract(1, 'day');
  }
  return d;
};

/**
 * 取默认查询日期（龙虎榜场景）
 *
 * 规则：
 *   1. 当天是交易日 + 当前时间 >= 17:00 → 返回当天
 *   2. 否则                          → 返回上一个交易日
 *
 * 示例（假设今天是 2026-05-29 周五）：
 *   - now = 2026-05-29 16:30 → 返回 2026-05-28 周四
 *   - now = 2026-05-29 17:00 → 返回 2026-05-29 周五
 *   - now = 2026-05-29 23:59 → 返回 2026-05-29 周五
 *   - now = 2026-05-31 周日   → 返回 2026-05-29 周五
 *   - now = 2026-06-01 周一 09:00 → 返回 2026-05-29 周五
 */
export const getDefaultTradingDate = (now: Dayjs = dayjs()): Dayjs => {
  const isToday17OrLater = now.hour() >= LHB_DATA_HOUR;
  if (isTradingDay(now) && isToday17OrLater) {
    return now.startOf('day');
  }
  return getPrevTradingDay(now).startOf('day');
};

/**
 * 取默认日期范围（龙虎榜场景）
 *
 * 终点：getDefaultTradingDate()
 * 起点：终点向前数 N 个自然日（默认 7 天，与原页面行为一致）
 *
 * 用于 RangePicker 的初始值。
 */
export const getDefaultTradingDateRange = (
  daysBack = 7,
  now: Dayjs = dayjs(),
): [Dayjs, Dayjs] => {
  const end = getDefaultTradingDate(now);
  const start = end.subtract(daysBack, 'day');
  return [start, end];
};
