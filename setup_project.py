#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================
量华量化交易平台 - 一键自动部署 & 数据库初始化
============================================

使用方法（两条命令即可）：
    pip install -r requirements.txt
    python setup_project.py

功能：
    1. 自动连接 MySQL（支持交互式输入或环境变量）
    2. 自动创建数据库 lianghua
    3. 自动扫描所有 news_* 分表
    4. 自动补全缺失字段（22个标准字段 + 4个索引）
    5. 自动修正字段类型/注释
    6. 自动创建当月新闻表（5种类型）
    7. 不删除、不覆盖任何原有数据
"""

import os
import sys
import re
import getpass
from datetime import date

# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════

DEFAULT_DB = {
    "host": os.environ.get("LH_DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("LH_DB_PORT", "3306")),
    "user": os.environ.get("LH_DB_USER", "root"),
    "password": os.environ.get("LH_DB_PASS", "042018"),
    "database": os.environ.get("LH_DB_NAME", "lianghua"),
    "charset": "utf8mb4",
}

# 支持的新闻表类型
NEWS_TYPES = ["company", "cctv", "caixin", "global", "flash"]

# ═══════════════════════════════════════════════════════════════
# 所有新闻表的统一补全字段（22个）
# ═══════════════════════════════════════════════════════════════

UNIFIED_COLUMNS = [
    # ---- 情感分析基础字段（6个）----
    ("sentiment",             "VARCHAR(20) DEFAULT NULL COMMENT '情感标签(positive/neutral/negative)'"),
    ("sentiment_label",       "TINYINT DEFAULT NULL COMMENT '情感标签(0=负面,1=中性,2=正面)'"),
    ("sentiment_confidence",  "FLOAT DEFAULT NULL COMMENT '情感置信度0-1'"),
    ("sentiment_score_neg",   "FLOAT DEFAULT NULL COMMENT '负面情感分数'"),
    ("sentiment_score_neu",   "FLOAT DEFAULT NULL COMMENT '中性情感分数'"),
    ("sentiment_score_pos",   "FLOAT DEFAULT NULL COMMENT '正面情感分数'"),
    # ---- FIB 衍生量化字段（8个）----
    ("sentiment_intensity",   "FLOAT DEFAULT 0 COMMENT '情绪强度：正面得分-负面得分，范围[-1,1]'"),
    ("sentiment_extreme",     "FLOAT DEFAULT 0 COMMENT '情绪极端度：正面与负面得分差值的绝对值'"),
    ("sentiment_certainty",   "FLOAT DEFAULT 0 COMMENT '情绪确定性：1-中性得分，越接近1情绪越明确'"),
    ("low_confidence_flag",   "TINYINT DEFAULT 0 COMMENT '低置信度标记：1=置信度<0.7（不可靠），0=正常'"),
    ("bull_bear_ratio",       "FLOAT DEFAULT 0 COMMENT '多空对比比例：正面得分/(负面得分+1e-8)，>1多头占优，<1空头占优'"),
    ("bear_risk_score",       "FLOAT DEFAULT 0 COMMENT '利空风险得分：负面得分×置信度，越高利空风险越大'"),
    ("bull_risk_score",       "FLOAT DEFAULT 0 COMMENT '利好强度得分：正面得分×置信度，越高利好强度越大'"),
    ("sentiment_volatility",  "FLOAT DEFAULT 0 COMMENT '情绪波动系数：(正面+负面得分)/(中性得分+1e-8)，越高情绪越不稳定'"),
    # ---- 分析时间 ----
    ("analyzed_at",           "DATETIME DEFAULT NULL COMMENT '情感分析时间'"),
    # ---- 新闻分类 + AI 解读字段（6个）----
    ("news_type",             "VARCHAR(20) DEFAULT NULL COMMENT '新闻类型(财经/时政/军事/外交/其他/空内容)'"),
    ("need_analyze",          "TINYINT DEFAULT NULL COMMENT '是否需要AI深度分析(1=是,0=否)'"),
    ("ai_interpretation",     "TEXT DEFAULT NULL COMMENT 'AI新闻解读'"),
    ("ai_benefit_sectors",    "VARCHAR(500) DEFAULT NULL COMMENT 'AI利好板块'"),
    ("ai_benefit_stocks",     "VARCHAR(1000) DEFAULT NULL COMMENT 'AI利好股票'"),
    ("ai_key_suppliers",      "VARCHAR(1000) DEFAULT NULL COMMENT 'AI核心供应商'"),
]

# 需要确保存在的索引
UNIFIED_INDEXES = [
    ("idx_sentiment",       "sentiment"),
    ("idx_sentiment_label", "sentiment_label"),
    ("idx_news_type",       "news_type"),
    ("idx_need_analyze",    "need_analyze"),
]

# ═══════════════════════════════════════════════════════════════
# 各类型新闻表的 DDL 定义
# ═══════════════════════════════════════════════════════════════

# 情感字段 DDL 片段
_SENTIMENT_DDL = """
            sentiment VARCHAR(20) DEFAULT NULL COMMENT '情感标签(positive/neutral/negative)',
            sentiment_label TINYINT DEFAULT NULL COMMENT '情感标签(0=负面,1=中性,2=正面)',
            sentiment_confidence FLOAT DEFAULT NULL COMMENT '情感置信度0-1',
            sentiment_score_neg FLOAT DEFAULT NULL COMMENT '负面情感分数',
            sentiment_score_neu FLOAT DEFAULT NULL COMMENT '中性情感分数',
            sentiment_score_pos FLOAT DEFAULT NULL COMMENT '正面情感分数',
            sentiment_intensity FLOAT DEFAULT 0 COMMENT '情绪强度：正面得分-负面得分，范围[-1,1]',
            sentiment_extreme FLOAT DEFAULT 0 COMMENT '情绪极端度：正面与负面得分差值的绝对值',
            sentiment_certainty FLOAT DEFAULT 0 COMMENT '情绪确定性：1-中性得分，越接近1情绪越明确',
            low_confidence_flag TINYINT DEFAULT 0 COMMENT '低置信度标记：1=置信度<0.7（不可靠），0=正常',
            bull_bear_ratio FLOAT DEFAULT 0 COMMENT '多空对比比例：正面得分/(负面得分+1e-8)，>1多头占优，<1空头占优',
            bear_risk_score FLOAT DEFAULT 0 COMMENT '利空风险得分：负面得分×置信度，越高利空风险越大',
            bull_risk_score FLOAT DEFAULT 0 COMMENT '利好强度得分：正面得分×置信度，越高利好强度越大',
            sentiment_volatility FLOAT DEFAULT 0 COMMENT '情绪波动系数：(正面+负面得分)/(中性得分+1e-8)，越高情绪越不稳定',
            analyzed_at DATETIME DEFAULT NULL COMMENT '情感分析时间',
            news_type VARCHAR(20) DEFAULT NULL COMMENT '新闻类型(财经/时政/军事/外交/其他/空内容)',
            need_analyze TINYINT DEFAULT NULL COMMENT '是否需要AI深度分析(1=是,0=否)',
            ai_interpretation TEXT DEFAULT NULL COMMENT 'AI新闻解读',
            ai_benefit_sectors VARCHAR(500) DEFAULT NULL COMMENT 'AI利好板块',
            ai_benefit_stocks VARCHAR(1000) DEFAULT NULL COMMENT 'AI利好股票',
            ai_key_suppliers VARCHAR(1000) DEFAULT NULL COMMENT 'AI核心供应商',
