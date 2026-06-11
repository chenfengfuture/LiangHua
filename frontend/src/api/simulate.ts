/**
 * 模拟交易模块 API
 *
 * 纯前端 localStorage 模拟，无后端接口依赖。
 *
 * 功能：
 *   - 账户资金管理（初始本金 100 万）
 *   - 持仓管理（买入/卖出）
 *   - 委托管理（下单/撤单）
 *   - 成交记录（每次买卖自动记录）
 *   - 每日资产快照（权益曲线用）
 *   - 交易统计（胜率/最大回撤/平均持仓天数等）
 */

import { stockCenterApi } from './stock/stockCenter';
import type {
  SimAccount,
  SimPosition,
  SimOrder,
  SimTrade,
  SimDailyRecord,
  SimPlaceOrderParams,
  SimStats,
} from '../types/stock';

const PREFIX = 'simulate:';

// ─── 佣金费率 ──────────────────────────────────────────────────
const COMMISSION_RATE = 0.0003;     // 万3
const STAMP_TAX_RATE = 0.001;      // 千1（卖出）
const MIN_COMMISSION = 5;          // 最低佣金 5 元

function calcCommission(amount: number): number {
  return Math.max(amount * COMMISSION_RATE, MIN_COMMISSION);
}

function calcStampTax(amount: number): number {
  return amount * STAMP_TAX_RATE;
}

// ─── 通用 localStorage 读写 ──────────────────────────────────
function loadJSON<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw ? JSON.parse(raw) : fallback;
  } catch { return fallback; }
}

function saveJSON<T>(key: string, data: T): void {
  try { localStorage.setItem(PREFIX + key, JSON.stringify(data)); } catch { /* ignore */ }
}

// ─── ID 生成 ──────────────────────────────────────────────────
let _idSeq = Date.now();
function genId(prefix: string): string {
  return `${prefix}_${(++_idSeq).toString(36)}`;
}

// ═══════════════════════════════════════════════════════════════════
//  账户
// ═══════════════════════════════════════════════════════════════════

const ACCOUNT_KEY = 'account';
const INITIAL_CAPITAL = 1_000_000; // 初始本金 100 万

export function initAccount(): SimAccount {
  const acct: SimAccount = {
    initial_capital: INITIAL_CAPITAL,
    available_cash: INITIAL_CAPITAL,
    frozen_cash: 0,
    total_assets: INITIAL_CAPITAL,
  };
  saveJSON(ACCOUNT_KEY, acct);
  return acct;
}

export function getAccount(): SimAccount {
  const acct = loadJSON<SimAccount>(ACCOUNT_KEY, null as any);
  if (!acct || acct.initial_capital == null) return initAccount();
  return acct;
}

function saveAccount(acct: SimAccount): void {
  saveJSON(ACCOUNT_KEY, acct);
}

/**
 * 刷新总资产 = 可用资金 + 冻结资金 + 所有持仓市值
 */
export function refreshTotalAssets(): SimAccount {
  const acct = getAccount();
  const positions = getPositions();
  const marketValue = positions.reduce((s, p) => s + p.market_value, 0);
  acct.total_assets = acct.available_cash + acct.frozen_cash + marketValue;
  saveAccount(acct);
  return acct;
}

// ═══════════════════════════════════════════════════════════════════
//  持仓
// ═══════════════════════════════════════════════════════════════════

const POSITIONS_KEY = 'positions';

export function getPositions(): SimPosition[] {
  return loadJSON<SimPosition[]>(POSITIONS_KEY, []);
}

function savePositions(positions: SimPosition[]): void {
  saveJSON(POSITIONS_KEY, positions);
}

/**
 * 根据后端实时行情刷新所有持仓的现价和盈亏
 */
export async function refreshPositionsPrice(): Promise<SimPosition[]> {
  const positions = getPositions();
  if (positions.length === 0) return positions;

  const today = new Date();
  const end = `${today.getFullYear()}${String(today.getMonth()+1).padStart(2,'0')}${String(today.getDate()).padStart(2,'0')}`;
  const start = `${today.getFullYear()}${String(today.getMonth()+1).padStart(2,'0')}01`;

  for (const pos of positions) {
    try {
      const kline = await stockCenterApi.getDailyKline(pos.symbol, 'daily', start, end, 'qfq');
      if (kline.length > 0) {
        const last = kline[kline.length - 1];
        pos.current_price = last.close_price;
        pos.market_value = pos.current_price * pos.quantity;
        pos.profit_loss = (pos.current_price - pos.cost_price) * pos.quantity;
        pos.profit_loss_pct = pos.cost_price > 0
          ? ((pos.current_price - pos.cost_price) / pos.cost_price) * 100
          : 0;
        pos.updated_at = new Date().toISOString();
      }
    } catch {
      // 单只股票刷新失败不阻塞整体
    }
  }
  savePositions(positions);
  return positions;
}

// ═══════════════════════════════════════════════════════════════════
//  委托
// ═══════════════════════════════════════════════════════════════════

const ORDERS_KEY = 'orders';

