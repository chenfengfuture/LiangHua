# 量华平台 — 新闻系统架构文档

> 文档版本：v1.0 | 更新日期：2026-04-07

---

## 一、总体架构概览

```
┌──────────────────────────────────────────────────────────────────────┐
│                        量华量化平台（FastAPI）                          │
│                     后端服务  host:8001                                 │
├───────────────┬──────────────────────────────┬───────────────────────┤
│  api/stock/   │       api/news/              │      api/llm/          │
│  routes.py    │       routes.py              │      routes.py         │
│  (K线/行情)   │  (新闻采集 / LLM分析接口)    │  (LLM对话接口)         │
└───────────────┴──────────────────────────────┴───────────────────────┘
         │                    │                           │
         ▼                    ▼                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         utils/（核心工具层）                           │
│  db.py              websocket_manager.py   llm.py                    │
│  （MySQL连接池）     （WS单例管理器）        （火山方舟LLM）           │
│  akshare.py         websocket_utils.py     collector.py              │
│  （新闻采集器）      （WS便捷函数）          （K线采集器）             │
└─────────────────────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌──────────────────┐  ┌─────────────────────┐
│  MySQL: lianghua │  │  MySQL: news_data   │
│  （K线/行情数据） │  │  （新闻专库）        │
└──────────────────┘  └─────────────────────┘
                              │
                     按月分表：news_{type}_{YYYYMM}
                     6种类型 × 每月1张表
```

---

## 二、新闻系统文件清单

| 文件路径 | 职责 | 状态 |
|----------|------|------|
| `backend/api/news/routes.py` | HTTP 路由入口（当前仅占位） | ⚠️ 待实现 |
| `backend/api/news/llm_analyzer.py` | LLM 分析核心模块（单条+批量） | ✅ 完成 |
| `backend/utils/akshare.py` | 多源新闻采集器（6种数据源） | ✅ 完成 |
| `backend/models/news_models.py` | 数据库模型、建表 DDL、CRUD | ✅ 完成 |
| `backend/utils/websocket_manager.py` | WebSocket 全局单例管理器 | ✅ 完成 |
| `backend/utils/websocket_utils.py` | WS 便捷推送函数 | ✅ 完成 |

---

## 三、数据库结构

### 3.1 数据库分离原则

| 数据库 | 用途 | 连接池 |
|--------|------|--------|
| `lianghua` | 股票K线、行情数据 | `utils/db.py → get_conn()` |
| `news_data` | 所有新闻数据（专库隔离） | `utils/db.py → get_news_conn()` |

### 3.2 分表策略

```
news_data 库：
  news_company_YYYYMM   ← 个股/公司新闻
  news_cctv_YYYYMM      ← 新闻联播
  news_caixin_YYYYMM    ← 财联社电报
  news_global_YYYYMM    ← 全球财经新闻
  news_notice_YYYYMM    ← 个股公告
  news_stock_YYYYMM     ← 研报

示例：news_company_202604、news_global_202604
```

### 3.3 表字段结构（共 44+ 字段，分 5 组）

```
【基础信息】8字段（采集时写入）
  id, title, content, url, source, source_category, news_type,
  publish_time, collect_time

【LLM分析输出】12字段（LLM回写）
  ai_interpretation    — 200字核心解读
  ai_event_type        — 事件类型枚举（11类）
  ai_impact_level      — 影响等级（1-5）
  ai_impact_direction  — 影响方向（-1/0/1 利空/中性/利好）
  ai_risk_level        — 风险等级（1-5）
  ai_benefit_sectors   — 受益板块（中文逗号分隔）
  ai_benefit_stocks    — 受益个股（严禁虚构）
  ai_keywords          — 3-6个关键词
  sentiment            — 情感得分（-1.0~1.0）
  sentiment_label      — 情感标签（-1/0/1）
  is_official          — 是否官方公告（0/1）
  is_breaking          — 是否突发新闻（0/1）

【系统自动填充】3字段
  ai_analyze_time      — AI分析完成时间
  need_analyze         — 1=待分析 / 0=已完成（入库时由清洗逻辑设置）
  source_level         — 来源可信度等级

【扩展预留】17字段（当前不使用）
  情感扩展6个、AI扩展5个、量化交易适配6个

【数据治理】5字段
  create_time, update_time, data_version, operator, is_deleted

【去重索引】
  url_hash CHAR(32) = MD5(url)，UNIQUE INDEX uk_url_hash
  + 8个普通索引（publish_time/collect_time/source_category/
    need_analyze/is_processed/ai_impact_direction/is_deleted/news_type/source）
```

