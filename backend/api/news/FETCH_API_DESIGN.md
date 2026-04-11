# 新闻数据查询接口设计文档

## 核心约束
- 不改动原有框架
- 最高效
- 无漏洞
- 前后端稳定交互

---

## 一、接口设计（2个核心接口）

### 1. 全量拉取接口

```
GET /api/news/fetch
```

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| date | string | 否 | 今天 | 日期，格式 YYYY-MM-DD |
| sections | string | 否 | 全部 | 板块列表，逗号分隔（company,cls,global,report,cctv） |
| limit | int | 否 | 500 | 每板块返回条数限制（1-1000） |
| auto_collect | bool | 否 | true | 无数据时是否自动触发采集 |

**响应格式：**

```json
{
  "status": "success",
  "date": "2026-04-08",
  "is_today": true,
  "sections": {
    "company": {
      "status": "success",
      "section": "company",
      "section_name": "公司动态",
      "date": "2026-04-08",
      "is_today": true,
      "data_source": "redis",
      "count": 10,
      "data": [...],
      "message": null
    },
    "cls": { ... },
    "global": { ... },
    "report": { ... }
  },
  "total_count": 150,
  "message": null
}
```

### 2. 单板块独立获取接口

```
GET /api/news/fetch/{section}
```

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| section | string | 新闻板块（company/cls/global/report/cctv） |

**查询参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| date | string | 否 | 今天 | 日期，格式 YYYY-MM-DD |
| limit | int | 否 | 500 | 返回条数限制（1-1000） |
| auto_collect | bool | 否 | true | 无数据时是否自动触发采集 |

**响应格式：**

```json
{
  "status": "success",
  "section": "company",
  "section_name": "公司动态",
  "date": "2026-04-08",
  "is_today": true,
  "data_source": "redis",
  "count": 10,
  "data": [
    {
      "id": 1,
      "title": "新闻标题",
      "content": "新闻内容",
      "url": "https://...",
      "source": "东方财富",
      "news_type": "company",
      "publish_time": "2026-04-08 10:00:00",
      "ai_interpretation": "AI解读",
      "ai_event_type": "财报",
      "ai_impact_level": 4,
      "ai_impact_direction": 1,
      "sentiment": 0.8,
      "_source": "redis",
      "_table_name": "news_company_202604"
    }
  ],
  "message": null
}
```

---

## 二、核心数据流向（最优解架构）

### 1. 当日/实时数据

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   前端请求   │────▶│  接口层判断  │────▶│  Redis读取  │
│  date=今天   │     │  is_today   │     │ news:data:* │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                       ┌────────────────────────┘
                       ▼
              ┌─────────────────┐
              │  有数据 → 返回   │
              │  无数据 → 触发采集│
              └─────────────────┘
```

- **来源**：Redis
- **Key**：`news:data:{table_name}:{id}`
- **规则**：只保留当日有效数据

### 2. 历史/非当日数据

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   前端请求   │────▶│  接口层判断  │────▶│  MySQL查询  │
│  date<今天   │     │  is_today   │     │  对应分表    │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                       ┌────────────────────────┘
                       ▼
              ┌─────────────────┐
              │  直接返回数据    │
              │  不触发采集     │
              └─────────────────┘
```

- **来源**：MySQL
- **规则**：Redis不存储历史数据，只从数据库读取

### 3. 数据不存在处理逻辑

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  查询无数据  │────▶│  判断日期    │────▶│  当日:触发采集 │
│             │     │             │     │  历史:返回空  │
└─────────────┘     └─────────────┘     └─────────────┘
```

- 前端请求指定日期/板块 → 检查MySQL
- 有数据 → 直接返回数据库数据
- 无数据 → 直接触发现有的新闻采集逻辑（仅当日）

---

## 三、最终统一返回逻辑

1. **当日数据** → Redis读取返回
2. **历史数据** → MySQL读取返回
3. **缺失数据** → 直接触发现有的新闻采集逻辑 → 返回
4. **所有接口返回格式完全统一**
5. **LLM结果通过通信机制推送到前端**
6. **前端只对接一套数据结构，无需改动**

---

## 四、架构规则（强约束）

1. **Redis只承担**：当日数据、实时数据、LLM分析数据
2. **MySQL承担**：历史数据、持久化存储
3. **接口统一封装**：自动判断日期 → 自动选择数据源
4. **前端永远只接收一套标准结构**
5. **数据源切换对前端完全透明**
6. **不改动原有框架、不改动视图、不改动后端核心逻辑**

---

## 五、状态码说明

| status | 含义 | 说明 |
|--------|------|------|
| success | 成功 | 正常返回数据 |
| empty | 空数据 | 该日期/板块暂无数据 |
| collecting | 采集中 | 已触发采集，数据正在获取中 |
| error | 错误 | 请求失败或参数错误 |

---

## 六、使用示例

### 获取当日全部板块新闻

```bash
curl "http://localhost:8001/api/news/fetch"
```

### 获取指定日期全部板块

```bash
curl "http://localhost:8001/api/news/fetch?date=2026-04-07"
```

### 获取当日指定板块

```bash
curl "http://localhost:8001/api/news/fetch?sections=company,cls"
```

### 获取单板块数据

```bash
curl "http://localhost:8001/api/news/fetch/company?date=2026-04-08&limit=100"
```

### 获取历史数据（不触发采集）

```bash
curl "http://localhost:8001/api/news/fetch?date=2026-04-01&auto_collect=false"
```

---

## 七、文件清单

### 新增文件
- `backend/api/news/fetch_routes.py` - 新闻数据查询接口模块

### 修改文件
- `backend/utils/akshare.py` - 新增 `collect_section()` 函数
- `backend/main.py` - 注册新的路由
