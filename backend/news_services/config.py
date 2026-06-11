"""
news_services/config.py — 新闻系统集中配置

将散落在各文件的硬编码配置统一管理，避免修改时遗漏。
原路径：api/news/config.py（2026-05-28 迁移至此）
"""

# ─── 采集模块配置 ──────────────────────────────────────────────────

# 各板块采集频率控制（秒）
COLLECT_INTERVAL = {
    "company": 3600,    # 1 小时
    "cls":     3600,    # 1 小时
    "global":  900,     # 15 分钟
    "cctv":    86400,   # 24 小时
    "report":  86400,   # 24 小时
}

# 采集时默认关注的股票代码
COLLECT_SYMBOLS = ["300059", "600519", "300750", "600030", "688981"]

# 采集并行线程数
COLLECT_WORKERS = 4

# 单次采集超时（秒）
COLLECT_TIMEOUT = 120


# ─── LLM 分析模块配置 ──────────────────────────────────────────────

# LLM 分析线程数
LLM_THREADS = 8

# 每批 SPOP 条数
LLM_BATCH_SIZE = 6

# 无任务时休眠秒数
LLM_IDLE_WAIT = 6

# LLM 单次请求超时
LLM_TIMEOUT = 25

# LLM 失败重试次数
LLM_MAX_RETRIES = 1


# ─── FinBERT 情感分析模块配置 ───────────────────────────────────────
# 在 LLM 之后追加 FinBERT 金融情感分析层，复用 DDL 中已预留的 4 个扩展字段：
#   title_sentiment       ← FinBERT 综合得分 = pos - neg   (-1.0 ~ 1.0)
#   title_sentiment_label ← FinBERT 三分类                 (1=正/0=中/-1=负)
#   sentiment_confidence  ← FinBERT 主类置信度 = max(p)    (0.0 ~ 1.0)
#   sentiment_volatility  ← FinBERT 概率分布归一化熵       (0.0 ~ 1.0)
# 完成标记：sentiment_confidence is not None 表示已分析（幂等）

# 总开关：False 时 LLM 直接 push 到 pending_persist，旁路 FinBERT（用于一键回滚）
# 当前因 HuggingFace 网络问题暂时关闭，待用户预先下载模型到本地后再开启
FINBERT_ENABLED = False

# FinBERT 分析线程数（CPU 多核推荐 8，GPU 建议 1）
FINBERT_THREADS = 8

# 每批拉取条数（CPU base 模型 64 一批 ~1.2s，减少总批次数 ~4x）
FINBERT_BATCH_SIZE = 64

# 无任务时休眠秒数
FINBERT_IDLE_WAIT = 6

# FinBERT 失败重试次数
FINBERT_MAX_RETRIES = 1

# 单条文本最大 token 数（128 足矣覆盖新闻情感基调，O(n²) attention 提速 ~16x）
FINBERT_MAX_TEXT_LEN = 128

# 模型路径或 huggingface 名称（中文金融情感模型）
# 已下载到本地缓存，避免每次启动联网拉模型
import os as _os
FINBERT_MODEL_NAME = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
    "models_cache", "finbert-zh",
)

# 推理设备："cpu" 或 "cuda:0"
FINBERT_DEVICE = "cpu"


# ─── 持久化模块配置 ────────────────────────────────────────────────

# 持久化执行间隔（秒）
PERSIST_INTERVAL = 5

# 每批取出条数
PERSIST_BATCH_SIZE = 200

# 批量更新失败重试次数
PERSIST_MAX_RETRIES = 2


# ─── Redis 配置 ────────────────────────────────────────────────────

# Redis 新闻数据 TTL（秒，0=永久）
NEWS_DATA_TTL = 0

# 采集时间缓存的 TTL（秒，0=永久）
COLLECT_TIME_TTL = 0


# ─── WS 推送配置 ───────────────────────────────────────────────────

# 每次 WS 推送的行动态
WS_PUSH = True

# WS 推送频道
WS_CHANNEL_NEWS = "news"
WS_CHANNEL_COLLECT = "collect"