---

## 四、新闻采集逻辑（utils/akshare.py）

### 4.1 采集器架构

```
AkNewsCollector（全局单例，双重检查锁）
    │
    ├── collect_all(target_date, types, symbols)
    │       ├── notice → 单独线程（数据量大约3000条，timeout=120s）
    │       └── 其余5种 → ThreadPoolExecutor（max_workers=8）并行
    │
    └── collect(news_type, target_date, symbols)
            └── _collect_single_type()
                    ├── 阶段1: 请求数据（_fetch_xxx）
                    ├── 阶段2: 清洗（clean_news_rows → need_analyze标记）
                    └── 阶段3: 入库（insert_news，INSERT IGNORE，500条分批）
```

### 4.2 各数据源采集细节

| 类型 | 数据源 | API | 过滤策略 | 特殊说明 |
|------|--------|-----|---------|---------|
| `company` | 东方财富 | `ak.stock_news_em(symbol)` | 按 symbol 遍历 | 不支持日期筛选，返回最近新闻 |
| `cctv` | 新闻联播 | `ak.news_cctv(date)` | 仅工作日 + 19:40后 | 周末/未到点直接返回空 |
| `caixin` | 财联社 | 直调 cxdata.caixin.com API | 分页直到无当日数据 | pageSize=100，pageNum递增 |
| `global` | 东方财富 | 直调 np-weblist.eastmoney.com | sortEnd游标翻页 | 最多25页(5000条)，出现昨日数据停止 |
| `notice` | 东方财富 | `ak.stock_notice_report("全部", date)` | 非交易日自动跳过 | 单独线程，explicit_date可强制采集 |
| `stock` | 东方财富 | `ak.stock_research_report_em(symbol)` | 按"日期"字段过滤 | 按symbol遍历，不支持日期筛选 |

### 4.3 敏感性清洗（入库前）

```python
# 非CCTV新闻
need_llm_analyze(title, content, news_type)
  → 命中敏感词（政治/战争/极端...）或高风险词（立案/退市/造假...）
    → need_analyze = 0（不进LLM）
  → 正常财经内容
    → need_analyze = 1（待LLM分析）

# CCTV新闻（二次过滤）
filter_cctv_policy(title, content)
  → 命中政治黑词（中央/国务院/领导人/外交...）→ need_analyze = 0
  → 命中产业白词（新能源/半导体/芯片/降准...）→ need_analyze = 1
  → 无明确产业指向 → need_analyze = 0
```

### 4.4 去重机制

- **数据库层**：`UNIQUE INDEX uk_url_hash (url_hash)`，`INSERT IGNORE` 自动跳过重复
- **采集层**：采集过程中维护 `seen_titles` / `seen_urls` / `seen_codes` Set，内存去重
- **url_hash**：`MD5(url)`，32位hex，url为空则为 NULL（不参与去重）

---

## 五、LLM 分析逻辑（api/news/llm_analyzer.py）

### 5.1 分析流程

```
analyze_news(title, content, source, source_category, news_type)
    │
    ├── 1. 校验：标题非空
    │
    ├── 2. 构建用户消息
    │       ## 新闻标题 / ## 新闻正文（≤3000字）/ ## 来源媒体 / ## 来源分类 / ## 新闻类型
    │
    ├── 3. 调用 LLM().chat(prompt, system_prompt=SYSTEM_PROMPT, temperature=0.1)
    │       模型：ark-code-latest（默认）
    │
    ├── 4. _extract_json(raw_text)
    │       支持纯JSON / ```json...``` / JSON前后有文字
    │
    ├── 5. _validate_and_clean(parsed)
    │       类型转换 + 范围钳位 + 枚举校验 → 清洗后12字段dict
    │
    └── 返回 {success, raw_text, result(12字段), error, stats{filled_count}}
```

