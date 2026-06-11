/**
 * API 层通用工具函数
 */

/**
 * 安全提取 data 字段（兼容直接返回数组/对象的情况）
 *
 * 后端部分接口（lhb-detail / lhb-jgmmtj-em / lhb-stock-statistic-em /
 * traderstatistic-em / lh-yyh-most）在只查到一条记录时返回 dict 而非 list，
 * 导致前端 Table.dataSource.some 报错崩溃。unwrap 会自动将单对象包成数组。
 */
export function unwrap<T>(resp: any, fallback: T): T {
  if (resp == null) return fallback;
  if (resp?.success === false) return fallback;
  const raw = resp?.data !== undefined ? resp.data : resp;
  // 后端返回 {success:true, data:null} 时，raw 为 null，此时必须返回 fallback
  if (raw == null) return fallback;
  // 期望数组但后端返回了单对象 → 包装为 [对象]
  if (Array.isArray(fallback) && raw != null && !Array.isArray(raw) && typeof raw === 'object') {
    return [raw] as unknown as T;
  }
  return raw as T;
}