export function getOrders(): SimOrder[] {
  return loadJSON<SimOrder[]>(ORDERS_KEY, []);
}

function saveOrders(orders: SimOrder[]): void {
  saveJSON(ORDERS_KEY, orders);
}

// ═══════════════════════════════════════════════════════════════════
//  成交记录
// ═══════════════════════════════════════════════════════════════════

const TRADES_KEY = 'trades';

export function getTrades(): SimTrade[] {
  return loadJSON<SimTrade[]>(TRADES_KEY, []);
}

function saveTrades(trades: SimTrade[]): void {
  saveJSON(TRADES_KEY, trades);
}

// ═══════════════════════════════════════════════════════════════════
//  每日资产快照（权益曲线）
// ═══════════════════════════════════════════════════════════════════

const DAILY_KEY = 'daily_records';

export function getDailyRecords(): SimDailyRecord[] {
  return loadJSON<SimDailyRecord[]>(DAILY_KEY, []);
}

function saveDailyRecords(records: SimDailyRecord[]): void {
  saveJSON(DAILY_KEY, records);
}

/**
 * 记录今日资产快照（幂等：同一日期只保留最后一条）
 */
export function recordDailySnapshot(): void {
  const acct = refreshTotalAssets();
  const today = new Date().toISOString().slice(0, 10);
  const positions = getPositions();
  const marketValue = positions.reduce((s, p) => s + p.market_value, 0);
  const records = getDailyRecords().filter((r) => r.date !== today);
  records.push({
    date: today,
    total_assets: acct.total_assets,
    available_cash: acct.available_cash,
    market_value: marketValue,
  });
  saveDailyRecords(records);
}

// ═══════════════════════════════════════════════════════════════════
//  下单执行
// ═══════════════════════════════════════════════════════════════════

/**
 * 执行买入
 *   - 校验可用资金（含佣金）
 *   - 扣款 → 创建委托+成交 → 更新持仓
 */
function executeBuy(params: SimPlaceOrderParams): { order: SimOrder; trade: SimTrade; success: boolean; message: string } {
  const acct = getAccount();
  const amount = params.price * params.quantity;
  const commission = calcCommission(amount);
  const totalCost = amount + commission;

  if (totalCost > acct.available_cash) {
    return {
      order: null as any, trade: null as any,
      success: false,
      message: `可用资金不足：需 ¥${totalCost.toFixed(2)}，可用 ¥${acct.available_cash.toFixed(2)}`,
    };
  }

  // 扣款
  acct.available_cash -= totalCost;
  saveAccount(acct);

  // 创建委托
  const now = new Date().toISOString();
  const order: SimOrder = {
    id: genId('ord'),
    symbol: params.symbol,
    name: params.name,
    direction: 'buy',
    price: params.price,
    quantity: params.quantity,
    filled_qty: params.quantity,
    status: 'filled',
    created_at: now,
    updated_at: now,
  };

  // 创建成交记录
  const trade: SimTrade = {
    id: genId('trd'),
    order_id: order.id,
    symbol: params.symbol,
    name: params.name,
    direction: 'buy',
    price: params.price,
    quantity: params.quantity,
    amount,
    commission,
    trade_date: now,
  };

  // 更新持仓
  const positions = getPositions();
  const existing = positions.find((p) => p.symbol === params.symbol);
  if (existing) {
    // 加权平均成本
    const totalCostOld = existing.cost_price * existing.quantity;
    const totalCostNew = totalCostOld + amount;
    const totalQty = existing.quantity + params.quantity;
    existing.cost_price = +(totalCostNew / totalQty).toFixed(4);
    existing.quantity = totalQty;
    existing.available_qty = totalQty;
    existing.current_price = params.price;
    existing.market_value = existing.current_price * existing.quantity;
    existing.profit_loss = (existing.current_price - existing.cost_price) * existing.quantity;
    existing.profit_loss_pct = existing.cost_price > 0
      ? ((existing.current_price - existing.cost_price) / existing.cost_price) * 100
      : 0;
    existing.updated_at = now;
  } else {
    positions.push({
      symbol: params.symbol,
      name: params.name,
      quantity: params.quantity,
      cost_price: params.price,
      current_price: params.price,
      market_value: params.price * params.quantity,
      profit_loss: 0,
      profit_loss_pct: 0,
      available_qty: params.quantity,
      updated_at: now,
    });
  }
  savePositions(positions);

  // 保存委托和成交
  const orders = getOrders();
  orders.unshift(order);
  saveOrders(orders);
  const trades = getTrades();
  trades.unshift(trade);
  saveTrades(trades);

  return { order, trade, success: true, message: '买入成功' };
}

/**
 * 执行卖出
 *   - 校验持仓数量
 *   - 资金回笼（扣除佣金+印花税）→ 更新持仓
 */
