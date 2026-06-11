/**
 * 日级缓存工具：基于 localStorage，按当天日期（YYYY-MM-DD）隔离。
 *
 * 特性：
 *   - 跨天访问时（日期 key 不匹配），自动失效并清除旧 key
 *   - 可选 TTL：用于盘中实时数据（如即时资金流、涨停池），过期后即使在同一天也会重取
 *   - cacheKey 自动按可选维度参数序列化（如 symbol、period、date）
 *
 * 用法：
 *   const cached = readDailyCache<T>('dashboard:all');
 *   writeDailyCache('dashboard:all', data);
 *
 *   // 带 60 秒 TTL（盘中频繁变化数据）
 *   const cached = readDailyCache<T>('fund:immediate', { ttlMs: 60_000 });
 *
 *   // 维度参数（如不同 symbol、不同 date 视为不同缓存键）
 *   const k = makeKey('kline:industry', { symbol: 'sh600000', period: 'daily' });
 */

const PREFIX = 'dailyCache:';

function todayKey(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

interface CachePayload<T> {
  date: string; // 缓存写入时的本地日期
  ts: number;   // 时间戳（用于 TTL 判断和诊断）
  data: T;
}

interface ReadOpts {
  /** 短期 TTL（毫秒），适用于盘中实时数据。未指定时只按"当天"判断 */
  ttlMs?: number;
}

interface TTLCachePayload<T> {
  ts: number;
  data: T;
}

const TTL_PREFIX = 'ttlCache:';

/** 拼接 cacheKey + 维度参数（dimensions 字典序），同一组参数总能映射到同一 key */
export function makeKey(base: string, dims?: Record<string, string | number | undefined | null>): string {
  if (!dims) return base;
  const parts = Object.keys(dims)
    .sort()
    .filter((k) => dims[k] !== undefined && dims[k] !== null && dims[k] !== '')
    .map((k) => `${k}=${dims[k]}`);
  return parts.length ? `${base}?${parts.join('&')}` : base;
}

/** 读取缓存：当天 + 未过 TTL（如指定）才返回，否则返回 null（顺便清除该 key） */
export function readDailyCache<T = unknown>(key: string, opts?: ReadOpts): T | null {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    if (!raw) return null;
    const payload: CachePayload<T> = JSON.parse(raw);
    if (!payload || payload.date !== todayKey()) {
      localStorage.removeItem(PREFIX + key);
      return null;
    }
    if (opts?.ttlMs && Date.now() - (payload.ts || 0) > opts.ttlMs) {
      // 已过 TTL → 当天内重取，不删除 key（写入时会覆盖）
      return null;
    }
    return payload.data;
  } catch {
    return null;
  }
}

/** 写入缓存（绑定今天日期） */
export function writeDailyCache<T = unknown>(key: string, data: T): void {
  try {
    const payload: CachePayload<T> = { date: todayKey(), ts: Date.now(), data };
    localStorage.setItem(PREFIX + key, JSON.stringify(payload));
  } catch {
    // 写入失败（如配额满）静默忽略
  }
}

/** 通用 TTL 缓存读取：只按写入时间 + TTL 判断，不受自然日限制 */
export function readTTLCache<T = unknown>(key: string, ttlMs: number): T | null {
  try {
    const raw = localStorage.getItem(TTL_PREFIX + key);
    if (!raw) return null;
    const payload: TTLCachePayload<T> = JSON.parse(raw);
    if (!payload || Date.now() - (payload.ts || 0) > ttlMs) {
      localStorage.removeItem(TTL_PREFIX + key);
      return null;
    }
    return payload.data;
  } catch {
    return null;
  }
}

/** 通用 TTL 缓存写入 */
export function writeTTLCache<T = unknown>(key: string, data: T): void {
  try {
    const payload: TTLCachePayload<T> = { ts: Date.now(), data };
    localStorage.setItem(TTL_PREFIX + key, JSON.stringify(payload));
  } catch {
    // 写入失败（如配额满）静默忽略
  }
}

/** 清除指定 key 的 TTL 缓存 */
export function clearTTLCache(key: string): void {
  try {
    localStorage.removeItem(TTL_PREFIX + key);
  } catch {
    // ignore
  }
}

/** 清除指定 key 的缓存 */
export function clearDailyCache(key: string): void {
  try {
    localStorage.removeItem(PREFIX + key);
  } catch {
    // ignore
  }
}

/** 按前缀批量清除（如 clearDailyCacheByPrefix('dashboard:')） */
export function clearDailyCacheByPrefix(prefix: string): void {
  try {
    const full = PREFIX + prefix;
    const toDelete: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith(full)) toDelete.push(k);
    }
    toDelete.forEach((k) => localStorage.removeItem(k));
  } catch {
    // ignore
  }
}

/** 清除所有过期（非今天）的 dailyCache key */
export function purgeExpiredDailyCache(): void {
  try {
    const today = todayKey();
    const toDelete: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (!k || !k.startsWith(PREFIX)) continue;
      try {
        const raw = localStorage.getItem(k);
        if (!raw) continue;
        const payload = JSON.parse(raw);
        if (!payload || payload.date !== today) toDelete.push(k);
      } catch {
        toDelete.push(k);
      }
    }
    toDelete.forEach((k) => localStorage.removeItem(k));
  } catch {
    // ignore
  }
}

/** 推荐 TTL 常量 */
export const TTL = {
  /** 实时盘中数据：60 秒 */
  REALTIME: 60_000,
  /** 短期：5 分钟（盘口异动、资金流向） */
  SHORT: 5 * 60_000,
  /** 中期：30 分钟（板块异动、个股榜单） */
  MEDIUM: 30 * 60_000,
  /** 半小时：逐笔/分笔成交缓存 */
  THIRTY_MINUTES: 30 * 60_000,
  /** 7天：日内K线/1分钟分时数据缓存 */
  SEVEN_DAYS: 7 * 24 * 60 * 60_000,
  /** 长期：当天有效（财报、月度统计、龙虎榜历史等） */
  DAY: undefined as number | undefined,
};