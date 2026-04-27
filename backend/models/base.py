"""
models/base.py — 数据库模型基础常量

定义所有数据库表通用的字段定义和常量。
"""

# 通用表字段后缀定义
# 包含所有表都需要的公共字段和表尾部信息
TABLE_COMMON_SUFFIX = """
`create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
`update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
`cache_key` VARCHAR(60) DEFAULT NULL COMMENT '缓存字段key',
`is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除标记(0=未删除,1=已删除)'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='{table_comment}';
"""

# 通用字段定义（单独使用）
COMMON_FIELDS = {
    'created_time': "`create_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'",
    'update_time': "`update_time` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'",
    'cache_key': "`cache_key` VARCHAR(60) DEFAULT NULL COMMENT '缓存字段key'",
    'is_deleted': "`is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除标记(0=未删除,1=已删除)'"
}

# 表尾部模板
TABLE_FOOTER_TEMPLATE = """) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='{table_comment}';"""

__all__ = [
    'TABLE_COMMON_SUFFIX',
    'COMMON_FIELDS',
    'TABLE_FOOTER_TEMPLATE'
]