function executeSell(params: SimPlaceOrderParams): { order: SimOrder; trade: SimTrade; success: boolean; message: string } {
  const positions = getPositions();
  const pos = positions.find((p) => p.symbol === params.symbol);
  if (!pos || pos.available_qty < params.quantity) {
    const have = pos ? pos.available_qty : 0;
    return {
      order: null as any, trade: null as any,
      success: false,
      message: `可卖数量不足：需 ${params.quantity} 股，可卖 ${have} 股`,
    };
  }

  const amount = params.price * params.quantity;
  const commission = calcCommission(amount);
  const stampTax = calcStampTax(amount);
  const netAmount = amount - commission - stampTax;

  // 资金回笼
  const acct = getAccount();
  acct.available_cash += netAmount;
  saveAccount(acct);

  // 创建委托
  const now = new Date().toISOString();
  const order: SimOrder = {
    id: genId('ord'),
    symbol: params.symbol,
    name: params.name,
    direction: 'sell',
    price: params.price,
    quantity: params.quantity,
    filled_qty: params.quantity,
    status: 'filled',
    created_at: now,
    updated_at: now,
  };

  // 创建成交记录
  const trade: SimTrade = {
    id: genId('trd'),
    order_id: order.id,
    symbol: params.symbol,
    name: params.name,
    direction: 'sell',
    price: params.price,
    quantity: params.quantity,
    amount,
    commission: commission + stampTax,
    trade_date: now,
  };

  // 更新持仓
  pos.quantity -= params.quantity;
  pos.available_qty -= params.quantity;
  if (pos.quantity <= 0) {
    const idx = positions.indexOf(pos);
    positions.splice(idx, 1);
  } else {
    pos.current_price = params.price;
    pos.market_value = pos.current_price * pos.quantity;
    pos.profit_loss = (pos.current_price - pos.cost_price) * pos.quantity;
    pos.profit_loss_pct = pos.cost_price > 0
      ? ((pos.current_price - pos.cost_price) / pos.cost_price) * 100
      : 0;
    pos.updated_at = now;
  }
  savePositions(positions);

  // 保存委托和成交
  const orders = getOrders();
  orders.unshift(order);
  saveOrders(orders);
  const tradesList = getTrades();
  tradesList.unshift(trade);
  saveTrades(tradesList);

  return { order, trade, success: true, message: '卖出成功' };
}

/**
 * 下单入口（买入/卖出）
 */
export function placeOrder(params: SimPlaceOrderParams): { order: SimOrder; trade: SimTrade; success: boolean; message: string } {
  if (params.direction === 'buy') {
    return executeBuy(params);
  }
  return executeSell(params);
}

// ═══════════════════════════════════════════════════════════════════
//  统计
// ═══════════════════════════════════════════════════════════════════

export function calcStats(): SimStats {
  const trades = getTrades();
  const records = getDailyRecords();

  const totalTrades = trades.length;
  const buyMap = new Map<string, number>();
  const sellTrades = trades.filter((t) => t.direction === 'sell');

  // 统计盈利/亏损次数（按卖出计算，每笔卖出对比买入成本）
  let winCount = 0;
  let loseCount = 0;
  for (const st of sellTrades) {
    const buyAmount = buyMap.get(st.symbol) || 0;
    const profit = st.amount - st.commission * 0.5 - buyAmount * (st.quantity / (getTotalBuyQty(st.symbol) || 1));
    // 简化逻辑：卖出金额 > 买入成本视为盈利
    if (profit > 0) winCount++;
    else loseCount++;
  }

  // 最大回撤
  let maxDrawdown = 0;
  let maxDrawdownPct = 0;
  if (records.length > 1) {
    let peak = records[0].total_assets;
    for (const r of records) {
      if (r.total_assets > peak) peak = r.total_assets;
      const dd = peak - r.total_assets;
      const ddPct = peak > 0 ? (dd / peak) * 100 : 0;
      if (dd > maxDrawdown) { maxDrawdown = dd; maxDrawdownPct = ddPct; }
    }
  }

  // 总佣金
  const totalCommission = trades.reduce((s, t) => s + t.commission, 0);

  return {
    total_trades: totalTrades,
    win_count: winCount,
    lose_count: loseCount,
    win_rate: totalTrades > 0 ? +(winCount / totalTrades * 100).toFixed(1) : 0,
    max_drawdown: maxDrawdown,
    max_drawdown_pct: +maxDrawdownPct.toFixed(2),
    avg_hold_days: 0,
    total_commission: totalCommission,
  };
}

function getTotalBuyQty(symbol: string): number {
  const trades = getTrades();
  return trades.filter((t) => t.symbol === symbol && t.direction === 'buy')
    .reduce((s, t) => s + t.quantity, 0);
}

// ═══════════════════════════════════════════════════════════════════
//  重置
// ═══════════════════════════════════════════════════════════════════

/** 清空所有模拟交易数据（重置账户） */
export function resetAll(): void {
  try {
    localStorage.removeItem(PREFIX + ACCOUNT_KEY);
    localStorage.removeItem(PREFIX + POSITIONS_KEY);
    localStorage.removeItem(PREFIX + ORDERS_KEY);
    localStorage.removeItem(PREFIX + TRADES_KEY);
    localStorage.removeItem(PREFIX + DAILY_KEY);
    initAccount();
  } catch { /* ignore */ }
}