# LLM分析接口 - 完整说明

## 📋 接口基本信息

### 1. 核心接口：上市公司LLM分析
- **接口地址**: `GET /api/stock/{symbol}/llm-analysis`
- **完整URL**: `http://localhost:8001/api/stock/{symbol}/llm-analysis`
- **接口类型**: GET
- **路由前缀**: `/api` (已在 `stock_router` 中定义)

### 2. 其他相关接口
- **清除会话**: `POST /api/llm/clear-session`
- **服务统计**: `GET /api/llm/stats`

---

## 🔧 请求参数说明

### 路径参数 (Path Parameters)
| 参数名 | 必填 | 说明 | 示例 |
|--------|------|------|------|
| `symbol` | ✅ | 股票代码 | `300063`, `000001.SZ`, `603777.SH` |

### 查询参数 (Query Parameters)
| 参数名 | 必填 | 类型 | 默认值 | 说明 | 示例 |
|--------|------|------|--------|------|------|
| `session_id` | ✅ | string | - | 会话ID，用于维护对话上下文 | `481a1081-83ae-424b-904b-d2d2a3aa3fe7` |
| `name` | ❌ | string | - | 股票名称，提供更准确的LLM分析 | `天龙集团` |
| `use_cache` | ❌ | string | `true` | 是否使用缓存（从stocks_info表读取） | `true` 或 `false` |

---

## 📊 响应格式

### 成功响应示例 (HTTP 200)
```json
{
  "success": true,
  "data": {
    "main_business": "公司主要从事互联网营销业务，提供搜索引擎营销、信息流广告、品牌整合营销等服务...",
    "is_state_owned": false,
    "actual_controller": "冯毅",
    "transformation_trend": "近年来持续向互联网营销业务转型...",
    "revenue": 102.5,
    "net_profit": 0.5,
    "pe_ratio": 50.2,
    "pb_ratio": 2.1
  },
  "error": null,
  "session_id": "481a1081-83ae-424b-904b-d2d2a3aa3fe7",
  "symbol": "300063",
  "cache_hit": false,
  "latency_ms": 9327,
  "cache_latency_ms": 14,
  "llm_latency_ms": 9313
}
```

### 失败响应示例
```json
{
  "success": false,
  "data": null,
  "error": "LLM调用超时",
  "session_id": "481a1081-83ae-424b-904b-d2d2a3aa3fe7",
  "symbol": "300063",
  "cache_hit": false,
  "latency_ms": 45000,
  "cache_latency_ms": 10,
  "llm_latency_ms": 0
}
```

---

## 🚀 快速测试命令

### 1. 使用curl测试
```bash
# 基本测试 (不提供股票名称)
curl -X GET "http://localhost:8001/api/stock/300063/llm-analysis?session_id=481a1081-83ae-424b-904b-d2d2a3aa3fe7&use_cache=true"

# 完整测试 (提供股票名称)
curl -X GET "http://localhost:8001/api/stock/300063/llm-analysis?session_id=481a1081-83ae-424b-904b-d2d2a3aa3fe7&name=天龙集团&use_cache=true"

# 不使用缓存
curl -X GET "http://localhost:8001/api/stock/300063/llm-analysis?session_id=481a1081-83ae-424b-904b-d2d2a3aa3fe7&name=天龙集团&use_cache=false"
```

### 2. 使用Python测试
```python
import requests
import uuid

# 配置参数
symbol = "300063"
session_id = str(uuid.uuid4())
url = f"http://localhost:8001/api/stock/{symbol}/llm-analysis"

# 发送请求
response = requests.get(url, params={
    "session_id": session_id,
    "name": "天龙集团",
    "use_cache": "true"
}, timeout=60)

# 处理响应
if response.status_code == 200:
    result = response.json()
    if result["success"]:
        print("分析成功:", result["data"])
    else:
        print("分析失败:", result["error"])
else:
    print("请求失败:", response.status_code)
```

---

## 🗄️ 数据存储映射

LLM分析结果会自动更新到现有的 `stocks_info` 表中：

| LLM字段 | stocks_info表字段 | 说明 |
|---------|-------------------|------|
| `main_business` | `main_business` | 主营业务 |
| `is_state_owned` | `is_state_owned` | 是否国企 |
| `actual_controller` | `actual_controller` | 实际控制人 |
| `transformation_trend` | `introduction` | 转型趋势合并到公司简介 |
| `revenue` | `revenue` | 营收（亿元） |
| `net_profit` | `net_profit` | 净利润（亿元） |
| `pe_ratio` | `pe_ttm` | 市盈率 → 滚动市盈率 |
| `pb_ratio` | `pb` | 市净率 |

---