### 5.2 系统提示词（SYSTEM_PROMPT）核心约束

```
- 只输出JSON，禁止任何额外文字
- 字段不可增减，未知填 null
- 列表用中文逗号分隔，空值填 ""
- 数字为数字类型，分数保留2位小数
- 严禁虚构个股、板块、指数
```

### 5.3 输出字段校验规则

| 字段 | 类型 | 范围/枚举 |
|------|------|---------|
| `ai_impact_level` | int | [1, 5] |
| `ai_impact_direction` | int | [-1, 0, 1] |
| `ai_risk_level` | int | [1, 5] |
| `sentiment` | float | [-1.0, 1.0] |
| `sentiment_label` | int | [-1, 0, 1] |
| `is_official` | int | [0, 1] |
| `is_breaking` | int | [0, 1] |
| `ai_event_type` | str | 财报/并购/政策/研发/诉讼/高管变动/战略合作/产能扩张/业务调整/风险事件/其他 |

### 5.4 批量分析（batch_analyze）

```
batch_analyze(limit=10, model=None, temperature=0.3, dry_run=False)
    │
    ├── 1. fetch_need_analyze(limit) — 跨所有分表查 need_analyze=1
    │
    ├── 2. 逐条调用 analyze_news()
    │
    ├── 3. update_ai_result(table_name, news_id, result)
    │       自动设 ai_analyze_time = NOW()，need_analyze 仍为1（未更新）
    │
    └── 返回统计 {total_fetched, processed, success, failed, results}
```

> **注意**：当前 `batch_analyze` 完成后 `need_analyze` 字段**不会**自动置0，
> 如需标记"已分析"，需在 `update_ai_result` 中额外设 `need_analyze=0`。

---

## 六、WebSocket 实时推送

### 6.1 架构设计

```
main.py
  @app.websocket("/ws")          ← 连接入口
  startup → ws_manager.set_loop()  ← 绑定事件循环

utils/websocket_manager.py
  ConnectionManager（全局单例 ws_manager）
    connect/disconnect            ← 生命周期
    subscribe/unsubscribe         ← 频道订阅
    broadcast(channel, data)      ← 异步广播
    broadcast_sync(channel, data) ← 同步广播（供线程调用）

utils/websocket_utils.py
  ws_send_news_update(news_id, data)         → 频道 news
  ws_send_news_batch(results)                → 频道 news
  ws_send_collect_status(source, status, count) → 频道 collect
  ws_send_collect_progress(source, total, current) → 频道 collect
  ws_broadcast(channel, data, msg_type)      → 任意频道
```

### 6.2 频道约定

| 频道 | 用途 | 消息 type |
|------|------|---------|
| `news` | 新闻分析结果推送 | `news_update` / `news_batch` |
| `collect` | 采集状态/进度推送 | `collect_status` / `collect_progress` |
| `llm` | LLM分析进度（预留） | — |
| `general` | 通用广播（默认） | `message` |

### 6.3 前端接入协议

```javascript
const ws = new WebSocket("ws://host:8001/ws");

// 订阅频道
ws.send(JSON.stringify({ action: "subscribe", channels: ["news", "collect"] }));

// 心跳
ws.send(JSON.stringify({ action: "ping" }));
// → 服务端返回 { type: "pong" }

// 接收消息格式
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  // msg.type = "news_update" | "news_batch" | "collect_status" | ...
  // msg.timestamp = Unix时间戳
};
```

---

## 七、当前接口状态

### 7.1 已实现接口（routes.py 占位）

| 方法 | 路由 | 状态 | 说明 |
|------|------|------|------|
| GET | `/api/news/` | ✅ 占位 | 返回 `{status: "ok"}` |

