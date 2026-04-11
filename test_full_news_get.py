#!/usr/bin/env python3
"""
测试全球新闻全量获取接口 - 获取昨天的数据
"""

import sys
sys.path.insert(0, 'backend')

from utils.full_news_get import _fetch_global_full
from datetime import datetime, timedelta

# 时间范围：昨天 00:00:00 ~ 昨天 23:59:59
end = datetime.now().replace(hour=23, minute=59, second=59)
start = end - timedelta(days=1)
start = start.replace(hour=0, minute=0, second=0)

print(f"测试全球新闻全量获取")
print(f"时间范围: {start.strftime('%Y-%m-%d %H:%M:%S')} ~ {end.strftime('%Y-%m-%d %H:%M:%S')}")
print()

result = _fetch_global_full(start, end)

print()
print(f"✅ 获取完成，共 {len(result)} 条新闻")
print()

if len(result) > 0:
    print("📝 前 3 条新闻预览:")
    for i, item in enumerate(result[:3]):
        dt_str = item["publish_time"].strftime("%Y-%m-%d %H:%M")
        title_preview = item["title"][:60]
        print(f"  {i+1}. [{dt_str}] {title_preview}")

    print()
    print("🔍 格式字段检查:")
    required_fields = ["title", "content", "url", "source", "source_category", "news_type", "publish_time", "content_hash"]
    all_ok = True
    for field in required_fields:
        if field not in result[0]:
            print(f"  ❌ 缺少字段: {field}")
            all_ok = False
        else:
            val = result[0][field]
            print(f"  ✅ {field}: {type(val)}")
            if field == "publish_time" and not isinstance(val, datetime):
                print(f"      ⚠️  publish_time 类型错误，应为 datetime 对象，实际 {type(val)}")
                all_ok = False

    print()
    if all_ok:
        print("🎉 所有检查通过！格式完全正确，可以正常入库和LLM分析")
    else:
        print("❌ 存在格式错误，请检查")