## ⚙️ 核心特性

### 1. 高性能架构
- **异步非阻塞**: 全链路 async/await，支持高并发
- **智能缓存**: 30天有效期，基于 `stocks_info.update_time` 字段
- **连接池**: 数据库连接池，避免频繁创建连接

### 2. 会话管理
- **上下文复用**: 每个 `session_id` 独立维护对话历史
- **自动注销**: 内存会话超时清理（默认30分钟）
- **历史限制**: 最多保留最近20轮对话

### 3. 容错机制
- **重试策略**: 指数退避重试，最大3次
- **超时控制**: LLM调用总超时45秒
- **JSON解析降级**: 自动清理和修复LLM返回的非标准JSON

### 4. 安全保护
- **输入验证**: 股票代码和会话ID格式验证
- **并发控制**: 可选的信号量限流（默认10并发）
- **错误隔离**: 单个请求失败不影响其他请求

---

## 🔍 常见问题排查

### 问题1: 404错误 (接口不存在)
**可能原因**:
1. 后端服务未启动
2. 路由未正确注册
3. 服务器未加载新的代码

**解决方案**:
```bash
# 1. 检查服务器是否运行
netstat -ano | findstr :8001

# 2. 重启服务器
cd backend
python main.py

# 3. 检查路由是否注册
访问 http://localhost:8001/docs 查看所有接口
```

### 问题2: 500错误 (服务器内部错误)
**可能原因**:
1. 数据库连接问题
2. LLM服务不可用
3. 代码逻辑错误

**解决方案**:
1. 检查数据库是否正常运行
2. 检查LLM服务配置
3. 查看服务器日志

### 问题3: 连接被拒绝
**可能原因**:
1. 服务器未启动
2. 防火墙阻止
3. 端口被占用

**解决方案**:
```bash
# 1. 启动后端服务
cd backend && python main.py

# 2. 检查端口占用
netstat -ano | findstr :8001

# 3. 检查防火墙
# Windows: 控制面板 → 系统和安全 → Windows Defender 防火墙
```

---

## 📈 性能指标

### 首次分析 (无缓存)
- **总耗时**: ~9-12秒
- **LLM调用耗时**: ~9-11秒
- **缓存查询耗时**: ~10-20ms

### 缓存命中
- **总耗时**: ~10-50ms
- **LLM调用耗时**: 0ms
- **缓存查询耗时**: ~10-20ms

### 并发性能
- **默认并发限制**: 10个LLM调用
- **内存会话**: 自动清理，无内存泄漏
- **数据库连接**: 连接池管理，高效复用

---

## 🎯 使用建议

### 1. 会话ID管理
- **建议使用UUID**: 确保唯一性
- **长期会话**: 同一用户使用固定会话ID
- **临时会话**: 一次性分析使用临时会话ID

### 2. 缓存策略
- **首次分析**: 建议使用缓存 (use_cache=true)
- **实时数据**: 需要最新数据时禁用缓存 (use_cache=false)
- **缓存失效**: 基于 `stocks_info.update_time` 自动失效

### 3. 错误处理
- **超时处理**: 设置合理的超时时间 (建议60秒)
- **重试机制**: 失败时自动重试，无需手动重试
- **降级策略**: JSON解析失败时返回原始响应

---

## 📁 文件位置

### 1. 核心实现文件
- `backend/api/stock/services/stock_llm.py` - LLM分析框架核心
- `backend/api/stock/routes.py` - API接口定义 (第748-897行)

### 2. 相关配置文件
- `backend/main.py` - 主应用入口，路由注册
- `backend/utils/llm.py` - 现有LLM调用模块

### 3. 测试文件
- `test_curl_commands.txt` - curl测试命令
- `restart_server.py` - 服务器重启脚本
- `LLM分析接口说明.md` - 本文档

---

## ✅ 验证步骤

1. **启动服务器**: 确保后端服务在端口8001运行
2. **访问文档**: 打开 http://localhost:8001/docs
3. **查找接口**: 在文档中找到 `/api/stock/{symbol}/llm-analysis`
4. **测试接口**: 使用提供的curl或Python代码测试
5. **验证数据**: 检查 `stocks_info` 表是否更新

---

## 🔄 更新日志

### 2026-04-14
- ✅ 创建LLM分析框架核心实现
- ✅ 适配现有 `stocks_info` 表结构
- ✅ 添加完整的API接口
- ✅ 实现智能缓存和会话管理
- ✅ 完成功能测试 (股票300063)

---

## 📞 技术支持

如果遇到问题，请检查：
1. 服务器日志
2. 数据库连接状态
3. LLM服务可用性
4. 路由注册情况

接口已就绪，可以开始使用！ 🚀