# 新闻系统 Bug 修复总结

## 问题描述

数据库中 `news_company_202604`, `news_cls_202604`, `news_report_202604` 表的新闻没有获得 AI 分析结果，Redis 中 `news:data:*` 数据显示 497 条（实际应该是 727 条以上）。

## 根本原因

### 1. 跨表 ID 冲突问题（主要问题）

不同新闻表的 ID 都是从 1 开始的自增 ID：
- company: id 1-5
- cls: id 1-10
- report: id 1-29
- global: id 1-727

原 Redis key 格式为 `news:data:{id}`，导致不同表的相同 ID 会互相覆盖。

### 2. 历史数据未同步到 Redis

数据库中的 company/cls/report 新闻是在 2026-04-08 重构之前采集的，当时还没有写入 Redis 的逻辑。新架构代码只处理了 global 新闻。

### 3. LLM 分析层丢失 table_name

LLM 分析完成后写回 Redis 的数据缺少 `table_name` 字段，导致持久化层无法正确更新数据库。

## 修复内容

### 1. 修改 Redis Key 格式（utils/redis_client.py）

- 新增 `_get_news_data_key()` 函数，生成包含 table_name 的 key
- `news_data_set()` / `news_data_get()` / `news_data_update()` 支持使用 table_name 构建 key
- `news_data_batch_get()` 支持批量使用 table_names 构建 key
- Key 格式从 `news:data:{id}` 改为 `news:data:{table_name}:{id}`

### 2. 修改 pending_llm 队列格式（utils/redis_client.py）

- 新增 `_pack_pending_item()` / `_unpack_pending_item()` 函数
- `pending_llm_add()` / `pending_llm_add_batch()` 支持存储 table_name
- `pending_llm_spop()` 返回格式为 `"table_name:news_id"` 的字符串
- `pending_persist_push()` / `pending_persist_push_batch()` / `pending_persist_pop_batch()` 同样支持 table_name

### 3. 修改 LLM 分析层（api/news/news_llm_analyzer.py）

- `_process_once()` 使用 `_unpack_pending_item()` 解包获取 table_name
- 使用 table_name 读取正确的 Redis key
- 写回 Redis 时保留 table_name
- 推入 pending_persist 时传入 table_names

### 4. 修改持久化层（api/news/news_persist.py）

- `_persist_once()` 使用 `_unpack_pending_item()` 解包获取 table_name
- 使用 table_names 批量读取 Redis
- 失败时放回队列使用正确的 table_name

### 5. 修改采集层（utils/akshare.py）

- `_push_news_to_redis_v2()` 推入 pending_llm 时传入 table_names

### 6. 创建修复脚本（fix_news_redis.py）

将数据库中已有但 Redis 中没有的新闻重新推入 Redis 和 pending_llm 队列。

## 修复后状态

- Redis news:data:* 总数: 42
  - company: 5
  - cls: 8
  - report: 29
- pending_llm: 42 条待分析
- pending_persist: 0 条

## 后续建议

1. 启动后端服务，LLM 8线程分析器会自动处理 pending_llm 队列中的新闻
2. 持久化层每 5 秒会将分析结果写入数据库
3. 新采集的新闻会自动使用新的 key 格式
