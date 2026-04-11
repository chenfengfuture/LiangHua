# 量华量化平台 — 后端 API 接口文档

> **服务地址**：`http://127.0.0.1:8001`  
> **框架**：FastAPI · Python 3.12  
> **数据库**：MySQL 8.0（lianghua）  
> **更新日期**：2026-04-06

---

## 目录

1. [通用说明](#通用说明)
2. [股票基础接口](#一股票基础接口)
3. [K 线接口](#二k-线接口)
4. [日内行情接口](#三日内行情接口)
5. [数据采集接口](#四数据采集接口)
6. [大模型接口（旧版）](#五大模型接口旧版--apillm)
7. [大模型接口（新版）](#六大模型接口新版--apiai)
8. [错误码说明](#错误码说明)

---

## 通用说明

### 请求格式

| 项目 | 说明 |
|------|------|
| Content-Type | `application/json`（POST 请求） |
| 字符编码 | UTF-8 |
| 日期格式 | `YYYY-MM-DD`（如 `2026-04-06`） |
| 日期时间格式 | `YYYY-MM-DD HH:MM:SS` |

### 通用响应结构

成功响应直接返回业务数据，错误响应格式如下：

```json
{
  "detail": "错误描述信息"
}
```

### 浮点数处理

- 所有价格/金额字段经 `safe_float()` 处理：`NaN`、`Inf` 一律返回 `null`
- 价格精度：保留 4 位小数
- 涨跌幅精度：保留 2 位小数

---

## 一、股票基础接口

### 1.1 服务健康检查

```
GET /
```

**响应示例**

```json
{
  "status": "ok",
  "message": "量华量化平台 API 运行中"
}
```

---

### 1.2 搜索股票

```
GET /api/stocks/search
```

**功能说明**：按股票代码前缀或名称模糊搜索，代码优先匹配前缀。

**请求参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `q` | string | ✅ | — | 搜索关键词，最短 1 个字符 |
| `limit` | integer | ❌ | 20 | 返回条数，范围 `[1, 100]` |

**请求示例**

```
GET /api/stocks/search?q=东方&limit=10
GET /api/stocks/search?q=300059
```

**响应示例**

```json
{
  "data": [
    {
      "symbol": "300059",
      "name": "东方财富",
      "market": "SZ",
      "list_date": "2010-03-19"
    }
  ],
  "total": 1
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `data` | array | 股票列表 |
| `data[].symbol` | string | 股票代码（6 位） |
| `data[].name` | string | 股票名称 |
| `data[].market` | string | 市场：`SH`（上交所）/ `SZ`（深交所）/ `BJ`（北交所） |
| `data[].list_date` | string | 上市日期 |
| `total` | integer | 返回总条数 |

---

### 1.3 股票列表（分页）

```
GET /api/stocks/list
```

**功能说明**：获取全量股票列表，支持按市场过滤和分页。

**请求参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | integer | ❌ | 1 | 页码，从 1 开始 |
| `page_size` | integer | ❌ | 50 | 每页条数，范围 `[1, 200]` |
| `market` | string | ❌ | null | 市场筛选：`SH` / `SZ` / `BJ`；不传则返回全市场 |

**请求示例**

```
GET /api/stocks/list?page=1&page_size=50&market=SH
```

**响应示例**

```json
{
  "data": [...],
  "total": 1600,
  "page": 1,
  "page_size": 50
}
```

---

### 1.4 单只股票基本信息

```
GET /api/stock/{symbol}/info
```

**功能说明**：获取单只股票基础信息，含最新收盘价和涨跌幅（从最近 3 年 K 线表中取最新 2 条计算）。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbol` | string | ✅ | 股票代码，如 `300059` |

**请求示例**

```
GET /api/stock/300059/info
```

**响应示例**

```json
{
  "symbol": "300059",
  "name": "东方财富",
  "market": "SZ",
  "list_date": "2010-03-19",
  "last_price": 16.88,
  "last_date": "2026-04-04",
  "change_pct": 2.35
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `last_price` | float\|null | 最新收盘价 |
| `last_date` | string\|null | 最新交易日 |
| `change_pct` | float\|null | 当日涨跌幅（%），红涨绿跌 |

**错误码**

| 状态码 | 说明 |
|--------|------|
| 404 | 股票代码不存在 |

---

### 1.5 市场概览

```
GET /api/market/overview
```

**功能说明**：统计最新交易日全市场涨跌平数量。

**请求参数**：无

**响应示例**

```json
{
  "date": "2026-04-04",
  "up": 2108,
  "down": 1650,
  "flat": 150,
  "total": 3908
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `date` | string | 统计交易日 |
| `up` | integer | 上涨股票数（含涨停） |
| `down` | integer | 下跌股票数（含跌停） |
| `flat` | integer | 平盘 / 数据不全 |
| `total` | integer | 统计股票总数 |

---

### 1.6 热门股票（成交额排行）

```
GET /api/stocks/hot
```

**功能说明**：按成交额从大到小排列，返回最热门的 N 只股票。

**请求参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `date_str` | string | ❌ | 最新交易日 | 指定日期，格式 `YYYY-MM-DD` |
| `limit` | integer | ❌ | 20 | 返回条数，范围 `[5, 100]` |

**请求示例**

```
GET /api/stocks/hot?limit=10
GET /api/stocks/hot?date_str=2026-04-04&limit=20
```

**响应示例**

```json
{
  "date": "2026-04-04",
  "data": [
    {
      "symbol": "600519",
      "name": "贵州茅台",
      "close": 1488.0,
      "open": 1470.0,
      "high": 1500.0,
      "low": 1465.0,
      "vol": 32100.0,
      "amount": 4780000000.0,
      "change_pct": 1.22
    }
  ]
}
```

---

## 二、K 线接口

### 2.1 日 K 线数据

```
GET /api/klines/{symbol}
```

**功能说明**：获取指定股票日 K 线数据，支持跨年表查询（`stock_klines_YYYY` 按年分表）。数据量超过 `limit` 时取最近 N 条。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbol` | string | ✅ | 股票代码 |

**查询参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `start_date` | string | ❌ | `2020-01-01` | 开始日期，格式 `YYYY-MM-DD` |
| `end_date` | string | ❌ | 今天 | 结束日期，格式 `YYYY-MM-DD` |
| `limit` | integer | ❌ | 500 | 最大返回条数，范围 `[1, 3000]` |
| `adjust` | string | ❌ | `none` | 复权方式（当前版本预留，暂不生效） |

**请求示例**

```
GET /api/klines/300059?start_date=2025-01-01&limit=250
```

**响应示例**

```json
{
  "symbol": "300059",
  "start_date": "2025-01-01",
  "end_date": "2026-04-06",
  "count": 250,
  "candles": [
    {
      "time": "2025-01-02",
      "open": 15.20,
      "high": 15.88,
      "low": 14.95,
      "close": 15.65,
      "vol": 125000.0,
      "amount": 1960000.0,
      "prev_close": 15.10
    }
  ],
  "volumes": [
    {
      "time": "2025-01-02",
      "value": 125000.0,
      "color": "#FF0000"
    }
  ]
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `candles[].time` | string | 交易日期 `YYYY-MM-DD` |
| `candles[].open` | float | 开盘价 |
| `candles[].high` | float | 最高价 |
| `candles[].low` | float | 最低价 |
| `candles[].close` | float | 收盘价 |
| `candles[].vol` | float\|null | 成交量（手） |
| `candles[].amount` | float\|null | 成交额（元） |
| `candles[].prev_close` | float\|null | 前一交易日收盘价 |
| `volumes[].color` | string | 柱色：`#FF0000` 红（涨）/ `#00B050` 绿（跌） |

---

### 2.2 均线数据

```
GET /api/klines/{symbol}/ma
```

**功能说明**：计算指定周期均线，内部调用 K 线接口获取数据后在内存中计算。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbol` | string | ✅ | 股票代码 |

**查询参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `start_date` | string | ❌ | `2015-01-01` | 数据起始日期 |
| `end_date` | string | ❌ | 今天 | 数据结束日期 |
| `periods` | string | ❌ | `5,10,20,60,120,250` | 逗号分隔的均线周期列表 |
| `limit` | integer | ❌ | 500 | 每条均线返回最近 N 个点，范围 `[1, 3000]` |

**请求示例**

```
GET /api/klines/300059/ma?periods=5,20,60&limit=200
```

**响应示例**

```json
{
  "symbol": "300059",
  "ma": {
    "MA5": [
      {"time": "2026-01-08", "value": 15.62},
      {"time": "2026-01-09", "value": 15.77}
    ],
    "MA20": [...],
    "MA60": [...]
  }
}
```

**注意**：为保证均线计算精度，接口内部实际请求 `limit + max_period + 50` 条原始数据，最终裁剪到 `limit` 条输出。

---

### 2.3 指定日期详细日线

```
GET /api/klines/{symbol}/detail
```

**功能说明**：获取某只股票指定交易日的详细日线数据，包含涨跌幅、振幅等衍生指标。如果前一交易日在上一年，自动跨年查询。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbol` | string | ✅ | 股票代码 |

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `date_str` | string | ✅ | 交易日期，格式 `YYYY-MM-DD` |

**请求示例**

```
GET /api/klines/300059/detail?date_str=2026-04-04
```

**响应示例**

```json
{
  "symbol": "300059",
  "date": "2026-04-04",
  "open": 16.50,
  "high": 17.00,
  "low": 16.30,
  "close": 16.88,
  "vol": 198000.0,
  "amount": 3340000.0,
  "prev_close": 16.50,
  "change": 0.38,
  "change_pct": 2.30,
  "amplitude": 4.24
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `change` | float\|null | 涨跌额（元） |
| `change_pct` | float\|null | 涨跌幅（%） |
| `amplitude` | float\|null | 振幅（%）= (high - low) / prev_close × 100 |

**错误码**

| 状态码 | 说明 |
|--------|------|
| 400 | 日期格式错误 |
| 404 | 对应年份 K 线表不存在，或该股票在该日期无数据 |

---

### 2.4 压力位 / 支撑位

```
GET /api/klines/{symbol}/levels
```

**功能说明**：综合 4 种方法计算压力位和支撑位：枢轴点（Pivot Point）、近期局部高低点、斐波那契回撤位、均线（MA5/10/20/60）。0.3% 以内的邻近价位自动归并，优先级：近期高低点 > 均线 > 枢轴点 > 斐波那契。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbol` | string | ✅ | 股票代码 |

**查询参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `end_date` | string | ❌ | 今天 | 参考基准日期 |
| `n_local` | integer | ❌ | 60 | 近期局部高低点的回溯 K 线条数，范围 `[10, 500]` |
| `n_data` | integer | ❌ | 120 | 参与计算的 K 线总条数，范围 `[30, 600]` |

**请求示例**

```
GET /api/klines/300059/levels?n_local=60&n_data=120
```

**响应示例**

```json
{
  "symbol": "300059",
  "base_date": "2026-04-04",
  "n_local": 60,
  "n_data": 120,
  "current": 16.88,
  "pivot": {
    "PP": 16.72,
    "R1": 17.05, "R2": 17.38, "R3": 17.71,
    "S1": 16.39, "S2": 16.06, "S3": 15.73
  },
  "local": {
    "recent_high": 18.50, "high_date": "2026-02-10",
    "recent_low": 14.20, "low_date": "2026-01-15"
  },
  "fib": {
    "high": 18.50, "low": 14.20,
    "f236": 17.49, "f382": 16.86, "f500": 16.35,
    "f618": 15.84, "f786": 15.12
  },
  "ma_levels": {
    "MA5": 16.75, "MA10": 16.60,
    "MA20": 16.20, "MA60": 15.80
  },
  "summary": {
    "resistance": [
      {"price": 16.86, "label": "Fib 38.2%", "method": "fib"},
      {"price": 17.49, "label": "Fib 23.6%", "method": "fib"},
      {"price": 18.50, "label": "近期高点",   "method": "local"}
    ],
    "support": [
      {"price": 16.75, "label": "MA5",  "method": "ma"},
      {"price": 16.39, "label": "S1",   "method": "pivot"},
      {"price": 15.80, "label": "MA60", "method": "ma"}
    ]
  }
}
```

**summary 字段说明**

| 字段 | 说明 |
|------|------|
| `summary.resistance` | 压力位列表（升序），价格 > 当前价 |
| `summary.support` | 支撑位列表（降序），价格 < 当前价 |
| `[].method` | 来源方法：`pivot` / `local` / `fib` / `ma` |

**错误码**

| 状态码 | 说明 |
|--------|------|
| 400 | 日期格式错误 |
| 404 | 可用 K 线数据不足 10 条 |
| 500 | 压力位计算内部错误 |

---

## 三、日内行情接口

> 数据来源：优先读 MySQL 缓存（`intraday_minutes` / `intraday_transactions_YYYYMMDD`），缓存未命中则实时从 mootdx 行情服务器拉取，并异步写入 DB 缓存。

### 3.1 分时行情

```
GET /api/intraday/{symbol}/minutes
```

**功能说明**：获取指定股票某交易日的分时行情，每分钟一条，A 股共 240 条（09:31-11:30，13:01-15:00）。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbol` | string | ✅ | 股票代码 |

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `date_str` | string | ✅ | 交易日期，格式 `YYYY-MM-DD` |

**请求示例**

```
GET /api/intraday/300059/minutes?date_str=2026-04-04
```

**响应示例**

```json
{
  "symbol": "300059",
  "date": "2026-04-04",
  "count": 240,
  "source": "cache",
  "data": [
    {
      "time": "09:31",
      "price": 16.55,
      "vol": 5200,
      "avg_price": 16.55
    }
  ]
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `source` | string | 数据来源：`cache`（数据库缓存）/ `mootdx`（实时拉取） |
| `data[].time` | string | 时间标签 `HH:MM` |
| `data[].price` | float | 分时价格 |
| `data[].vol` | integer | 当分钟成交量（手） |
| `data[].avg_price` | float | 均价（从开盘累计计算） |

**错误码**

| 状态码 | 说明 |
|--------|------|
| 404 | 该股票该日期无分时数据 |
| 503 | mootdx 行情服务器连接失败 |

---

### 3.2 分笔成交

```
GET /api/intraday/{symbol}/transactions
```

**功能说明**：获取指定股票某交易日的逐笔成交记录，最多可返回 40000 条（50 批 × 每批 800 条）。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbol` | string | ✅ | 股票代码 |

**查询参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `date_str` | string | ✅ | — | 交易日期，格式 `YYYY-MM-DD` |
| `limit` | integer | ❌ | 2000 | 返回条数，范围 `[0, 20000]`；传 `0` 返回全量 |

**请求示例**

```
GET /api/intraday/300059/transactions?date_str=2026-04-04&limit=500
```

**响应示例**

```json
{
  "symbol": "300059",
  "date": "2026-04-04",
  "count": 500,
  "total": 12800,
  "source": "mootdx",
  "data": [
    {
      "time": "09:31:02",
      "price": 16.55,
      "vol": 100,
      "side": "B"
    }
  ]
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `count` | integer | 本次返回条数（受 `limit` 限制） |
| `total` | integer | 该日全量分笔条数（仅 `source=mootdx` 时有效） |
| `data[].time` | string | 成交时间 `HH:MM:SS` |
| `data[].price` | float | 成交价格 |
| `data[].vol` | integer | 成交量（手） |
| `data[].side` | string | 成交方向：`B`（主买）/ `S`（主卖）/ `N`（中性） |

---

### 3.3 SSE 流式日内行情（推荐）

```
GET /api/intraday/{symbol}/stream
```

**功能说明**：Server-Sent Events（SSE）流式接口，同时并行拉取分时和分笔数据，哪个先完成就先推送，减少等待时间。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbol` | string | ✅ | 股票代码 |

**查询参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `date_str` | string | ✅ | — | 交易日期 |
| `limit` | integer | ❌ | 2000 | 分笔数据返回条数，`0` 表示全量 |

**SSE 事件格式**

```
event: minutes
data: {"data": [...], "source": "cache", "count": 240, "_ms": 12}

event: transactions
data: {"data": [...], "source": "mootdx", "count": 2000, "total": 12800, "_ms": 450}

event: done
data: {"ms": 462}
```

| 事件名 | 说明 |
|--------|------|
| `minutes` | 分时数据（结构同 3.1 响应中的 `data`） |
| `transactions` | 分笔数据（结构同 3.2 响应中的 `data`） |
| `done` | 所有数据推送完毕，携带总耗时 `ms` |

**响应 Headers**

```
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

---

### 3.4 日内合并接口（兼容，已废弃）

```
GET /api/intraday/{symbol}/combined
```

> ⚠️ **已废弃**，请改用 `/stream` 接口。分时和分笔串行返回（等全部完成后才响应），延迟更高。

**请求参数**：同 3.3

**响应示例**

```json
{
  "symbol": "300059",
  "date": "2026-04-04",
  "minutes": {"data": [...], "source": "cache", "count": 240},
  "transactions": {"data": [...], "source": "mootdx", "count": 2000}
}
```

---

## 四、数据采集接口

### 4.1 触发每日收盘数据采集

```
POST /api/collect/trigger
```

**功能说明**：手动触发每日收盘 K 线采集任务，在后台线程执行 `daily_collector.py`，立即返回不阻塞。同一时间只能运行一个采集任务。

**查询参数**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `date_str` | string | ❌ | 今天 | 指定采集日期，格式 `YYYY-MM-DD` |
| `symbols` | string | ❌ | 全市场 | 指定股票代码，逗号分隔，如 `300059,600519` |

**请求示例**

```
POST /api/collect/trigger
POST /api/collect/trigger?date_str=2026-04-04&symbols=300059,600519
```

**响应（已在运行中）**

```json
{
  "status": "running",
  "message": "已有采集任务在进行中",
  "progress": {
    "running": true,
    "date": "today",
    "total": 3908,
    "done": 1200,
    "failed": 3,
    "started_at": "15:50:01",
    "finished_at": null,
    "message": "已处理 1200/3908 只"
  }
}
```

**响应（启动成功）**

```json
{
  "status": "started",
  "message": "采集任务已启动",
  "date": "today",
  "symbols": "全市场"
}
```

---

### 4.2 查询采集进度

```
GET /api/collect/status
```

**功能说明**：轮询查询当前采集任务状态（前端默认 1.5 秒轮询一次）。

**请求参数**：无

**响应示例**

```json
{
  "running": false,
  "date": "2026-04-04",
  "total": 3908,
  "done": 3908,
  "failed": 2,
  "started_at": "15:50:01",
  "finished_at": "16:12:35",
  "message": "完成 ✓ 成功 3906 只，失败 2 只"
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `running` | boolean | 是否正在运行 |
| `date` | string | 采集目标日期 |
| `total` | integer | 总股票数 |
| `done` | integer | 已处理股票数（含失败） |
| `failed` | integer | 失败数量 |
| `started_at` | string\|null | 开始时间 `HH:MM:SS` |
| `finished_at` | string\|null | 完成时间（运行中为 null） |
| `message` | string | 状态描述 |

---

## 五、大模型接口（旧版 · `/api/llm`）

> 该组接口在 `api/stock/routes.py` 中定义，功能完整但不推荐新代码使用，请使用 [新版 `/api/ai` 接口](#六大模型接口新版--apiai)。

### 5.1 非流式对话

```
POST /api/llm/chat
```

**请求体（JSON）**

```json
{
  "prompt": "分析东方财富近期走势",
  "model": "deepseek-v3.2",
  "system_prompt": "你是一名专业的股票分析师",
  "temperature": 0.7,
  "max_tokens": 4096,
  "messages": null
}
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string | ✅ | — | 用户输入文本 |
| `model` | string | ❌ | `ark-code-latest` | 模型名称 |
| `system_prompt` | string | ❌ | null | 系统提示词 |
| `temperature` | float | ❌ | 0.7 | 采样温度 `[0, 2]` |
| `max_tokens` | integer | ❌ | 4096 | 最大生成 token 数 `[1, 32768]` |
| `messages` | array | ❌ | null | 自定义消息列表（传入后 `prompt`/`system_prompt` 失效） |

**响应示例**

```json
{
  "ok": true,
  "content": "东方财富近期走势...",
  "model": "deepseek-v3.2"
}
```

---

### 5.2 流式对话（SSE）

```
POST /api/llm/stream
```

**请求体**：同 5.1

**SSE 数据格式**

```
data: {"content": "东方"}
data: {"content": "财富"}
data: [DONE]
```

---

### 5.3 获取模型列表

```
GET /api/llm/models
```

**响应示例**

```json
{
  "models": {
    "ark-code-latest": "Auto（智能选模型）",
    "deepseek-v3.2": "DeepSeek V3.2",
    "glm-4.7": "GLM 4.7"
  }
}
```

---

## 六、大模型接口（新版 · `/api/ai`）

> 位于 `api/llm/routes.py`，经 Pydantic 校验，支持多轮对话历史，推荐所有新功能使用此组接口。

### 6.1 非流式对话

```
POST /api/ai/chat
```

**请求体（JSON）**

```json
{
  "message": "东方财富300059的近期技术面如何？",
  "model": "deepseek-v3.2",
  "system_prompt": "你是一名专业股票分析师，回答简洁专业",
  "temperature": 0.7,
  "max_tokens": 4096,
  "history": [
    {"role": "user",      "content": "什么是MACD指标？"},
    {"role": "assistant", "content": "MACD是..."}
  ]
}
```

| 字段 | 类型 | 必填 | 限制 | 说明 |
|------|------|------|------|------|
| `message` | string | ✅ | 最少 1 字符 | 当前用户消息 |
| `model` | string | ❌ | — | 模型 ID，见 6.3 |
| `system_prompt` | string | ❌ | — | 系统提示词 |
| `temperature` | float | ❌ | `[0, 2]`，默认 0.7 | 采样温度 |
| `max_tokens` | integer | ❌ | `[1, 32768]`，默认 4096 | 最大 token 数 |
| `history` | array | ❌ | — | 历史消息列表 `[{"role":"...", "content":"..."}]` |

**响应体（Pydantic 校验）**

```json
{
  "success": true,
  "model": "deepseek-v3.2",
  "content": "从技术面来看，300059近期...",
  "error": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | boolean | 是否成功 |
| `model` | string | 实际使用的模型 |
| `content` | string | 模型回复文本 |
| `error` | string\|null | 错误信息（成功时为 null） |

**错误码**

| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数校验失败（如 message 为空） |
| 500 | LLM 调用失败 |

---

### 6.2 流式对话（SSE）

```
POST /api/ai/stream
```

**请求体**：同 6.1

**SSE 数据格式**

每条数据：

```
data: {"content": "文本片段"}
```

结束标记：

```
data: [DONE]
```

出错时：

```
data: {"error": "错误描述"}
```

**响应 Headers**

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

---

### 6.3 可用模型列表

```
GET /api/ai/models
```

**响应示例**

```json
[
  {"id": "ark-code-latest",    "name": "Auto（智能选模型）", "description": ""},
  {"id": "doubao-seed-code",   "name": "豆包 Seed Code",    "description": ""},
  {"id": "deepseek-v3.2",      "name": "DeepSeek V3.2",     "description": ""},
  {"id": "glm-4.7",            "name": "GLM 4.7",           "description": ""},
  {"id": "kimi-k2.5",          "name": "Kimi K2.5",         "description": ""},
  {"id": "minimax-m2.5",       "name": "MiniMax M2.5",      "description": ""},
  {"id": "doubao-seed-2.0-code","name": "豆包 Seed 2.0 Code","description": ""},
  {"id": "doubao-seed-2.0-pro", "name": "豆包 Seed 2.0 Pro", "description": ""},
  {"id": "doubao-seed-2.0-lite","name": "豆包 Seed 2.0 Lite","description": ""}
]
```

---

## 错误码说明

| HTTP 状态码 | 含义 | 常见场景 |
|-------------|------|----------|
| 200 | 成功 | — |
| 400 | 请求参数错误 | 日期格式不对、字段超出范围 |
| 404 | 数据不存在 | 股票代码不存在、指定日期无数据 |
| 500 | 服务器内部错误 | 数据库连接异常、LLM 调用失败 |
| 503 | 外部服务不可用 | mootdx 行情服务器连接失败 |

---

*文档由系统自动生成 · 2026-04-06*