"""

# 通用尾部字段
_COMMON_TAIL = """
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
"""

def get_create_ddl(news_type: str, table_name: str, year_month: str) -> str:
    """生成指定新闻表的 CREATE TABLE DDL"""
    label = f"{year_month[:4]}年{year_month[4:]}月"

    if news_type == "company":
        return f"""CREATE TABLE IF NOT EXISTS {table_name} (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL COMMENT '股票代码',
            name VARCHAR(100) COMMENT '股票名称',
            event_type VARCHAR(50) COMMENT '事件类型',
            content TEXT COMMENT '具体内容',
            event_date DATE NOT NULL COMMENT '事件日期',
{_SENTIMENT_DDL}
{_COMMON_TAIL}
            UNIQUE KEY uk_symbol_date_type (symbol, event_date, event_type(30)),
            KEY idx_event_date (event_date),
            KEY idx_symbol (symbol),
            KEY idx_event_type (event_type),
            KEY idx_sentiment (sentiment),
            KEY idx_sentiment_label (sentiment_label),
            KEY idx_news_type (news_type),
            KEY idx_need_analyze (need_analyze),
            FULLTEXT KEY ft_content (content)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='公司动态新闻-{label}'"""

    elif news_type == "cctv":
        return f"""CREATE TABLE IF NOT EXISTS {table_name} (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            news_date DATE NOT NULL COMMENT '新闻日期',
            title VARCHAR(500) COMMENT '标题',
            content TEXT COMMENT '内容',
{_SENTIMENT_DDL}
{_COMMON_TAIL}
            UNIQUE KEY uk_date_title (news_date, title(200)),
            KEY idx_news_date (news_date),
            KEY idx_sentiment (sentiment),
            KEY idx_sentiment_label (sentiment_label),
            KEY idx_news_type (news_type),
            KEY idx_need_analyze (need_analyze),
            FULLTEXT KEY ft_content (content)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻联播-{label}'"""

    elif news_type == "caixin":
        return f"""CREATE TABLE IF NOT EXISTS {table_name} (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            tag VARCHAR(50) COMMENT '标签',
            title VARCHAR(500) COMMENT '标题',
            summary TEXT COMMENT '摘要',
            url VARCHAR(500) COMMENT '链接',
            pub_time DATETIME COMMENT '发布时间',
{_SENTIMENT_DDL}
{_COMMON_TAIL}
            UNIQUE KEY uk_url (url(200)),
            KEY idx_pub_time (pub_time),
            KEY idx_tag (tag),
            KEY idx_sentiment (sentiment),
            KEY idx_sentiment_label (sentiment_label),
            KEY idx_news_type (news_type),
            KEY idx_need_analyze (need_analyze),
            FULLTEXT KEY ft_summary (summary)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='财新新闻-{label}'"""

    elif news_type == "global":
        return f"""CREATE TABLE IF NOT EXISTS {table_name} (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(500) COMMENT '标题',
            summary TEXT COMMENT '摘要',
            url VARCHAR(500) COMMENT '链接',
            pub_time DATETIME COMMENT '发布时间',
            source VARCHAR(50) COMMENT '来源(em/cls)',
{_SENTIMENT_DDL}
{_COMMON_TAIL}
            UNIQUE KEY uk_url (url(200)),
            KEY idx_pub_time (pub_time),
            KEY idx_source (source),
            KEY idx_sentiment (sentiment),
            KEY idx_sentiment_label (sentiment_label),
            KEY idx_news_type (news_type),
            KEY idx_need_analyze (need_analyze),
            FULLTEXT KEY ft_summary (summary)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='国际财经新闻-{label}'"""

    elif news_type == "flash":
        return f"""CREATE TABLE IF NOT EXISTS {table_name} (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            content TEXT COMMENT '快讯内容',
            pub_time DATETIME COMMENT '发布时间',
{_SENTIMENT_DDL}
{_COMMON_TAIL}
            KEY idx_pub_time (pub_time),
            KEY idx_sentiment (sentiment),
            KEY idx_sentiment_label (sentiment_label),
            KEY idx_news_type (news_type),
            KEY idx_need_analyze (need_analyze),
            FULLTEXT KEY ft_content (content)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='财经快讯-{label}'"""
    else:
        raise ValueError(f"未知的新闻类型: {news_type}")


# ═══════════════════════════════════════════════════════════════
# 数据库操作工具
# ═══════════════════════════════════════════════════════════════

def get_connection(db_config, database=None):
    """获取 MySQL 连接，支持不指定数据库"""
    import pymysql
    conf = {k: v for k, v in db_config.items() if k != "database"}
    if database:
        conf["database"] = database
    return pymysql.connect(**conf)


def banner():
    """打印横幅"""
    print()
    print("=" * 64)
    print("  量华量化交易平台 - 自动部署 & 数据库初始化")
    print("=" * 64)
    print()


def step(msg):
    """打印步骤"""
    print(f"\n{'─' * 50}")
    print(f"  ▶ {msg}")
    print(f"{'─' * 50}")


def ok(msg="✅"):
    print(f"  {msg}")


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def main():
    banner()

    # ── Step 0: 检查依赖 ──────────────────────────────────────
    step("Step 0: 检查 Python 依赖")
    missing = []
    try:
        import pymysql
        ok("PyMySQL ✓")
    except ImportError:
        missing.append("PyMySQL")
    try:
        import dbutils
        ok("DBUtils ✓")
    except ImportError:
        missing.append("DBUtils")

    if missing:
        print(f"\n  ⚠️  缺少依赖: {', '.join(missing)}")
        print(f"  请先运行: pip install -r requirements.txt")
        sys.exit(1)

    # ── Step 1: 获取数据库连接配置 ─────────────────────────────
    step("Step 1: 配置数据库连接")

    db_config = dict(DEFAULT_DB)

    # 交互式输入（如果密码为空或命令行指定了）
    if "--host" in sys.argv:
        idx = sys.argv.index("--host")
        db_config["host"] = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else db_config["host"]
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        db_config["port"] = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else db_config["port"]
    if "--user" in sys.argv:
        idx = sys.argv.index("--user")
        db_config["user"] = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else db_config["user"]
    if "--database" in sys.argv:
        idx = sys.argv.index("--database")
        db_config["database"] = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else db_config["database"]

    # 密码：命令行 > 环境变量 > 交互式输入
    if "--password" in sys.argv:
        idx = sys.argv.index("--password")
        db_config["password"] = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
    elif not db_config["password"]:
        try:
            db_config["password"] = getpass.getpass(f"  MySQL 密码 [{db_config['user']}@{db_config['host']}]: ")
        except EOFError:
            db_config["password"] = ""

    print(f"  Host:     {db_config['host']}:{db_config['port']}")
    print(f"  User:     {db_config['user']}")
    print(f"  Database: {db_config['database']}")
    ok()

    # ── Step 2: 连接 MySQL 并创建数据库 ────────────────────────
    step("Step 2: 连接 MySQL 并创建数据库")

    try:
        conn = get_connection(db_config)
        cur = conn.cursor()
        ok(f"连接 MySQL 成功")
    except Exception as e:
        print(f"\n  ❌ 连接 MySQL 失败: {e}")
        print(f"  请检查 MySQL 是否已安装并启动")
        sys.exit(1)

    # 创建数据库（如果不存在）
    db_name = db_config["database"]
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.commit()
    ok(f"数据库 `{db_name}` 已就绪")

    # 切换到目标数据库
    cur.execute(f"USE `{db_name}`")
    conn.commit()

    # ── Step 3: 扫描现有新闻表 ────────────────────────────────
    step("Step 3: 扫描现有 news_* 表")

    cur.execute("""
        SELECT table_name, table_comment
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name LIKE 'news_%%'
        ORDER BY table_name
    """, (db_name,))
    existing_tables = cur.fetchall()
    print(f"  找到 {len(existing_tables)} 个新闻表:")
    for tname, tcomment in existing_tables:
        print(f"    • {tname}  ({tcomment or ''})")

    # ── Step 4: 创建当月新闻表（如果不存在）────────────────────
    step("Step 4: 创建当月新闻表")

    today = date.today()
    ym = today.strftime("%Y%m")
    created_tables = []
    for ntype in NEWS_TYPES:
        table_name = f"news_{ntype}_{ym}"
        ddl = get_create_ddl(ntype, table_name, ym)
        cur.execute(ddl)
        conn.commit()
        created_tables.append(table_name)
        ok(f"  {table_name} ✓")

    # ── Step 5: 自动补全所有新闻表的缺失字段 ───────────────────
    step("Step 5: 检查并补全缺失字段")

    # 重新扫描（包含刚创建的表）
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = %s AND table_name LIKE 'news_%%'
        ORDER BY table_name
    """, (db_name,))
    all_tables = [row[0] for row in cur.fetchall()]

    total_columns_added = 0
    total_indexes_added = 0
    fixed_tables = []

    for table_name in all_tables:
        # 获取当前表的字段列表
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """, (db_name, table_name))
        existing_cols = {row[0] for row in cur.fetchall()}

        # 获取当前表的索引列表
        cur.execute("""
            SELECT index_name FROM information_schema.statistics
            WHERE table_schema = %s AND table_name = %s
            GROUP BY index_name
        """, (db_name, table_name))
        existing_indexes = {row[0] for row in cur.fetchall()}

        added_cols = 0
        added_idxs = 0

        # 补全缺失字段
        for col_name, col_def in UNIFIED_COLUMNS:
            if col_name not in existing_cols:
                try:
                    cur.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_def}")
                    added_cols += 1
                    print(f"  [{table_name}] + 字段 {col_name}")
                except Exception as e:
                    print(f"  [{table_name}] + 字段 {col_name} 失败: {e}")

        # 补全缺失索引
        for idx_name, idx_col in UNIFIED_INDEXES:
            if idx_name not in existing_indexes:
                # 确认字段存在再建索引
                if idx_col in existing_cols or idx_col in {c[0] for c in UNIFIED_COLUMNS}:
                    try:
                        cur.execute(f"ALTER TABLE `{table_name}` ADD KEY `{idx_name}` (`{idx_col}`)")
                        added_idxs += 1
                        print(f"  [{table_name}] + 索引 {idx_name}({idx_col})")
                    except Exception as e:
                        # 索引可能已存在（主键/唯一键包含），忽略
                        if "Duplicate key name" not in str(e):
                            print(f"  [{table_name}] + 索引 {idx_name} 失败: {e}")

        conn.commit()
        total_columns_added += added_cols
        total_indexes_added += added_idxs
        if added_cols > 0 or added_idxs > 0:
            fixed_tables.append(table_name)

    # ── Step 6: 修正字段注释 ───────────────────────────────────
    step("Step 6: 修正字段注释")

    comment_fixes = 0
    for table_name in all_tables:
        for col_name, col_def in UNIFIED_COLUMNS:
            # 从 DDL 中提取期望的 COMMENT
            m = re.search(r"COMMENT\s+'([^']+)'", col_def)
            if not m:
                continue
            expected_comment = m.group(1)

            # 查询当前注释
            cur.execute("""
                SELECT COLUMN_COMMENT FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s AND column_name = %s
            """, (db_name, table_name, col_name))
            row = cur.fetchone()
            if not row:
                continue
            current_comment = row[0] or ""

            # 比较注释
            if current_comment != expected_comment:
                # 提取类型和默认值部分
                type_default = col_def.split("COMMENT")[0].strip()
                try:
                    cur.execute(
                        f"ALTER TABLE `{table_name}` MODIFY COLUMN `{col_name}` {type_default} COMMENT %s",
                        (expected_comment,)
                    )
                    comment_fixes += 1
                    conn.commit()
                except Exception as e:
                    # MODIFY 可能因数据不兼容失败，忽略
                    pass

    # ── Step 7: 打印总结报告 ───────────────────────────────────
    step("Step 7: 初始化完成报告")

    print()
    print(f"  📊 数据库:   {db_config['host']}:{db_config['port']}/{db_config['database']}")
    print(f"  📋 新闻表总数: {len(all_tables)}")
    print(f"  🆕 当月新创建: {len(created_tables)} 个")
    print(f"  🔧 字段补全:  {total_columns_added} 个字段 ({len(fixed_tables)} 张表)")
    print(f"  📑 索引补全:  {total_indexes_added} 个索引")
    print(f"  💬 注释修正:  {comment_fixes} 个字段")
    print()

    if fixed_tables:
        print("  已修复的表:")
        for t in fixed_tables:
            print(f"    ✅ {t}")
        print()

    if created_tables:
        print("  已创建的当月表:")
        for t in created_tables:
            print(f"    🆕 {t}")
        print()

    # 验证所有表完整性
    step("Step 8: 验证表结构完整性")
    incomplete = []
    for table_name in all_tables:
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """, (db_name, table_name))
        cols = {row[0] for row in cur.fetchall()}
        missing = [c[0] for c in UNIFIED_COLUMNS if c[0] not in cols]
        if missing:
            incomplete.append((table_name, missing))

    if incomplete:
        print("  ⚠️  以下表仍有缺失字段:")
        for tname, miss in incomplete:
            print(f"    ⚠️  {tname}: 缺少 {', '.join(miss)}")
    else:
        ok(f"所有 {len(all_tables)} 个新闻表结构完整 ✓")

    print()
    print("=" * 64)
    print("  🎉 量华平台数据库初始化完成！")
    print("=" * 64)
    print()
    print("  后续步骤:")
    print("    1. cd backend && python main.py        # 启动后端 (端口 8001)")
    print("    2. cd frontend && npm run dev           # 启动前端 (端口 3000)")
    print()

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