### 7.2 待实现接口（规划中）

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/api/news/collect_all` | **统一采集总接口**（4线程并行：company/caixin/global/stock） |
| GET | `/api/news/list` | 新闻列表查询 |
| GET | `/api/news/analyze` | 触发批量LLM分析 |
| GET | `/api/news/stats` | 采集/分析统计 |

---

## 八、完整数据流

### 8.1 单次采集（collect_all 触发后的完整链路）

```
GET /api/news/collect_all?date=2026-04-07
    │
    ├── 后台启动4个独立线程（立即返回"已启动"）
    │
    │   ┌────────────────────────────────────────────────┐
    │   │  线程A: company  线程B: caixin  线程C: global  线程D: stock
    │   │
    │   │  每个线程执行：
    │   │
    │   │  1. [采集] AkNewsCollector._collect_single_type()
    │   │       → _fetch_xxx() 请求外部API
    │   │       → clean_news_rows() 清洗+设置need_analyze
    │   │       → insert_news() 批量入库（INSERT IGNORE）
    │   │
    │   │  2. [推送①] ws_send_collect_status(source, "completed", count)
    │   │       → WebSocket广播到前端 collect 频道
    │   │
    │   │  3. [LLM分析] 对本批新闻逐条调用 analyze_news()
    │   │       → need_analyze=1 的新闻才进LLM
    │   │       → 返回12字段结构化结果
    │   │
    │   │  4. [回写DB] update_ai_result(table, id, result)
    │   │       → 更新12个AI字段 + ai_analyze_time
    │   │
    │   │  5. [推送②] ws_send_news_update(news_id, result)
    │   │       → WebSocket广播到前端 news 频道
    │   │
    │   └────────────────────────────────────────────────┘
    │
    └── 返回 {"status": "started", "message": "4个采集线程已启动"}
```

### 8.2 数据写入时序

```
原始新闻入库
  title / content / url / source / source_category
  news_type / publish_time / collect_time（系统自动）
  need_analyze（1=待分析 / 0=敏感跳过）
  url_hash = MD5(url)

↓ LLM分析完成后回写

  ai_interpretation / ai_event_type / ai_impact_level
  ai_impact_direction / ai_risk_level / ai_benefit_sectors
  ai_benefit_stocks / ai_keywords / sentiment / sentiment_label
  is_official / is_breaking
  ai_analyze_time = NOW()
```

---

## 九、当前已知限制 & 待改进项

| 编号 | 问题 | 说明 |
|------|------|------|
| 1 | `routes.py` 仅占位 | `/api/news/collect_all` 等接口尚未实现 |
| 2 | `update_ai_result` 未重置 `need_analyze` | LLM分析完成后 `need_analyze` 仍为1，`fetch_need_analyze` 会重复拉取 |
| 3 | `batch_analyze` 串行处理 | 每条新闻逐一等待LLM返回，无并发，处理速度慢 |
| 4 | 无日期范围采集 | `collect_all` 只支持单日，不支持 `start_date~end_date` 范围 |
| 5 | `cctv` 采集时间限制 | 写死了"19:40后"限制，回测场景无法绕过 |
| 6 | `company/stock` 无日期筛选 | akshare 接口本身不支持日期过滤，只能拉最近数据 |

---

## 十、代码快速索引

```python
# 采集新闻（单次）
from utils.akshare import collect_news
collect_news(target_date="2026-04-07", types=["global", "caixin"])

# 采集新闻（单例方式）
from utils.akshare import get_news_collector
get_news_collector().collect_all()

# 单条LLM分析
from api.news.llm_analyzer import analyze_news
result = analyze_news(title="...", content="...", news_type="global")

# 批量LLM分析（从DB拉取待分析）
from api.news.llm_analyzer import batch_analyze
stats = batch_analyze(limit=50)

# WebSocket推送
from utils.websocket_utils import ws_send_news_update, ws_send_collect_status
ws_send_news_update(news_id=123, data={"sentiment": 0.8, ...})
ws_send_collect_status(source="global", status="completed", count=42)

# 数据库直接查询
from models.news_models import fetch_need_analyze, update_ai_result, fetch_news_by_date
news_list = fetch_need_analyze(limit=20)
fetch_news_by_date("global", "202604", "2026-04-07")
```
