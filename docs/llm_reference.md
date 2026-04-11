# 量华量化平台 — 大模型（LLM）接口文档

> **模块文件**：`backend/utils/llm.py`（核心）· `backend/api/llm/routes.py`（HTTP 接口）  
> **服务提供方**：火山方舟（Volcengine ARK）  
> **更新日期**：2026-04-06

---

## 目录

1. [概览](#一概览)
2. [配置说明](#二配置说明)
3. [可用模型](#三可用模型)
4. [Python SDK 调用](#四python-sdk-调用)  
   4.1 [基础对话 chat()](#41-基础对话-chat)  
   4.2 [流式对话 stream()](#42-流式对话-stream)  
   4.3 [多轮对话 chat_with_history()](#43-多轮对话-chat_with_history)  
   4.4 [图片识别 chat_image()](#44-图片识别-chat_image)  
   4.5 [多图片识别 chat_images()](#45-多图片识别-chat_images)  
   4.6 [文件分析 chat_file()](#46-文件分析-chat_file)  
   4.7 [函数式兼容 API](#47-函数式兼容-api)
5. [HTTP REST 接口](#五http-rest-接口)  
   5.1 [POST /api/ai/chat](#51-post-apiaichat)  
   5.2 [POST /api/ai/stream](#52-post-apiaistream)  
   5.3 [GET /api/ai/models](#53-get-apiaimodels)
6. [多模态支持](#六多模态支持)
7. [错误处理](#七错误处理)
8. [注意事项与限制](#八注意事项与限制)

---

## 一、概览

`LLM` 类是火山方舟大模型的统一客户端，采用**单例模式**，整个服务进程只初始化一次。

**核心特性：**

| 特性 | 说明 |
|------|------|
| 单例 | `LLM()` 始终返回同一实例 |
| 对接配置内置 | API Key / Base URL / 默认模型全部内置，无需每次传入 |
| 多模态 | 支持文本、图片（URL/本地/Base64）、音频、视频、文档 |
| 流式输出 | `stream()` 方法，Generator 逐字 yield |
| 多轮对话 | `chat_with_history()` 传入历史消息列表 |
| 启动预热 | `warmup()` 在服务启动时自动调用，验证 API 可达性 |
| 函数式兼容 | `call_llm()` / `stream_llm()` 等函数式接口保持向后兼容 |

---

## 二、配置说明

配置来源：`backend/config/settings.py` + `backend/config/.env`

| 配置项 | 环境变量 | 默认值 | 说明 |
|--------|----------|--------|------|
| `ARK_API_KEY` | `ARK_API_KEY` | `8ac119c9-...` | 火山方舟 API 密钥 |
| `ARK_BASE_URL` | `ARK_BASE_URL` | `https://ark.cn-beijing.volces.com/api/coding` | 接口基础 URL |
| `DEFAULT_LLM_MODEL` | — | `ark-code-latest` | 默认模型（不传 model 时使用） |

**API 请求端点**：`{ARK_BASE_URL}/v1/chat/completions`

即：`https://ark.cn-beijing.volces.com/api/coding/v1/chat/completions`

**认证方式**：HTTP Header `Authorization: Bearer {api_key}`

---

## 三、可用模型

| 模型 ID | 显示名 | 特点 |
|---------|--------|------|
| `ark-code-latest` | Auto（智能选模型） | **默认模型**，自动路由到最优模型 |
| `doubao-seed-code` | 豆包 Seed Code | 字节跳动代码优化模型 |
| `doubao-seed-2.0-code` | 豆包 Seed 2.0 Code | 豆包第二代代码模型 |
| `doubao-seed-2.0-pro` | 豆包 Seed 2.0 Pro | 豆包旗舰版，综合能力强 |
| `doubao-seed-2.0-lite` | 豆包 Seed 2.0 Lite | 豆包轻量版，速度快 |
| `deepseek-v3.2` | DeepSeek V3.2 | 深度求索，推理分析能力强 |
| `glm-4.7` | GLM 4.7 | 智谱 AI，中文理解出色 |
| `kimi-k2.5` | Kimi K2.5 | Moonshot，长上下文支持好 |
| `minimax-m2.5` | MiniMax M2.5 | MiniMax，文学写作能力强 |

---

## 四、Python SDK 调用

### 4.1 基础对话 `chat()`

**函数签名**

```python
def chat(
    self,
    prompt: str = "",
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    messages: list[dict] | None = None,
    images: list[str] | None = None,
    files: list[str] | None = None,
    **extra,
) -> str
```

**参数说明**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | str | ❌ | `""` | 用户输入的文本消息 |
| `model` | str\|None | ❌ | `None`（使用 `ark-code-latest`） | 指定模型 ID，见第三节 |
| `system_prompt` | str\|None | ❌ | `None` | 系统提示词，设定 AI 角色和行为规范 |
| `temperature` | float | ❌ | `0.7` | 采样温度，范围 `[0, 2]`：越低输出越确定，越高越随机 |
| `max_tokens` | int | ❌ | `4096` | 最大生成 token 数，上限由模型决定 |
| `messages` | list\|None | ❌ | `None` | 自定义完整消息列表（传入后 `prompt` / `system_prompt` / `images` / `files` 均被忽略） |
| `images` | list\|None | ❌ | `None` | 图片列表（URL / 本地路径 / Base64 Data URI） |
| `files` | list\|None | ❌ | `None` | 文件列表（本地路径，支持图片/音频/视频/文档） |
| `**extra` | dict | ❌ | — | 额外请求参数（如 `top_p`、`frequency_penalty`） |

**返回值**：`str`，模型回复文本

**使用示例**

```python
from utils.llm import LLM

llm = LLM()

# 最简调用
result = llm.chat("分析东方财富最近的走势")
print(result)

# 指定模型 + 系统提示词
result = llm.chat(
    prompt="300059今日成交量异常，请分析原因",
    model="deepseek-v3.2",
    system_prompt="你是一位专业的A股量化分析师，回答简洁专业",
    temperature=0.5,
    max_tokens=2000,
)

# 使用自定义 messages
result = llm.chat(messages=[
    {"role": "system", "content": "你是一名股票分析师"},
    {"role": "user", "content": "什么是MACD指标？"},
])
```

---

### 4.2 流式对话 `stream()`

**函数签名**

```python
def stream(
    self,
    prompt: str = "",
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    messages: list[dict] | None = None,
    images: list[str] | None = None,
    files: list[str] | None = None,
    **extra,
) -> Generator[str, None, None]
```

**参数说明**：与 `chat()` 完全相同，见 4.1。

**返回值**：`Generator[str, None, None]`，逐字符 / 逐词 yield 文本片段。

**使用示例**

```python
from utils.llm import LLM

llm = LLM()

# 逐字打印
for chunk in llm.stream("请分析贵州茅台的护城河"):
    print(chunk, end="", flush=True)
print()  # 换行

# 拼接完整内容
full_text = ""
for chunk in llm.stream("你好", model="glm-4.7"):
    full_text += chunk
```

---

### 4.3 多轮对话 `chat_with_history()`

**函数签名**

```python
def chat_with_history(
    self,
    message: str,
    history: list[dict] | None = None,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    images: list[str] | None = None,
    files: list[str] | None = None,
    **extra,
) -> str
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `message` | str | ✅ | 当前用户消息 |
| `history` | list\|None | ❌ | 历史消息列表，格式 `[{"role": "user/assistant", "content": "..."}]` |
| 其余参数 | — | — | 同 `chat()` |

**消息列表格式**

```python
history = [
    {"role": "user",      "content": "什么是均线？"},
    {"role": "assistant", "content": "均线是指..."},
    {"role": "user",      "content": "MA5和MA20有什么区别？"},
    {"role": "assistant", "content": "MA5是5日均线..."},
]
```

**使用示例**

```python
from utils.llm import LLM

llm = LLM()

history = []
while True:
    user_input = input("你: ")
    if not user_input:
        break
    
    response = llm.chat_with_history(
        message=user_input,
        history=history,
        system_prompt="你是量化交易助手",
    )
    print(f"AI: {response}")
    
    # 更新历史
    history.append({"role": "user",      "content": user_input})
    history.append({"role": "assistant", "content": response})
```

---

### 4.4 图片识别 `chat_image()`

**功能说明**：单张图片识别快捷方法，底层调用 `chat()` 并传入 `images=[image]`。

**函数签名**

```python
def chat_image(
    self,
    prompt: str,
    image: str,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    **extra,
) -> str
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `prompt` | str | ✅ | 提问文本，如 "描述这张K线图" |
| `image` | str | ✅ | 图片来源（见下表） |

**image 参数支持格式**

| 格式 | 示例 |
|------|------|
| HTTP/HTTPS URL | `"https://example.com/chart.png"` |
| 本地文件路径 | `"D:/images/kline.jpg"` |
| Base64 Data URI | `"data:image/png;base64,iVBORw..."` |

**使用示例**

```python
from utils.llm import LLM

llm = LLM()

# URL 图片
result = llm.chat_image(
    prompt="分析这张K线图的技术形态",
    image="https://example.com/kline_300059.png",
    system_prompt="你是专业的技术分析师",
)

# 本地图片
result = llm.chat_image(
    prompt="这张截图显示了什么股票行情？",
    image="D:/screenshots/chart.png",
)
```

---

### 4.5 多图片识别 `chat_images()`

**函数签名**

```python
def chat_images(
    self,
    prompt: str,
    images: list[str],
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    **extra,
) -> str
```

**使用示例**

```python
from utils.llm import LLM

llm = LLM()

result = llm.chat_images(
    prompt="对比这两张K线图，哪只股票走势更强？",
    images=[
        "D:/charts/300059.png",
        "D:/charts/600519.png",
    ],
)
```

---

### 4.6 文件分析 `chat_file()`

**功能说明**：文件分析快捷方法，自动检测文件 MIME 类型并转为对应格式传给模型。

**函数签名**

```python
def chat_file(
    self,
    prompt: str,
    file_path: str,
    model: str | None = None,
    system_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    **extra,
) -> str
```

**file_path 支持的文件类型**

| 类型 | 扩展名 | 处理方式 |
|------|--------|----------|
| 图片 | `.jpg` `.jpeg` `.png` `.gif` `.webp` `.bmp` | Base64 内联 `image_url` |
| 音频 | `.mp3` `.wav` `.m4a` `.flac` `.ogg` | Base64 内联 `input_audio` |
| 视频 | `.mp4` `.webm` `.avi` `.mov` | Base64 内联 `image_url` |
| 文档 | `.pdf` `.docx` `.txt` `.csv` `.xlsx` | 文本附件（部分 Base64 截断） |

**使用示例**

```python
from utils.llm import LLM

llm = LLM()

# 分析财报图片
result = llm.chat_file(
    prompt="分析这份财报中的关键财务指标",
    file_path="D:/reports/annual_report_2025.pdf",
    system_prompt="你是财务分析专家，重点关注营收、利润和现金流",
)

# 分析音频
result = llm.chat_file(
    prompt="这段会议录音讨论了哪些主要内容？",
    file_path="D:/audio/meeting_20260404.mp3",
)
```

---

### 4.7 函数式兼容 API

> 为旧代码提供向后兼容的函数式接口，底层调用同一个 `LLM()` 单例。

```python
from utils.llm import call_llm, stream_llm, call_llm_with_history, warmup

# 非流式调用
result: str = call_llm(
    prompt="分析东方财富",
    model="deepseek-v3.2",
    system_prompt="你是股票分析师",
    temperature=0.7,
    max_tokens=2000,
    messages=None,       # 传入后 prompt/system_prompt 失效
    images=None,
    files=None,
)

# 流式调用（Generator）
for chunk in stream_llm(prompt="讲个笑话"):
    print(chunk, end="")

# 带历史上下文调用
result = call_llm_with_history(
    message="继续分析",
    history=[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
    model=None,
    system_prompt=None,
    temperature=0.7,
    max_tokens=4096,
)

# 手动触发预热（通常无需调用，服务启动时自动执行）
warmup()
```

---

## 五、HTTP REST 接口

### 5.1 POST /api/ai/chat

非流式对话，请求/响应经 Pydantic 校验，推荐使用。

**请求 URL**：`POST http://127.0.0.1:8001/api/ai/chat`

**请求体**

```json
{
  "message":       "东方财富近期走势分析",
  "model":         "deepseek-v3.2",
  "system_prompt": "你是专业股票分析师",
  "temperature":   0.7,
  "max_tokens":    4096,
  "history": [
    {"role": "user",      "content": "什么是MACD？"},
    {"role": "assistant", "content": "MACD是移动平均收敛散度..."}
  ]
}
```

**请求字段说明**

| 字段 | 类型 | 必填 | 验证规则 | 说明 |
|------|------|------|----------|------|
| `message` | string | ✅ | 最少 1 字符 | 当前用户输入 |
| `model` | string\|null | ❌ | — | 模型 ID，null 使用默认 |
| `system_prompt` | string\|null | ❌ | — | 系统提示词 |
| `temperature` | float | ❌ | `[0, 2]`，默认 `0.7` | 采样温度 |
| `max_tokens` | integer | ❌ | `[1, 32768]`，默认 `4096` | 最大 token 数 |
| `history` | array\|null | ❌ | 元素格式 `{role, content}` | 历史消息（有则启用多轮模式） |

**成功响应（200）**

```json
{
  "success": true,
  "model":   "deepseek-v3.2",
  "content": "从技术面来看，东方财富（300059）...",
  "error":   null
}
```

**失败响应**

```json
{
  "detail": "LLM 调用失败: Connection timeout"
}
```

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | message 为空 / 参数校验失败 |
| 500 | LLM 内部调用失败 |

---

### 5.2 POST /api/ai/stream

流式对话，SSE 协议。

**请求 URL**：`POST http://127.0.0.1:8001/api/ai/stream`

**请求体**：与 5.1 完全相同。

**SSE 事件流**

```
data: {"content": "从"}
data: {"content": "技"}
data: {"content": "术"}
data: {"content": "面"}
data: {"content": "来看"}
data: [DONE]
```

**出错时**

```
data: {"error": "LLM 调用失败: ..."}
```

**客户端示例（JavaScript）**

```javascript
const response = await fetch('http://127.0.0.1:8001/api/ai/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: '分析东方财富',
    model: 'deepseek-v3.2',
  }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const text = decoder.decode(value);
  const lines = text.split('\n');
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      if (data === '[DONE]') break;
      const { content } = JSON.parse(data);
      process.stdout.write(content);
    }
  }
}
```

**响应 Headers**

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

---

### 5.3 GET /api/ai/models

获取可用模型列表。

**请求 URL**：`GET http://127.0.0.1:8001/api/ai/models`

**响应（200）**

```json
[
  {
    "id":          "ark-code-latest",
    "name":        "Auto（智能选模型）",
    "description": ""
  },
  {
    "id":          "deepseek-v3.2",
    "name":        "DeepSeek V3.2",
    "description": ""
  }
]
```

---

## 六、多模态支持

### 图片输入

支持三种方式混用：

```python
llm = LLM()

# 1. HTTP URL（直接引用，不上传到服务器）
result = llm.chat(
    prompt="这张图显示了什么？",
    images=["https://example.com/chart.png"],
)

# 2. 本地文件路径（自动读取并转为 Base64）
result = llm.chat(
    prompt="分析这张K线图",
    images=["D:/charts/kline.jpg"],
)

# 3. Base64 Data URI（已编码）
import base64
with open("D:/charts/kline.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
result = llm.chat(
    prompt="分析这张图",
    images=[f"data:image/jpeg;base64,{b64}"],
)

# 4. 多图混用
result = llm.chat(
    prompt="对比这两张图",
    images=[
        "https://example.com/a.png",
        "D:/local/b.jpg",
    ],
)
```

### 音频输入

```python
llm = LLM()

# 本地音频文件（自动转为 input_audio 格式）
result = llm.chat_file(
    prompt="这段录音的主要内容是什么？",
    file_path="D:/audio/meeting.mp3",
)
```

支持格式：`.mp3` `.wav` `.m4a` `.flac` `.ogg` `.webm`

### 多模态 + 历史消息

如果需要在多轮对话中传入图片，使用 `chat_with_history()` 并传 `images` 参数：

```python
history = [
    {"role": "user",      "content": "你好，我想分析股票"},
    {"role": "assistant", "content": "好的，请告诉我您想分析哪只股票"},
]

result = llm.chat_with_history(
    message="帮我分析这张K线图的技术形态",
    history=history,
    images=["D:/charts/kline_300059.png"],
)
```

---

## 七、错误处理

### 常见异常

| 异常类型 | 触发场景 | 处理建议 |
|----------|----------|----------|
| `requests.exceptions.Timeout` | API 请求超时（默认 120s） | 重试，或降低 `max_tokens` |
| `requests.exceptions.HTTPError` | HTTP 4xx / 5xx | 检查 API Key 和 quota |
| `ValueError: ARK API Error` | 模型返回错误 | 检查请求参数，模型 ID 是否正确 |
| `ValueError: 解析 API 响应失败` | 响应格式异常 | 联系方舟平台 |

### 推荐错误处理

```python
from utils.llm import LLM
import requests

llm = LLM()

try:
    result = llm.chat("分析东方财富")
except requests.exceptions.Timeout:
    print("LLM 请求超时，请稍后重试")
except requests.exceptions.HTTPError as e:
    print(f"HTTP 错误: {e.response.status_code}")
except ValueError as e:
    print(f"API 返回错误: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

---

## 八、注意事项与限制

### 请求限制

| 项目 | 限制 |
|------|------|
| 默认超时 | 120 秒 |
| 默认 `max_tokens` | 4096 |
| 最大 `max_tokens`（HTTP 接口校验） | 32768 |
| `temperature` 范围（HTTP 接口校验） | `[0, 2]` |

### 模型选用建议

| 场景 | 推荐模型 |
|------|----------|
| 股票分析、量化策略 | `deepseek-v3.2` |
| 中文新闻解读 | `glm-4.7` 或 `ark-code-latest` |
| 长文档分析 | `kimi-k2.5` |
| 快速响应（轻量） | `doubao-seed-2.0-lite` |
| 代码生成 | `doubao-seed-code` 或 `ark-code-latest` |

### 多模态注意事项

1. **图片大小**：本地图片建议小于 5MB，过大会影响响应速度
2. **音视频**：文件读取后全部编码为 Base64，大文件（>10MB）可能导致请求超时
3. **文档类型**：`.pdf` / `.docx` 等文件当前以文本附件形式传入，仅截取前 100 字节 Base64，**实际内容有限**，建议先提取文本再传 `prompt`

### 单例与线程安全

- `LLM()` 是线程安全的单例，多线程环境可直接共用
- `chat()` 和 `chat_with_history()` 是**同步阻塞**调用，在 FastAPI 的 `async def` 路由中需注意不要阻塞事件循环（当前 `/api/ai/chat` 和 `/api/ai/stream` 均已正确处理）

---

*文档由系统自动生成 · 2026-04-06*
