"""
models/news_models.py — 新闻系统数据库模型 & 建表

2026-04-03 v2:
  - DDL 增加 UNIQUE INDEX uk_url (url(255)) 避免重复
  - insert_news 改为 500 条分批 INSERT IGNORE
  - ensure_table_exists 自动补齐唯一索引

2026-04-06 v4（重大重构）:
  - 数据库统一为 news_data，拼写修正 news_date → news_data
  - 分表 DDL 直接包含全部量化字段（44字段），不再需要第二张同步表
  - 去重改用 url_hash（CHAR(32)）替代 UNIQUE INDEX uk_url(url(255))
  - 所有 CRUD 函数改用 get_news_conn()（news_data 专用连接池）
  - 新增 fetch_need_analyze() / update_ai_result() 量化分析接口

2026-04-07 v5（自动容错）:
  - insert_news 正常路径直接写入，不做前置检查
  - 捕获 ER_BAD_DB_ERROR(1049) / ER_NO_SUCH_TABLE(1146) 时：
      1. 调用 init_news_db() 自动建库
      2. 调用 create_news_table() 建表
      3. 自动重试一次写入
  - 其他错误（重复键、连接失败等）按原有逻辑处理
"""

import hashlib
import re
from datetime import datetime
import pymysql
from utils.db import get_news_conn, get_news_cursor, table_exists


# ─── 特殊字符清洗工具 ─────────────────────────────────────────────

# MySQL utf8mb4 可以存 emoji，但如果表/连接字符集仍是 utf8（3字节），
# 高码位字符（\U00010000~）会导致 Incorrect string value 错误。
# 下面函数在入库前对 4 字节 Unicode 字符做替换，保底兼容老版 MySQL。
_EMOJI_RE = re.compile(
    "["
    "\U00010000-\U0010FFFF"   # 辅助平面（emoji、历史文字等）
    "]",
    flags=re.UNICODE,
)


def sanitize_text(text) -> str | None:
    """
    文本入库安全清洗：
      1. None / 非字符串 → None
      2. 去除 NUL 字节（MySQL 禁止 \\x00）
      3. 4 字节 Unicode（如 emoji）替换为 [emoji]（兼容非 utf8mb4 列）
    """
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    # 移除 NUL 字节
    text = text.replace("\x00", "")
    # 替换 emoji 等 4 字节字符（若确认全链路均为 utf8mb4 可注释此行）
    text = _EMOJI_RE.sub("[emoji]", text)
    return text or None

# ─── 新闻类型常量 ─────────────────────────────────────────────────
NEWS_TYPES = ("company", "cctv", "caixin", "global", "notice", "stock")

# news_data 数据库名
NEWS_DB_NAME = "news_data"

# ─── 建表 DDL（按月分表，news_data 库）────────────────────────────
# 分表直接包含全部量化字段，无需第二张表同步

