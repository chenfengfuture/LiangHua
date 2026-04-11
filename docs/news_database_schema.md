# 量华量化平台 — 新闻数据库表结构文档

> **模块文件**：`backend/models/news_models.py`  
> **数据库**：MySQL 8.0，schema `lianghua`  
> **版本**：v2（2026-04-03 从零重写）  
> **更新日期**：2026-04-06

---

## 目录

1. [设计原则](#一设计原则)
2. [新闻类型与分表规则](#二新闻类型与分表规则)
3. [表结构详解](#三表结构详解)  
   3.1 [核心字段](#31-核心字段)  
   3.2 [AI 分析字段（预留）](#32-ai-分析字段预留)  
   3.3 [情感分析字段](#33-情感分析字段)  
   3.4 [索引设计](#34-索引设计)
4. [各类型表说明](#四各类型表说明)  
   4.1 [company — 个股新闻](#41-company--个股新闻)  
   4.2 [cctv — 新闻联播](#42-cctv--新闻联播)  
   4.3 [caixin — 财联社电报](#43-caixin--财联社电报)  
   4.4 [global — 全球财经新闻](#44-global--全球财经新闻)  
   4.5 [notice — 个股公告](#45-notice--个股公告)  
   4.6 [stock — 研报](#46-stock--研报)
5. [DDL 完整定义](#五ddl-完整定义)
6. [CRUD 操作说明](#六crud-操作说明)
7. [去重机制](#七去重机制)
8. [敏感性分析字段（need_analyze）](#八敏感性分析字段need_analyze)
9. [数据示例](#九数据示例)

---

## 一、设计原则

| 原则 | 说明 |
|------|------|
| **按月分表** | 每种新闻类型按月建表：`news_{type}_YYYYMM`，避免单表过大 |
| **唯一去重** | `UNIQUE INDEX uk_url(url(255))`，基于 URL 自动去重，`INSERT IGNORE` 幂等写入 |
| **保留原始时间** | `publish_time` 严格保留 akshare 原生字段值，**禁止用系统时间覆盖** |
| **AI 字段预留** | 4 个 AI 分析字段（解读/受益板块/受益个股/关键供应商）已在 DDL 中预留，目前均为 NULL |
| **情感字段预留** | 3 个情感分析字段已预留，目前均为 NULL |
| **自动补全** | `ensure_table_exists()` 支持自动 ALTER ADD 补齐缺失字段和索引，幂等操作 |
| **批量写入** | `insert_news()` 每批 500 条 `INSERT IGNORE`，避免单条 SQL 过大 |

---

## 二、新闻类型与分表规则

### 分表命名规则

```
news_{type}_{YYYYMM}
```

**示例**：
- `news_company_202604`（2026年4月个股新闻）
- `news_cctv_202604`（2026年4月新闻联播）
- `news_notice_202604`（2026年4月公告）

### 新闻类型一览

| 类型 ID | 表名示例 | 表注释 | 数据来源 | source_category 值 |
|---------|----------|--------|----------|-------------------|
| `company` | `news_company_YYYYMM` | 公司动态新闻 | 东方财富 `stock_news_em()` | `东方财富` |
| `cctv` | `news_cctv_YYYYMM` | 新闻联播 | AkShare `news_cctv()` | `新闻联播` |
| `caixin` | `news_caixin_YYYYMM` | 财新新闻 | 财联社 API 直接调用 | `财联社` |
| `global` | `news_global_YYYYMM` | 国际新闻 | 东方财富 API 直接调用 | `东方财富全球` |
| `notice` | `news_notice_YYYYMM` | 公告 | 东方财富 `stock_notice_report()` | `东方财富公告` |
| `stock` | `news_stock_YYYYMM` | 个股新闻 | 东方财富 `stock_research_report_em()` | `东方财富研报` |

---

## 三、表结构详解

所有 6 种类型的分表使用**完全相同的 DDL**，仅表名和 COMMENT 不同。

### 3.1 核心字段

| 字段名 | 类型 | 非空 | 默认值 | 注释 |
|--------|------|------|--------|------|
| `id` | BIGINT AUTO_INCREMENT | ✅ | — | 主键，自增 |
| `title` | VARCHAR(500) | ✅ | `''` | 新闻标题（最长 500 字符） |
| `content` | TEXT | ❌ | NULL | 正文摘要（无长度限制） |
| `url` | VARCHAR(1000) | ❌ | NULL | 原文链接（唯一索引基于前 255 字符） |
| `source` | VARCHAR(100) | ✅ | `''` | 来源媒体名称，如 `东方财富`、`财联社`、`新华社` |
| `source_category` | VARCHAR(50) | ✅ | `''` | 来源分类（枚举，见下表） |
| `news_type` | VARCHAR(20) | ✅ | `''` | 新闻分类，如 `财经` / `时政` / `军事` / `外交` / `其他` |
| `publish_time` | DATETIME | ❌ | NULL | **发布时间**（原始值，禁止用系统时间覆盖） |
| `collect_time` | DATETIME | ✅ | `CURRENT_TIMESTAMP` | 入库时间（自动填写） |

**source_category 枚举值**

| 值 | 对应表类型 | 说明 |
|----|-----------|------|
| `东方财富` | company | 东方财富个股动态新闻 |
| `新闻联播` | cctv | CCTV 新闻联播 |
| `财联社` | caixin | 财联社电报 |
| `东方财富全球` | global | 东方财富全球财经新闻 |
| `东方财富公告` | notice | 东方财富上市公司公告 |
| `东方财富研报` | stock | 东方财富分析师研报 |

---

### 3.2 AI 分析字段（预留）

> 字段已在 DDL 中创建，目前均为 NULL，待后续 AI 分析流水线写入。

| 字段名 | 类型 | 默认值 | 注释 |
|--------|------|--------|------|
| `ai_interpretation` | TEXT | NULL | AI 解读（对新闻的专业解读文本） |
| `ai_benefit_sectors` | TEXT | NULL | AI 受益板块（JSON 数组，如 `["半导体","新能源"]`） |
| `ai_benefit_stocks` | TEXT | NULL | AI 受益个股（JSON 数组，如 `["300059","688981"]`） |
| `ai_key_suppliers` | TEXT | NULL | AI 关键供应商（JSON 数组）|
| `need_analyze` | TINYINT(1) | 0 | **是否需要 AI 分析**（写入时由敏感性判断逻辑设置，见第八节） |

---

### 3.3 情感分析字段

> 字段已在 DDL 中创建，目前均为 NULL，待后续情感分析模型写入。

| 字段名 | 类型 | 默认值 | 注释 |
|--------|------|--------|------|
| `sentiment` | FLOAT | NULL | 情感得分（通常 -1 到 +1 之间） |
| `sentiment_label` | TINYINT | NULL | 情感标签：`1`=正面 / `0`=中性 / `-1`=负面 |
| `sentiment_confidence` | FLOAT | NULL | 情感置信度（0 到 1） |

---

### 3.4 索引设计

| 索引名 | 类型 | 字段 | 用途 |
|--------|------|------|------|
| `PRIMARY` | PRIMARY KEY | `id` | 主键 |
| `idx_publish_time` | 普通索引 | `publish_time` | 按发布时间查询 |
| `idx_collect_time` | 普通索引 | `collect_time` | 按入库时间查询 |
| `idx_source_category` | 普通索引 | `source_category` | 按来源分类过滤 |
| `idx_sentiment_label` | 普通索引 | `sentiment_label` | 按情感标签过滤 |
| `idx_need_analyze` | 普通索引 | `need_analyze` | 快速找待分析数据 |
| `uk_url` | **唯一索引** | `url(255)` | 基于 URL 前 255 字符去重 |

---

## 四、各类型表说明

### 4.1 company — 个股新闻

**表名**：`news_company_YYYYMM`  
**数据来源**：AkShare `ak.stock_news_em(symbol=股票代码)`  
**采集说明**：
- 需传入 `symbols` 列表（默认：`300059, 600519, 300750, 600030, 688981`）
- 每只股票单独调用 API，无日期筛选能力，返回最近 N 条
- 标题去重（`seen_titles` 集合）

**典型数据示例**

| 字段 | 示例值 |
|------|--------|
| `title` | `东方财富：2025年年报净利润同比增长28%` |
| `content` | `（正文摘要）东方财富公告称...` |
| `url` | `https://guba.eastmoney.com/news,300059,...` |
| `source` | `东方财富` |
| `source_category` | `东方财富` |
| `news_type` | `company` |
| `publish_time` | `2026-04-04 18:30:00` |

---

### 4.2 cctv — 新闻联播

**表名**：`news_cctv_YYYYMM`  
**数据来源**：AkShare `ak.news_cctv(date="YYYYMMDD")`  
**采集限制**：
- 仅工作日（周一~周五）采集，周末跳过
- 仅 19:40 之后可成功调用（新闻联播播出后）
- 无 URL，`url` 字段始终为 NULL

**敏感性过滤**：CCTV 新闻走专用 `filter_cctv_policy()` 二次过滤：
- 命中政治黑名单词（中央/国务院/外交等）→ `need_analyze = 0`
- 命中产业白名单词（新能源/半导体/降息等）→ `need_analyze = 1`
- 其他无产业指向 → `need_analyze = 0`

**典型数据示例**

| 字段 | 示例值 |
|------|--------|
| `title` | `工业和信息化部部署加快新能源汽车产业发展` |
| `content` | `今日新闻联播播出以下内容：...` |
| `url` | `NULL` |
| `source` | `新闻联播` |
| `source_category` | `新闻联播` |
| `news_type` | `cctv` |
| `publish_time` | `2026-04-04 19:00:00` |

---

### 4.3 caixin — 财联社电报

**表名**：`news_caixin_YYYYMM`  
**数据来源**：财联社 API 直接调用（非 AkShare，支持分页）  
**API**：`https://cxdata.caixin.com/api/dataplus/sjtPc/news`  
**采集逻辑**：
- `pageNum` + `pageSize=100` 分页拉取
- 使用 Unix 时间戳 `time` 字段解析发布时间（精确到秒）
- 过滤出当天数据，当某页无当天数据时停止翻页

**典型数据示例**

| 字段 | 示例值 |
|------|--------|
| `title` | `【财联社】央行今日开展2000亿逆回购操作` |
| `content` | `央行今日通过公开市场操作...` |
| `url` | `https://database.caixin.com/2026-04-04/102430524.html` |
| `source` | `财联社` |
| `source_category` | `财联社` |
| `news_type` | `caixin` |
| `publish_time` | `2026-04-04 09:15:32` |

---

### 4.4 global — 全球财经新闻

**表名**：`news_global_YYYYMM`  
**数据来源**：东方财富 API 直接调用  
**API**：`https://np-weblist.eastmoney.com/comm/web/getFastNewsList`  
**采集逻辑**：
- 使用 `sortEnd` 游标翻页（每页 200 条）
- 过滤出当天数据，当某页全无当天数据时停止
- 安全阀：最多拉 25 页（共 5000 条）
- URL 自动构造：`https://finance.eastmoney.com/a/{code}.html`

**典型数据示例**

| 字段 | 示例值 |
|------|--------|
| `title` | `美联储主席鲍威尔暗示年内降息节奏将放缓` |
| `content` | `美联储主席杰罗姆·鲍威尔周五发表讲话称...` |
| `url` | `https://finance.eastmoney.com/a/202604043456789.html` |
| `source` | `东方财富` |
| `source_category` | `东方财富全球` |
| `news_type` | `global` |
| `publish_time` | `2026-04-04 22:30:00` |

---

### 4.5 notice — 个股公告

**表名**：`news_notice_YYYYMM`  
**数据来源**：AkShare `ak.stock_notice_report(symbol="全部", date="YYYYMMDD")`  
**特点**：
- 数据量大（约 3000 条/日），使用**单独线程**采集，不占用主线程池
- 等待超时：2 分钟（`join(timeout=120)`）
- `content` 字段格式：`[公告类型] 公司名称`

**典型数据示例**

| 字段 | 示例值 |
|------|--------|
| `title` | `东方财富关于2025年度利润分配方案的公告` |
| `content` | `[年度报告] 东方财富` |
| `url` | `https://data.eastmoney.com/notices/300059,...` |
| `source` | `东方财富` |
| `source_category` | `东方财富公告` |
| `news_type` | `notice` |
| `publish_time` | `2026-04-04 00:00:00` |

---

### 4.6 stock — 研报

**表名**：`news_stock_YYYYMM`  
**数据来源**：AkShare `ak.stock_research_report_em(symbol=股票代码)`  
**采集说明**：
- 需传入 `symbols` 列表（默认同 company）
- 接口不支持日期筛选，从"日期"字段过滤出当天数据
- `content` 字段格式：`[机构名称] 评级:xxx 行业:xxx`
- `url` 为报告 PDF 链接

**典型数据示例**

| 字段 | 示例值 |
|------|--------|
| `title` | `东方财富2026年中期投资策略报告：互联网金融龙头持续扩张` |
| `content` | `[中信证券] 评级:买入 行业:互联网金融` |
| `url` | `https://pdf.dfcfw.com/pdf/.../...pdf` |
| `source` | `中信证券` |
| `source_category` | `东方财富研报` |
| `news_type` | `stock` |
| `publish_time` | `2026-04-04 00:00:00` |

---

## 五、DDL 完整定义

```sql
CREATE TABLE IF NOT EXISTS `news_{type}_{YYYYMM}` (
    -- ── 主键 ──
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY,

    -- ── 核心字段 ──
    title           VARCHAR(500)    NOT NULL DEFAULT ''     COMMENT '标题',
    content         TEXT            DEFAULT NULL            COMMENT '正文摘要',
    url             VARCHAR(1000)   DEFAULT NULL            COMMENT '原文链接',
    source          VARCHAR(100)    NOT NULL DEFAULT ''     COMMENT '来源',
    source_category VARCHAR(50)     NOT NULL DEFAULT ''     COMMENT '来源分类: 东方财富/财联社/新闻联播/东方财富研报等',
    news_type       VARCHAR(20)     NOT NULL DEFAULT ''     COMMENT '分类: 财经/时政/军事/外交/其他',
    publish_time    DATETIME        DEFAULT NULL            COMMENT '发布时间',
    collect_time    DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',

    -- ── AI 分析字段（预留）──
    ai_interpretation   TEXT        DEFAULT NULL COMMENT 'AI 解读',
    ai_benefit_sectors  TEXT        DEFAULT NULL COMMENT 'AI 受益板块',
    ai_benefit_stocks   TEXT        DEFAULT NULL COMMENT 'AI 受益个股',
    ai_key_suppliers    TEXT        DEFAULT NULL COMMENT 'AI 关键供应商',
    need_analyze        TINYINT(1)  DEFAULT 0    COMMENT '是否需要AI分析',

    -- ── 情感分析字段 ──
    sentiment           FLOAT       DEFAULT NULL COMMENT '情感得分',
    sentiment_label     TINYINT     DEFAULT NULL COMMENT '情感标签: 1=正面, 0=中性, -1=负面',
    sentiment_confidence FLOAT      DEFAULT NULL COMMENT '情感置信度',

    -- ── 索引 ──
    INDEX idx_publish_time      (publish_time),
    INDEX idx_collect_time      (collect_time),
    INDEX idx_source_category   (source_category),
    INDEX idx_sentiment_label   (sentiment_label),
    INDEX idx_need_analyze      (need_analyze),

    -- ── 唯一索引：基于 URL 前缀去重 ──
    UNIQUE INDEX uk_url         (url(255))

) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='{表注释}';
```

---

## 六、CRUD 操作说明

### 建表

```python
from models.news_models import (
    create_news_table,
    create_news_tables_for_month,
    ensure_table_exists,
)

# 创建单张表
create_news_table(news_type="company", year_month="202604")
# → 创建 news_company_202604

# 批量创建某月所有类型表
create_news_tables_for_month(year_month="202604")
# → 创建 news_company_202604, news_cctv_202604, ..., news_stock_202604

# 幂等确保表存在（含自动 ALTER ADD 补齐缺失字段和索引）
ensure_table_exists(news_type="caixin", year_month="202604")
```

### 写入

```python
from models.news_models import insert_news

rows = [
    {
        "title":           "标题示例",
        "content":         "摘要内容",
        "url":             "https://example.com/news/1.html",
        "source":          "财联社",
        "source_category": "财联社",
        "news_type":       "caixin",
        "publish_time":    "2026-04-04 10:30:00",
        "need_analyze":    1,
    },
    # ... 更多数据
]

inserted_count = insert_news(
    news_type="caixin",
    year_month="202604",
    rows=rows
)
print(f"实际写入：{inserted_count} 条")
# 重复 URL 自动跳过，not counted
```

**写入规则：**
- 每 500 条一批 `INSERT IGNORE`
- 遇到 `uk_url` 唯一索引冲突时静默跳过（不计入返回值）
- 返回值为实际新增行数

### 查询

```python
from models.news_models import fetch_news_by_date

# 按日期查询
rows = fetch_news_by_date(
    news_type="global",
    year_month="202604",
    date_str="2026-04-04",
    limit=100
)
```

### 获取表名

```python
from models.news_models import get_table_name

table = get_table_name("notice", "202604")
# → "news_notice_202604"
```

---

## 七、去重机制

### 核心原理

**唯一索引**：`UNIQUE INDEX uk_url (url(255))`

- 基于 `url` 字段前 255 字符建立唯一索引
- 同一 URL 的新闻只会入库一次
- `INSERT IGNORE` + 唯一索引 = 幂等写入（可安全重复采集）

### 特殊情况

| 情况 | 处理方式 |
|------|----------|
| `url` 为 NULL | NULL 不参与唯一性判断，多条 NULL 可同时存在 |
| URL 超过 255 字符 | 只取前 255 字符参与去重（可能极少数长 URL 被错误判重） |
| CCTV 新闻无 URL | `url = NULL`，无法通过 URL 去重，依赖 `title` 手动去重（采集器层面） |

### 自动修复唯一索引

若旧表没有 `uk_url` 索引，`ensure_table_exists()` 会自动添加，并处理已有重复数据：

```sql
-- 先清理重复
DELETE t1 FROM `news_caixin_202604` t1
INNER JOIN `news_caixin_202604` t2
WHERE t1.id > t2.id AND t1.url = t2.url AND t1.url IS NOT NULL;

-- 再建唯一索引
ALTER TABLE `news_caixin_202604` ADD UNIQUE INDEX uk_url (url(255));
```

---

## 八、敏感性分析字段（need_analyze）

`need_analyze` 字段在**采集入库前**由 `clean_news_rows()` 自动填写，决定是否后续需要 LLM 分析。

### 判断规则

#### 非 CCTV 类型：`need_llm_analyze(title, content, news_type)`

| 情况 | `need_analyze` 值 | 说明 |
|------|-------------------|------|
| 命中**敏感词**（政治/战争/示威等） | `0` | 敏感内容，不进 LLM |
| 命中**高风险词**（立案/退市/欺诈等） | `0` | 高风险内容，不进 LLM |
| 正常财经内容 | `1` | 可进 LLM 分析 |

**敏感词列表**：
```
政治 战争 制裁 外交 国家领导人 示威 暴乱 恐怖
疫情 死亡 极端 反动 台独 港独 敏感
```

**高风险词列表**：
```
立案 调查 处罚 退市 破产 违法 违规 造假 欺诈
强制措施 风险警示 内幕交易 操纵市场
```

#### CCTV 类型：`filter_cctv_policy(title, content)`

| 情况 | `need_analyze` 值 |
|------|-------------------|
| 命中**政治黑名单词**（中央/国务院/外交等） | `0` |
| 命中**产业白名单词**（新能源/半导体/降息等） | `1` |
| 无明确产业指向 | `0` |

**产业白名单**：
```
新能源 半导体 芯片 高端制造 生物医药 创新药
消费 家电 汽车 基建 新基建 降准 降息
乡村振兴 养老 医疗 教育 数字经济 人工智能
光伏 储能 风电 新能源车 国产替代
```

---

## 九、数据示例

### 完整记录示例（caixin）

```json
{
  "id": 12345,
  "title": "【财联社】央行今日开展2000亿逆回购操作，利率维持1.5%不变",
  "content": "中国人民银行今日以利率招标方式开展了2000亿元7天期逆回购操作，中标利率为1.50%，与上次持平。",
  "url": "https://database.caixin.com/2026-04-04/102430524.html",
  "source": "财联社",
  "source_category": "财联社",
  "news_type": "caixin",
  "publish_time": "2026-04-04 09:15:32",
  "collect_time": "2026-04-04 09:16:05",
  "ai_interpretation": null,
  "ai_benefit_sectors": null,
  "ai_benefit_stocks": null,
  "ai_key_suppliers": null,
  "need_analyze": 1,
  "sentiment": null,
  "sentiment_label": null,
  "sentiment_confidence": null
}
```

### 完整记录示例（notice）

```json
{
  "id": 98765,
  "title": "东方财富关于2025年度利润分配预案的公告",
  "content": "[利润分配预案] 东方财富",
  "url": "https://data.eastmoney.com/notices/detail/300059/ANNa2026040401234567.html",
  "source": "东方财富",
  "source_category": "东方财富公告",
  "news_type": "notice",
  "publish_time": "2026-04-04 00:00:00",
  "collect_time": "2026-04-04 16:30:22",
  "ai_interpretation": null,
  "ai_benefit_sectors": null,
  "ai_benefit_stocks": null,
  "ai_key_suppliers": null,
  "need_analyze": 0,
  "sentiment": null,
  "sentiment_label": null,
  "sentiment_confidence": null
}
```

---

## 附录：各分表字段对应的采集来源字段

| 统一字段 | company 来源字段 | cctv 来源字段 | caixin 来源字段 | global 来源字段 | notice 来源字段 | stock 来源字段 |
|----------|-----------------|--------------|-----------------|-----------------|-----------------|----------------|
| `title` | `新闻标题` | `title` | `title` 或 `summary[:200]` | `title` | `公告标题` | `报告名称` |
| `content` | `新闻内容` | `content` | `summary` | `summary` | `[公告类型] 名称` | `[机构] 评级:x 行业:x` |
| `url` | `新闻链接` | NULL | `url` | 构造自 `code` | `网址` | `报告PDF链接` |
| `source` | `文章来源` | `新闻联播`（固定） | `财联社`（固定） | `东方财富`（固定） | `东方财富`（固定） | `机构` |
| `publish_time` | `发布时间` | `date` | `time`（Unix ts） | `showTime` | `公告日期` | `日期` |

---

*文档由系统自动生成 · 2026-04-06*
