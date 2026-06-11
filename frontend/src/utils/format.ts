/**
 * 格式化工具函数
 *
 * 集中管理项目中所有的数据格式化逻辑：金额/百分比/数字/日期。
 */

/**
 * 安全转数字：后端 change_percent 等字段可能返回 string / number / null
 * 确保始终返回 number，无法转换时返回 fallback
 */
export function safeNum(v: string | number | null | undefined, fallback = 0): number {
  if (v == null) return fallback;
  if (typeof v === 'number') return isNaN(v) ? fallback : v;
  const n = parseFloat(String(v));
  return isNaN(n) ? fallback : n;
}

/**
 * 安全 toFixed：对可能为 string/number/null 的值调用 toFixed
 */
export function safeToFixed(v: string | number | null | undefined, digits = 2, fallback = '--'): string {
  const n = safeNum(v, NaN);
  return isNaN(n) ? fallback : n.toFixed(digits);
}

/**
 * 格式化金额：自动选择合适的单位（亿/万/元）
 * 用于 Dashboard、FundFlow 等页面
 */
export function fmtYi(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '--';
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿';
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + '万';
  return v.toFixed(2);
}

/**
 * 格式化金额-仅数值部分（不含单位）
 * 用于表格中的数值列
 */
export function fmtYiRaw(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '0.00';
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2);
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2);
  return v.toFixed(2);
}

/**
 * 格式化百分比
 */
export function fmtPercent(v: number | null | undefined, digits = 2): string {
  if (v == null || isNaN(v)) return '--';
  return (v >= 0 ? '+' : '') + v.toFixed(digits) + '%';
}

/**
 * 格式化数字：千分位加逗号
 */
export function fmtNumber(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '--';
  return v.toLocaleString();
}

/**
 * 格式化带符号的数字（用于涨跌显示）
 */
export function fmtSigned(v: number | null | undefined, digits = 2): string {
  if (v == null || isNaN(v)) return '--';
  return (v >= 0 ? '+' : '') + v.toFixed(digits);
}

/**
 * 成交量格式化（手 → 万手 / 亿手）
 */
export function fmtVolume(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '--';
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(1) + '万';
  return v.toFixed(0);
}

/**
 * 百分比文字颜色（A 股惯例：红涨绿跌）
 */
export function changeColor(v: number | null | undefined): string {
  if (v == null) return 'inherit';
  if (v > 0) return '#EF4444';
  if (v < 0) return '#10B981';
  return 'inherit';
}

/**
 * 截取字符串前 N 个字符
 */
export function truncate(s: string, maxLen: number): string {
  if (!s || s.length <= maxLen) return s;
  return s.slice(0, maxLen) + '...';
}