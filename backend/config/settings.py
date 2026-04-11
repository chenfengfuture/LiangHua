"""
config/settings.py — 量华平台主配置

所有非私密配置集中于此。
私密配置（密码、API Key）从 config/.env 加载。
"""

import os
from pathlib import Path

# ─── .env 文件路径 ──────────────────────────────────────────────────
_ENV_FILE = Path(__file__).parent / ".env"

# ─── 加载 .env（简易实现，不引入 python-dotenv 依赖）──────────────
def _load_env(path: Path):
    """从 .env 文件加载环境变量（不覆盖已有的系统环境变量）"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key not in os.environ:
                os.environ[key] = value

_load_env(_ENV_FILE)


# ═══════════════════════════════════════════════════════════════════
#  服务配置
# ═══════════════════════════════════════════════════════════════════

# FastAPI 服务端口
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8001

# CORS
CORS_ORIGINS = ["*"]


# ═══════════════════════════════════════════════════════════════════
#  数据库配置
# ═══════════════════════════════════════════════════════════════════

# ─── 主库：量化行情（lianghua）────────────────────────────────
DB_HOST     = os.environ.get("DB_HOST",     "127.0.0.1")
DB_PORT     = int(os.environ.get("DB_PORT",   "3306"))
DB_USER     = os.environ.get("DB_USER",     "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "042018")
DB_NAME     = os.environ.get("DB_NAME",     "lianghua")
DB_CHARSET  = os.environ.get("DB_CHARSET",  "utf8mb4")

# 完整 DB_CONFIG 字典（兼容 pymysql.connect / PooledDB）
DB_CONFIG = {
    "host":         DB_HOST,
    "port":         DB_PORT,
    "user":         DB_USER,
    "password":     DB_PASSWORD,
    "database":     DB_NAME,
    "charset":      DB_CHARSET,
    # 每条连接建立后立即设置字符集与排序规则，确保中文/emoji 不乱码
    "init_command": "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
    "cursorclass":  None,  # 由调用方按需设置
}

# ─── 新闻数据库（news_data）──────────────────────────────────
NEWS_DB_HOST     = os.environ.get("NEWS_DB_HOST",     "127.0.0.1")
NEWS_DB_PORT     = int(os.environ.get("NEWS_DB_PORT",   "3306"))
NEWS_DB_USER     = os.environ.get("NEWS_DB_USER",     "root")
NEWS_DB_PASSWORD = os.environ.get("NEWS_DB_PASSWORD", "042018")
NEWS_DB_NAME     = os.environ.get("NEWS_DB_NAME",     "news_data")
NEWS_DB_CHARSET  = os.environ.get("NEWS_DB_CHARSET",  "utf8mb4")

# news_data 数据库连接配置字典
NEWS_DB_CONFIG = {
    "host":         NEWS_DB_HOST,
    "port":         NEWS_DB_PORT,
    "user":         NEWS_DB_USER,
    "password":     NEWS_DB_PASSWORD,
    "database":     NEWS_DB_NAME,
    "charset":      NEWS_DB_CHARSET,
    # 每条连接建立后立即设置字符集，确保中文/emoji 正确存取
    "init_command": "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
    "cursorclass":  None,  # 由调用方按需设置
}

# news_data 连接池参数（新闻库，读写均衡）
NEWS_DB_POOL_CONFIG = {
    "maxconnections": 8,
    "mincached":      2,
    "maxcached":      4,
    "maxshared":      0,
    "blocking":       True,
    "ping":           4,
}

# 数据库连接池参数
DB_POOL_CONFIG = {
    "maxconnections": 10,
    "mincached":      3,
    "maxcached":      6,
    "maxshared":      0,
    "blocking":       True,
    "ping":           4,
}

# 采集器专用连接池（并发更高）
DB_POOL_CONFIG_COLLECTOR = {
    "maxconnections": 16,
    "mincached":      4,
    "maxcached":      8,
    "maxshared":      0,
    "blocking":       True,
    "ping":           4,
}


# ═══════════════════════════════════════════════════════════════════
#  火山方舟大模型配置
# ═══════════════════════════════════════════════════════════════════

ARK_API_KEY  = os.environ.get("ARK_API_KEY",  "8ac119c9-5b43-4523-bc54-d763e79386a8")
ARK_BASE_URL = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/coding")

DEFAULT_LLM_MODEL = "ark-code-latest"

AVAILABLE_LLM_MODELS = {
    "ark-code-latest":    "Auto（智能选模型）",
    "doubao-seed-code":   "豆包 Seed Code",
    "doubao-seed-2.0-code": "豆包 Seed 2.0 Code",
    "doubao-seed-2.0-pro":  "豆包 Seed 2.0 Pro",
    "doubao-seed-2.0-lite": "豆包 Seed 2.0 Lite",
    "deepseek-v3.2":      "DeepSeek V3.2",
    "glm-4.7":            "GLM 4.7",
    "kimi-k2.5":          "Kimi K2.5",
    "minimax-m2.5":       "MiniMax M2.5",
}


# ═══════════════════════════════════════════════════════════════════
#  采集器配置
# ═══════════════════════════════════════════════════════════════════

COLLECT_WORKERS   = 8      # 并发线程数
COLLECT_BATCH     = 50     # 每批 DB INSERT 的股票数
COLLECT_BARS      = 3      # 每次拉取最近 N 根日K
COLLECT_RETRY     = 3      # 单股票失败重试次数
COLLECT_RETRY_SLEEP = 1.0  # 重试间隔秒
COLLECT_SCHEDULE  = "15:50"  # 每日采集时间


# ═══════════════════════════════════════════════════════════════════
#  Redis 配置（2026-04-07 新增，新闻采集状态缓存）
# ═══════════════════════════════════════════════════════════════════

REDIS_HOST     = os.environ.get("REDIS_HOST",     "127.0.0.1")
REDIS_PORT     = int(os.environ.get("REDIS_PORT",   "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")  # 默认无密码
REDIS_DB       = int(os.environ.get("REDIS_DB",     "0"))
REDIS_DECODE   = True  # 自动解码为 str