CREATE_NEWS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS `{table_name}` (
    -- ═══════════════════════════════════════════════════════════════
    -- 基础信息（8字段）：新闻原始数据，采集时写入
    -- ═══════════════════════════════════════════════════════════════
    id                  BIGINT         AUTO_INCREMENT PRIMARY KEY     COMMENT '主键ID，自增',
    title               VARCHAR(500)   NOT NULL DEFAULT ''           COMMENT '新闻标题',
    content             LONGTEXT       DEFAULT NULL                  COMMENT '新闻正文，完整内容',
    url                 VARCHAR(1000)  DEFAULT NULL                  COMMENT '原文链接URL',
    source              VARCHAR(100)   NOT NULL DEFAULT ''           COMMENT '来源媒体名称（如：东方财富、财联社、新闻联播）',
    source_category     VARCHAR(50)    NOT NULL DEFAULT ''           COMMENT '来源细分分类（如：东方财富个股、东方财富研报、东方财富公告、东方财富全球）',
    news_type           VARCHAR(20)    NOT NULL DEFAULT ''           COMMENT '新闻大类（company=公司动态 / cctv=新闻联播 / caixin=财新 / global=国际 / notice=公告 / stock=个股研报）',
    publish_time        DATETIME       DEFAULT NULL                  COMMENT '新闻发布时间（原始时间，非入库时间）',
    collect_time        DATETIME       DEFAULT CURRENT_TIMESTAMP     COMMENT '采集入库时间（系统自动）',

    -- ═══════════════════════════════════════════════════════════════
    -- LLM 分析输出字段（12个）：大模型分析结果
    -- ═══════════════════════════════════════════════════════════════
    -- AI 核心分析（10个）
    ai_interpretation     TEXT         DEFAULT NULL                  COMMENT '【LLM】AI核心解读，200字以内新闻要点概括',
    ai_event_type         VARCHAR(50)  DEFAULT NULL                  COMMENT '【LLM】事件类型枚举（财报/并购/政策/研发/诉讼/高管变动/战略合作/产能扩张/业务调整/风险事件/其他）',
    ai_impact_level       TINYINT      DEFAULT NULL                  COMMENT '【LLM】影响等级（1=轻微 / 2=一般 / 3=中等 / 4=较大 / 5=重大）',
    ai_impact_direction   TINYINT      DEFAULT NULL                  COMMENT '【LLM】影响方向（1=利好 / 0=中性 / -1=利空）',
    ai_risk_level         TINYINT      DEFAULT NULL                  COMMENT '【LLM】风险等级（1=低 / 2=较低 / 3=中等 / 4=较高 / 5=高）',
    ai_benefit_sectors    TEXT         DEFAULT NULL                  COMMENT '【LLM】受益板块，中文逗号分隔（如：新能源,半导体,光伏）',
    ai_benefit_stocks     TEXT         DEFAULT NULL                  COMMENT '【LLM】受益个股，中文逗号分隔（如：比亚迪,宁德时代），严禁虚构',
    ai_keywords           TEXT         DEFAULT NULL                  COMMENT '【LLM】核心关键词，3-6个，中文逗号分隔',
    is_official           TINYINT      DEFAULT 0                     COMMENT '【LLM】是否官方公告（1=是 / 0=否）',
    is_breaking           TINYINT      DEFAULT 0                     COMMENT '【LLM】是否突发新闻（1=是 / 0=否）',

    -- 情感分析（2个）
    sentiment             FLOAT        DEFAULT NULL                  COMMENT '【LLM】全文情感得分（-1.0极度负面 ~ 1.0极度正面，保留2位小数）',
    sentiment_label       TINYINT      DEFAULT NULL                  COMMENT '【LLM】情感标签（1=正面 / 0=中性 / -1=负面）',

    -- ═══════════════════════════════════════════════════════════════
    -- 系统自动填充字段（3个）：程序计算/自动设置
    -- ═══════════════════════════════════════════════════════════════
    ai_analyze_time       DATETIME     DEFAULT NULL                  COMMENT '【系统】AI分析完成时间，回写时自动设为 NOW()',
    need_analyze          TINYINT      DEFAULT 1                     COMMENT '【系统】是否需要AI分析（1=待分析 / 0=已完成或跳过）',
    source_level          TINYINT      DEFAULT 3                     COMMENT '【系统】来源可信度等级（1=官方权威 / 2=主流媒体 / 3=行业媒体 / 4=自媒体 / 5=不明）',

    -- ═══════════════════════════════════════════════════════════════
    -- 扩展字段（17个）：预留给未来功能扩展，当前不使用
    -- ═══════════════════════════════════════════════════════════════
    -- 情感分析扩展（6个）
    title_sentiment       FLOAT        DEFAULT NULL                  COMMENT '【扩展】标题情感得分（-1.0 ~ 1.0），暂未启用',
    title_sentiment_label TINYINT      DEFAULT NULL                  COMMENT '【扩展】标题情感标签（1/0/-1），暂未启用',
    sentiment_confidence  FLOAT        DEFAULT NULL                  COMMENT '【扩展】情感置信度（0.0 ~ 1.0），暂未启用',
    sentiment_volatility  FLOAT        DEFAULT NULL                  COMMENT '【扩展】情感波动度（0.0 ~ 1.0），暂未启用',
    subjectivity_score    FLOAT        DEFAULT NULL                  COMMENT '【扩展】主观性得分（0=纯客观 ~ 1=纯主观），暂未启用',
    emotion_type          VARCHAR(20)  DEFAULT NULL                  COMMENT '【扩展】情绪类型（喜悦/愤怒/恐惧/悲伤/惊讶/厌恶/平静/期望/焦虑/乐观/悲观），暂未启用',

    -- AI分析扩展（5个）
    ai_impact_duration    VARCHAR(20)  DEFAULT NULL                  COMMENT '【扩展】影响持续时间（短期/中期/长期），暂未启用',
    ai_key_suppliers      TEXT         DEFAULT NULL                  COMMENT '【扩展】关键供应商/合作方，逗号分隔，暂未启用',
    ai_topic_tags         TEXT         DEFAULT NULL                  COMMENT '【扩展】主题标签，逗号分隔，暂未启用',
    ai_related_indices    TEXT         DEFAULT NULL                  COMMENT '【扩展】关联指数，逗号分隔（如：沪深300,创业板指），暂未启用',

    -- 量化交易适配（6个）
    is_processed          TINYINT      DEFAULT 0                     COMMENT '【扩展】是否已被量化策略处理（1=是 / 0=否）',
    strategy_signal       TINYINT      DEFAULT NULL                  COMMENT '【扩展】策略信号（1=买入 / 0=持有 / -1=卖出）',
    signal_strength       FLOAT        DEFAULT NULL                  COMMENT '【扩展】信号强度（0.0 ~ 1.0）',
    signal_expire_time    DATETIME     DEFAULT NULL                  COMMENT '【扩展】信号失效时间',
    backtest_result       TEXT         DEFAULT NULL                  COMMENT '【扩展】回测结果，JSON格式',
    market_reaction       TEXT         DEFAULT NULL                  COMMENT '【扩展】市场实际反应，JSON格式',

    -- ═══════════════════════════════════════════════════════════════
    -- 数据治理（5字段）：记录生命周期管理
    -- ═══════════════════════════════════════════════════════════════
    create_time           DATETIME     DEFAULT CURRENT_TIMESTAMP     COMMENT '记录创建时间（系统自动）',
    update_time           DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录最后更新时间（系统自动）',
    data_version          VARCHAR(20)  DEFAULT 'v1.0'                COMMENT '数据版本号（当前 v1.0，字段精简版）',
    operator              VARCHAR(50)  DEFAULT NULL                  COMMENT '操作人/系统标识（如：llm_analyzer / manual）',
    is_deleted            TINYINT      DEFAULT 0                     COMMENT '逻辑删除标记（1=已删除 / 0=正常）',

    -- ═══════════════════════════════════════════════════════════════
    -- 去重 & 索引
    -- ═══════════════════════════════════════════════════════════════
    content_hash          CHAR(32)     DEFAULT NULL                  COMMENT '内容摘要（32位hex）：md5(title + content)，用于去重',
    INDEX idx_publish_time        (publish_time),
    INDEX idx_collect_time        (collect_time),
    INDEX idx_source_category     (source_category),
    INDEX idx_need_analyze        (need_analyze),
    INDEX idx_is_processed        (is_processed),
    INDEX idx_ai_impact_direction (ai_impact_direction),
    INDEX idx_is_deleted          (is_deleted),
    INDEX idx_news_type           (news_type),
    INDEX idx_source              (source),
    UNIQUE INDEX uk_content_hash  (content_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='{comment}'
"""


# ─── content_hash 工具 ────────────────────────────────────────────────

def compute_content_hash(title: str | None, content: str | None) -> str | None:
    """计算内容的 MD5 摘要（32位hex）：md5(title + content)"""
    if not title and not content:
        return None
    
    title_str = str(title) if title else ""
    content_str = str(content) if content else ""
    combined = f"{title_str}{content_str}"
    
    if not combined.strip():
        return None
    
    return hashlib.md5(combined.encode("utf-8")).hexdigest()

# 兼容旧代码（暂时保留，逐步迁移）
def compute_url_hash(url: str | None) -> str | None:
    """计算 URL 的 MD5 摘要（32位hex），url 为空返回 None"""
    if not url:
        return None
    return hashlib.md5(url.encode("utf-8")).hexdigest()


# ─── 表名映射 ────────────────────────────────────────────────────

def get_table_name(news_type: str, year_month: str) -> str:
    """
    获取分表名。
    示例: get_table_name("company", "202604") -> "news_company_202604"
    """
    return f"news_{news_type}_{year_month}"


def get_table_comment(news_type: str) -> str:
    """获取表的中文注释"""
    comments = {
        "company": "公司动态新闻",
        "cctv":    "新闻联播",
        "caixin":  "财新新闻",
        "global":  "国际新闻",
        "notice":  "公告",
        "stock":   "个股新闻",
    }
    return comments.get(news_type, "新闻")


# ─── 建表函数 ────────────────────────────────────────────────────

def create_news_table(news_type: str, year_month: str):
    """为指定类型和月份创建分表（如不存在则创建），使用 news_data 连接"""
    table_name = get_table_name(news_type, year_month)
    comment = get_table_comment(news_type)
    ddl = CREATE_NEWS_TABLE_DDL.format(table_name=table_name, comment=comment)

    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
        print(f"[news_models] 表 {table_name} 已就绪")
    finally:
        conn.close()
    return table_name


def create_news_tables_for_month(year_month: str, types=None):
    """为指定月份批量创建所有新闻类型分表"""
    if types is None:
        types = NEWS_TYPES
    for t in types:
        create_news_table(t, year_month)


def ensure_table_exists(news_type: str, year_month: str):
    """
    检查表是否存在，不存在则创建；存在则补齐缺失字段（幂等）。
    使用 news_data 连接。
    """
    table_name = get_table_name(news_type, year_month)
    if not table_exists(table_name, NEWS_DB_NAME):
        create_news_table(news_type, year_month)
        return True

    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT COLUMN_NAME FROM information_schema.COLUMNS "
                f"WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
                (NEWS_DB_NAME, table_name),
            )
            existing_cols = {row["COLUMN_NAME"] for row in cur.fetchall()}

            # v4 新增字段（从旧表升级时补齐）
            new_cols = {
                "url_hash":              "CHAR(32) DEFAULT NULL COMMENT 'URL MD5摘要'",
                "ai_event_type":         "VARCHAR(50) DEFAULT NULL COMMENT '事件类型'",
                "ai_impact_level":       "TINYINT DEFAULT NULL COMMENT 'AI评估影响等级'",
                "ai_impact_direction":   "TINYINT DEFAULT NULL COMMENT '影响方向'",
                "ai_impact_duration":    "VARCHAR(20) DEFAULT NULL COMMENT '影响持续时间'",
                "ai_risk_level":         "TINYINT DEFAULT NULL COMMENT '风险等级'",
                "ai_keywords":           "TEXT DEFAULT NULL COMMENT '核心关键词'",
                "ai_topic_tags":         "TEXT DEFAULT NULL COMMENT '主题标签'",
                "ai_related_indices":    "TEXT DEFAULT NULL COMMENT '关联指数'",
                "ai_analyze_time":       "DATETIME DEFAULT NULL COMMENT 'AI分析完成时间'",
                "source_level":          "TINYINT DEFAULT 3 COMMENT '来源可信度等级'",
                "is_official":           "TINYINT DEFAULT 0 COMMENT '是否官方公告'",
                "is_breaking":           "TINYINT DEFAULT 0 COMMENT '是否突发新闻'",
                "title_sentiment":       "FLOAT DEFAULT NULL COMMENT '标题情感得分'",
                "title_sentiment_label": "TINYINT DEFAULT NULL COMMENT '标题情感标签'",
                "sentiment_volatility":  "FLOAT DEFAULT NULL COMMENT '情感波动度'",
                "subjectivity_score":    "FLOAT DEFAULT NULL COMMENT '主观性得分'",
                "emotion_type":          "VARCHAR(20) DEFAULT NULL COMMENT '情绪类型'",
                "is_processed":          "TINYINT DEFAULT 0 COMMENT '是否已被策略处理'",
                "strategy_signal":       "TINYINT DEFAULT NULL COMMENT '策略信号'",
                "signal_strength":       "FLOAT DEFAULT NULL COMMENT '信号强度'",
                "signal_expire_time":    "DATETIME DEFAULT NULL COMMENT '信号失效时间'",
                "backtest_result":       "TEXT DEFAULT NULL COMMENT '回测结果'",
                "market_reaction":       "TEXT DEFAULT NULL COMMENT '市场实际反应'",
                "data_version":          "VARCHAR(20) DEFAULT 'v1.0' COMMENT '数据版本号'",
                "operator":              "VARCHAR(50) DEFAULT NULL COMMENT '操作人/系统'",
                "is_deleted":            "TINYINT DEFAULT 0 COMMENT '逻辑删除'",
            }
            added = []
            for col_name, col_def in new_cols.items():
                if col_name not in existing_cols:
                    cur.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_def}")
                    added.append(col_name)

            # 回填 url_hash（如果有 url 字段但无 url_hash 数据）
            if "url_hash" in added and "url" in existing_cols:
                cur.execute(
                    f"UPDATE `{table_name}` SET url_hash = MD5(url) "
                    f"WHERE url IS NOT NULL AND url_hash IS NULL"
                )
                print(f"[news_models] 表 {table_name} 已回填 url_hash")

            # 添加 uk_url_hash 唯一索引（如果不存在）
            cur.execute(
                "SELECT INDEX_NAME FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
                "AND INDEX_NAME = 'uk_url_hash'",
                (NEWS_DB_NAME, table_name),
            )
            if not cur.fetchone():
                try:
                    cur.execute(
                        f"ALTER TABLE `{table_name}` "
                        f"ADD UNIQUE INDEX uk_url_hash (url_hash)"
                    )
                    print(f"[news_models] 表 {table_name} 已添加唯一索引 uk_url_hash")
                except Exception as e:
                    print(f"[news_models] 建唯一索引失败({e})，清理重复 url_hash 后重试...")
                    cur.execute(
                        f"DELETE t1 FROM `{table_name}` t1 "
                        f"INNER JOIN `{table_name}` t2 "
                        f"WHERE t1.id > t2.id AND t1.url_hash = t2.url_hash AND t1.url_hash IS NOT NULL"
                    )
                    cur.execute(
                        f"ALTER TABLE `{table_name}` "
                        f"ADD UNIQUE INDEX uk_url_hash (url_hash)"
                    )
                    print(f"[news_models] 表 {table_name} 清理后已添加唯一索引 uk_url_hash")

        conn.commit()
        if added:
            print(f"[news_models] 表 {table_name} 已补齐字段: {', '.join(added)}")
    except Exception as e:
        conn.rollback()
        print(f"[news_models] 补齐失败: {e}")
    finally:
        conn.close()

    return True


# ─── CRUD 工具 ────────────────────────────────────────────────────

BATCH_SIZE = 500  # 每批写入条数


def insert_news(news_type: str, year_month: str, rows: list[dict]) -> int:
    """
    批量插入新闻（INSERT IGNORE + 500 条分批）。
    自动计算 url_hash 并写入。
    使用 news_data 连接。

    容错策略（v5）：
      - 正常路径：直接写入，不做前置检查
      - 捕获 ER_BAD_DB_ERROR(1049)：自动建库 → 建表 → 重试一次
      - 捕获 ER_NO_SUCH_TABLE(1146)：自动建表 → 重试一次
      - 其他错误（如重复键/连接失败）：按原有逻辑处理

    Returns:
        实际插入行数
    """
    if not rows:
        return 0

    table_name = get_table_name(news_type, year_month)

    # ─── 入库前安全清洗 ────────────────────────────────────────────
    _TEXT_FIELDS = {
        "title", "content", "url", "source", "source_category",
        "news_type", "ai_interpretation", "ai_event_type",
        "ai_benefit_sectors", "ai_benefit_stocks", "ai_keywords",
        "sentiment_label", "operator",
    }
    for row in rows:
        for field in _TEXT_FIELDS:
            if field in row:
                row[field] = sanitize_text(row[field])

    # 自动补齐 content_hash
    for row in rows:
        if "content_hash" not in row:
            row["content_hash"] = compute_content_hash(row.get("title"), row.get("content"))

    columns = list(rows[0].keys())
    col_str = ", ".join([f"`{c}`" for c in columns])
    placeholders_per_row = "(" + ",".join(["%s"] * len(columns)) + ")"

    def _do_insert(conn) -> int:
        """执行实际 INSERT，返回插入行数"""
        total = 0
        with conn.cursor() as cur:
            for i in range(0, len(rows), BATCH_SIZE):
                batch = rows[i : i + BATCH_SIZE]
                all_placeholders = ",".join([placeholders_per_row] * len(batch))
                sql = (
                    f"INSERT IGNORE INTO `{table_name}` ({col_str}) "
                    f"VALUES {all_placeholders}"
                )
                flat_params = [row[c] for row in batch for c in columns]
                cur.execute(sql, flat_params)
                total += cur.rowcount
        conn.commit()
        return total

    # ─── 主路径：直接写入 ─────────────────────────────────────────
    conn = get_news_conn()
    try:
        return _do_insert(conn)

    except pymysql.err.OperationalError as e:
        err_code = e.args[0]

        # ── 错误 1049：数据库不存在 ──────────────────────────────
        if err_code == 1049:
            print(f"[news_models] 数据库不存在（1049），自动创建 news_data 及表 {table_name} ...")
            try:
                from utils.db import init_news_db  # 延迟导入避免循环
                init_news_db()                      # 建库
                create_news_table(news_type, year_month)  # 建表
            except Exception as init_err:
                print(f"[news_models] 自动初始化失败: {init_err}")
                return 0
            # 重试一次（获取新连接，此时库已存在）
            retry_conn = get_news_conn()
            try:
                result = _do_insert(retry_conn)
                print(f"[news_models] 重试写入成功，插入 {result} 条")
                return result
            except Exception as retry_err:
                retry_conn.rollback()
                print(f"[news_models] 重试写入仍失败: {retry_err}")
                return 0
            finally:
                retry_conn.close()

        # ── 错误 1146：表不存在 ──────────────────────────────────
        elif err_code == 1146:
            print(f"[news_models] 表不存在（1146），自动创建 {table_name} ...")
            try:
                create_news_table(news_type, year_month)
            except Exception as init_err:
                print(f"[news_models] 自动建表失败: {init_err}")
                return 0
            # 重试一次
            retry_conn = get_news_conn()
            try:
                result = _do_insert(retry_conn)
                print(f"[news_models] 重试写入成功，插入 {result} 条")
                return result
            except Exception as retry_err:
                retry_conn.rollback()
                print(f"[news_models] 重试写入仍失败: {retry_err}")
                return 0
            finally:
                retry_conn.close()

        # ── 其他 OperationalError：按原有逻辑处理 ────────────────
        else:
            conn.rollback()
            print(f"[news_models] 批量插入失败（OperationalError {err_code}）: {e}")
            return 0

    except Exception as e:
        conn.rollback()
        print(f"[news_models] 批量插入失败: {e}")
        return 0
    finally:
        conn.close()


def fetch_news_by_date(news_type: str, year_month: str, date_str: str, limit: int = 100) -> list[dict]:
    """按日期查询新闻（news_data 连接）"""
    table_name = get_table_name(news_type, year_month)
    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT * FROM `{table_name}` WHERE DATE(publish_time) = %s "
                f"ORDER BY publish_time DESC LIMIT %s",
                (date_str, limit)
            )
            return cur.fetchall()
    finally:
        conn.close()


# ─── 量化分析接口 ─────────────────────────────────────────────────

def fetch_need_analyze(limit: int = 50) -> list[dict]:
    """
    获取所有待 AI 分析的新闻（need_analyze=1 且 is_deleted=0）。
    跨所有新闻类型和月份分表查询。

    Args:
        limit: 最多返回条数

    Returns:
        新闻列表，每条包含 _table 和 _news_type 标记
    """
    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            # 查询 news_data 下所有 news_ 开头的分表
            cur.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME LIKE 'news_%%_20%%'",
                (NEWS_DB_NAME,),
            )
            tables = [row["TABLE_NAME"] for row in cur.fetchall()]

            results = []
            for table_name in tables:
                # 从表名提取 news_type（如 news_company_202604 → company）
                parts = table_name.split("_")
                if len(parts) >= 3:
                    news_type = parts[1]
                else:
                    news_type = "unknown"

                cur.execute(
                    f"SELECT *, '{table_name}' AS `_table`, '{news_type}' AS `_news_type` "
                    f"FROM `{table_name}` "
                    f"WHERE need_analyze = 1 AND is_deleted = 0 "
                    f"ORDER BY publish_time DESC "
                    f"LIMIT %s",
                    (limit,),
                )
                rows = cur.fetchall()
                for row in rows:
                    results.append(row)
                    if len(results) >= limit:
                        return results

            return results
    finally:
        conn.close()


def fetch_need_analyze_by_types(news_types: list[str], limit: int = 20) -> list[dict]:
    """
    按指定 news_type 列表获取待 AI 分析的新闻。

    与 fetch_need_analyze 的区别：
      - 只查询指定 news_type 对应的分表（不扫全部分表）
      - 适用于 4 线程并行分析场景，每个线程只查自己负责的分类

    Args:
        news_types: 要查询的新闻类型列表（如 ["company"] 或 ["caixin"]）
        limit: 每种类型最多返回条数

    Returns:
        新闻列表，每条包含 _table 和 _news_type 标记
    """
    if not news_types:
        return []

    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            results = []
            for nt in news_types:
                # 查询 news_data 下匹配 news_{nt}_20** 的分表
                pattern = f"news_{nt}_20%%"
                cur.execute(
                    "SELECT TABLE_NAME FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = %s AND TABLE_NAME LIKE %s",
                    (NEWS_DB_NAME, pattern),
                )
                tables = [row["TABLE_NAME"] for row in cur.fetchall()]

                for table_name in tables:
                    # 从表名提取 news_type
                    parts = table_name.split("_")
                    extracted_type = parts[1] if len(parts) >= 3 else "unknown"

                    cur.execute(
                        f"SELECT *, '{table_name}' AS `_table`, '{extracted_type}' AS `_news_type` "
                        f"FROM `{table_name}` "
                        f"WHERE need_analyze = 1 AND is_deleted = 0 "
                        f"ORDER BY publish_time DESC "
                        f"LIMIT %s",
                        (limit,),
                    )
                    rows = cur.fetchall()
                    for row in rows:
                        results.append(row)
                        if len(results) >= limit:
                            return results

            return results
    finally:
        conn.close()


def fetch_news_by_id(table_name: str, news_id: int) -> dict | None:
    """
    按主键 ID 获取单条新闻（用于 LLM 分析消费者从队列取出后读取详情）。

    Args:
        table_name: 分表名（如 news_company_202604）
        news_id: 新闻主键 ID

    Returns:
        新闻字典，或 None（不存在时）
    """
    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT *, %s AS `_table`, %s AS `_news_type` "
                f"FROM `{table_name}` WHERE id = %s",
                (table_name, table_name.split("_")[1] if "_" in table_name else "", news_id),
            )
            row = cur.fetchone()
            return row
    finally:
        conn.close()


def fetch_news_by_ids(items: list[dict]) -> list[dict]:
    """
    批量按主键 ID 获取新闻（从队列弹出的项列表）。
    每个输入项需包含 news_id 和 table_name。

    Args:
        items: [{"news_id": 1, "table_name": "news_company_202604", "news_type": "company"}, ...]

    Returns:
        新闻详情列表（顺序与输入一致，不存在的跳过）
    """
    if not items:
        return []

    # 按 table_name 分组，减少连接数
    by_table: dict[str, list[int]] = {}
    id_to_item = {}  # news_id → original item（用于补齐 _table/_news_type）
    for item in items:
        tid = item["news_id"]
        tname = item["table_name"]
        by_table.setdefault(tname, []).append(tid)
        id_to_item[tid] = item

    results = []
    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            for tname, ids in by_table.items():
                # 从表名提取 news_type
                parts = tname.split("_")
                extracted_type = parts[1] if len(parts) >= 3 else "unknown"
                placeholders = ",".join(["%s"] * len(ids))
                cur.execute(
                    f"SELECT *, %s AS `_table`, %s AS `_news_type` "
                    f"FROM `{tname}` WHERE id IN ({placeholders})",
                    (tname, extracted_type, *ids),
                )
                rows = cur.fetchall()
                for row in rows:
                    results.append(row)
    finally:
        conn.close()

    return results


def update_ai_result(table_name: str, news_id: int, ai_result: dict) -> bool:
    """
    更新单条新闻的 AI 分析结果。
    自动设置 ai_analyze_time = NOW()。

    Args:
        table_name: 目标分表名（如 news_company_202604）
        news_id:    新闻 ID
        ai_result:  AI 分析结果字段字典，支持以下 key：
            ai_interpretation / ai_event_type / ai_impact_level /
            ai_impact_direction / ai_impact_duration / ai_risk_level /
            ai_benefit_sectors / ai_benefit_stocks / ai_key_suppliers /
            ai_keywords / ai_topic_tags / ai_related_indices /
            sentiment / title_sentiment / sentiment_label /
            title_sentiment_label / sentiment_confidence /
            sentiment_volatility / subjectivity_score / emotion_type

    Returns:
        是否更新成功
    """
    if not ai_result:
        return False

    ai_result["ai_analyze_time"] = datetime.now()
    ai_result["need_analyze"] = 0  # 标记已分析完成，避免重复处理

    set_parts = []
    values = []
    for key, val in ai_result.items():
        set_parts.append(f"`{key}` = %s")
        values.append(val)

    values.append(news_id)

    sql = f"UPDATE `{table_name}` SET {', '.join(set_parts)} WHERE id = %s"

    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, values)
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"[news_models] 更新AI结果失败: {e}")
        return False
    finally:
        conn.close()


def batch_update_ai_results(items: list[dict]) -> int:
    """
    批量更新新闻 AI 分析结果。

    每条 item 结构：{"table_name": str, "news_id": int, "result": dict}
    自动设置 ai_analyze_time = NOW()。

    单个连接、单次事务，比逐条 update_ai_result 高效得多。
    单条失败不影响其他条。

    Args:
        items: 待更新的分析结果列表

    Returns:
        成功更新的条数
    """
    if not items:
        return 0

    success_count = 0
    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            for item in items:
                table_name = item["table_name"]
                news_id = item["news_id"]
                ai_result = item["result"]

                if not ai_result:
                    continue

                ai_result_copy = dict(ai_result)
                ai_result_copy["ai_analyze_time"] = datetime.now()
                ai_result_copy["need_analyze"] = 0  # 标记已分析完成

                set_parts = []
                values = []
                for key, val in ai_result_copy.items():
                    set_parts.append(f"`{key}` = %s")
                    values.append(val)
                values.append(news_id)

                sql = f"UPDATE `{table_name}` SET {', '.join(set_parts)} WHERE id = %s"
                try:
                    cur.execute(sql, values)
                    if cur.rowcount > 0:
                        success_count += 1
                except Exception as e:
                    print(f"[news_models] 批量更新中单条失败(table={table_name}, id={news_id}): {e}")
                    continue

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[news_models] 批量更新异常: {e}")
    finally:
        conn.close()

    return success_count


def insert_news_return_ids(news_type: str, year_month: str, rows: list[dict]) -> list[dict]:
    """
    批量插入新闻，完成后通过 url_hash 回查刚插入的记录，返回完整记录列表（含 id）。

    新架构采集层专用：
      - 先调用 insert_news 写入 MySQL
      - 再通过 url_hash IN (...) 回查，获取 id + 完整字段（供写入 Redis String）
      - 对于 INSERT IGNORE 忽略的重复数据，回查也能取到已有记录（含已有 id）

    Args:
        news_type:  新闻类型（company/cls/global/cctv/report）
        year_month: 月份字符串（如 202604）
        rows:       待插入的新闻字典列表

    Returns:
        已入库新闻的完整字典列表（含 id、table_name 字段）
    """
    if not rows:
        return []

    table_name = get_table_name(news_type, year_month)

    # 先确保表存在
    ensure_table_exists(news_type, year_month)

    # 插入（自动补 content_hash）
    insert_news(news_type, year_month, rows)

    # 收集本批次中所有记录的 content_hash，用于回查
    content_hashes = []
    for row in rows:
        title = row.get("title")
        content = row.get("content")
        if title or content:
            h = compute_content_hash(title, content)
            if h:
                content_hashes.append(h)

    if not content_hashes:
        return []

    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(content_hashes))
            cur.execute(
                f"SELECT id, title, content, url, source, source_category, news_type, "
                f"publish_time, need_analyze, content_hash, "
                f"'{table_name}' AS `table_name` "
                f"FROM `{table_name}` "
                f"WHERE content_hash IN ({placeholders})",
                content_hashes,
            )
            return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"[news_models] insert_news_return_ids 回查失败: {e}")
        return []
    finally:
        conn.close()


def insert_news_with_content_hash(news_type: str, year_month: str, rows: list[dict]) -> list[dict]:
    """
    基于content_hash的新闻插入函数（新架构专用）。
    严格实现：去重 → 唯一 → 写入 → 获取id
    
    流程：
    1. 计算每条新闻的content_hash = md5(title + content)
    2. 去重判断：检查数据库中是否已存在相同content_hash
    3. 已存在：不写入MySQL，返回None
    4. 不存在：写入MySQL，获取自增id，返回完整新闻记录
    
    Args:
        news_type: 新闻类型
        year_month: 年月
        rows: 新闻数据列表
        
    Returns:
        成功插入的新闻列表（含id），重复项返回None
    """
    if not rows:
        return []
    
    table_name = get_table_name(news_type, year_month)
    ensure_table_exists(news_type, year_month)
    
    # 计算content_hash
    for row in rows:
        row["content_hash"] = compute_content_hash(row.get("title"), row.get("content"))
    
    # 收集所有content_hash用于去重检查
    content_hashes = []
    for row in rows:
        if row["content_hash"]:
            content_hashes.append(row["content_hash"])
    
    if not content_hashes:
        return []
    
    # 连接数据库
    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            # 第一步：检查哪些content_hash已存在
            placeholders = ",".join(["%s"] * len(content_hashes))
            cur.execute(
                f"SELECT content_hash FROM `{table_name}` WHERE content_hash IN ({placeholders})",
                content_hashes
            )
            existing_hashes = set(row["content_hash"] for row in cur.fetchall())
            
            # 第二步：过滤掉重复的新闻
            unique_rows = []
            for row in rows:
                if row["content_hash"] and row["content_hash"] in existing_hashes:
                    # 重复新闻，标记为None
                    continue
                unique_rows.append(row)
            
            if not unique_rows:
                return []
            
            # 第三步：批量插入唯一新闻
            columns = list(unique_rows[0].keys())
            col_str = ", ".join([f"`{c}`" for c in columns])
            placeholders_per_row = "(" + ",".join(["%s"] * len(columns)) + ")"
            
            # 插入数据
            for i in range(0, len(unique_rows), BATCH_SIZE):
                batch = unique_rows[i:i+BATCH_SIZE]
                all_placeholders = ",".join([placeholders_per_row] * len(batch))
                sql = f"INSERT IGNORE INTO `{table_name}` ({col_str}) VALUES {all_placeholders}"
                flat_params = [row[c] for row in batch for c in columns]
                cur.execute(sql, flat_params)
            
            conn.commit()
            
            # 第四步：回查刚插入的记录获取id
            new_content_hashes = [row["content_hash"] for row in unique_rows if row["content_hash"]]
            placeholders = ",".join(["%s"] * len(new_content_hashes))
            cur.execute(
                f"SELECT id, title, content, url, source, source_category, news_type, "
                f"publish_time, need_analyze, content_hash, "
                f"'{table_name}' AS `table_name` "
                f"FROM `{table_name}` "
                f"WHERE content_hash IN ({placeholders})",
                new_content_hashes
            )
            
            result = []
            for row in cur.fetchall():
                result.append(dict(row))
            
            return result
            
    except Exception as e:
        conn.rollback()
        print(f"[news_models] insert_news_with_content_hash 失败: {e}")
        return []
    finally:
        conn.close()


def batch_update_ai_case(items: list[dict]) -> int:
    """
    使用 CASE 语法一次性批量更新 AI 分析结果（持久化层专用，高性能）。

    每条 item 结构：
        {"table_name": str, "news_id": int, "result": dict}
        result 中应包含 ai_interpretation / ai_impact_level 等 LLM 输出字段

    实现方式（CASE 批量 UPDATE，减少往返次数）：
        UPDATE `table` SET
          ai_interpretation = CASE id WHEN 1 THEN '...' WHEN 2 THEN '...' END,
          ...
          need_analyze = 0,
          ai_analyze_time = NOW()
        WHERE id IN (1, 2, ...)

    Args:
        items: 待更新列表

    Returns:
        成功更新的条数
    """
    if not items:
        return 0

    # 按 table_name 分组
    by_table: dict[str, list[dict]] = {}
    for item in items:
        tname = item["table_name"]
        by_table.setdefault(tname, []).append(item)

    total_success = 0
    conn = get_news_conn()
    try:
        with conn.cursor() as cur:
            for tname, tbl_items in by_table.items():
                if not tbl_items:
                    continue

                # 收集需要更新的所有字段名（取第一条的 result keys）
                all_fields = set()
                for item in tbl_items:
                    all_fields.update(item["result"].keys())
                # 移除系统字段（这里统一处理）
                all_fields.discard("ai_analyze_time")
                all_fields.discard("need_analyze")

                ids = [item["news_id"] for item in tbl_items]
                id_placeholders = ",".join(["%s"] * len(ids))

                # 构造 CASE 语句
                case_parts = []
                all_params = []

                for field in sorted(all_fields):
                    case_whens = []
                    for item in tbl_items:
                        val = item["result"].get(field)
                        case_whens.append(f"WHEN %s THEN %s")
                        all_params.extend([item["news_id"], val])
                    case_parts.append(
                        f"`{field}` = CASE `id` {' '.join(case_whens)} ELSE `{field}` END"
                    )

                # 追加固定字段
                case_parts.append("`need_analyze` = 0")
                case_parts.append("`ai_analyze_time` = NOW()")

                set_clause = ",\n  ".join(case_parts)
                sql = (
                    f"UPDATE `{tname}` SET\n  {set_clause}\n"
                    f"WHERE `id` IN ({id_placeholders})"
                )
                all_params.extend(ids)

                try:
                    cur.execute(sql, all_params)
                    total_success += cur.rowcount
                except Exception as e:
                    print(f"[news_models] CASE批量更新 {tname} 失败: {e}")
                    # 降级：逐条更新
                    for item in tbl_items:
                        try:
                            update_ai_result(item["table_name"], item["news_id"], dict(item["result"]))
                            total_success += 1
                        except Exception as ue:
                            print(f"[news_models] 降级单条更新失败 id={item['news_id']}: {ue}")

        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"[news_models] batch_update_ai_case 整体异常: {e}")
    finally:
        conn.close()

    return total_success


# ─── 直接运行：建当前月份的表 ────────────────────────────────────

if __name__ == "__main__":
    ym = datetime.now().strftime("%Y%m")
    print(f"正在为 {ym} 创建所有新闻分表...")
    create_news_tables_for_month(ym)
    print("完成。")
