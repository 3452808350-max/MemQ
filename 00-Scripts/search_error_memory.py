#!/usr/bin/env python3
"""
错误归因记忆检索工具
通过特征值快速查找历史错误和解决方案

使用方法:
    python3 search_error_memory.py --error_type 数据丢失
    python3 search_error_memory.py --system memory-lancedb-pro
    python3 search_error_memory.py --root_cause 数据写入
"""

import json
import argparse
from datetime import datetime
from pathlib import Path

try:
    import lancedb
    HAS_LANCEDB = True
except ImportError:
    HAS_LANCEDB = False

LANCEDB_PATH = '/home/kyj/.openclaw/workspace/lancedb'

def search_by_tags(tags, limit=10):
    """按标签搜索错误记忆"""
    if not HAS_LANCEDB:
        print("❌ 需要安装 lancedb: pip install lancedb")
        return []
    
    db = lancedb.connect(LANCEDB_PATH)
    table = db.open_table('memories')
    
    # 查询包含"错误归因"标签的记忆
    results = table.search(tags[0]).limit(limit * 2).toArray()
    
    # 过滤包含所有标签的结果
    matched = []
    for r in results:
        try:
            metadata = json.loads(r.metadata) if isinstance(r.metadata, str) else r.metadata
            record_tags = metadata.get('tags', [])
            
            if all(tag in record_tags for tag in tags):
                matched.append({
                    'error_id': metadata.get('error_id', r.id),
                    'text': r.text,
                    'metadata': metadata,
                    'score': getattr(r, 'score', 1.0)
                })
        except Exception as e:
            continue
    
    return matched[:limit]

def search_by_metadata(key, value, limit=10):
    """按 metadata 字段搜索"""
    if not HAS_LANCEDB:
        print("❌ 需要安装 lancedb: pip install lancedb")
        return []
    
    db = lancedb.connect(LANCEDB_PATH)
    table = db.open_table('memories')
    
    # 查询包含关键词的记忆
    results = table.search(value).limit(limit * 2).toArray()
    
    # 过滤 metadata 匹配的结果
    matched = []
    for r in results:
        try:
            metadata = json.loads(r.metadata) if isinstance(r.metadata, str) else r.metadata
            
            if key in metadata and str(metadata[key]) == str(value):
                matched.append({
                    'error_id': metadata.get('error_id', r.id),
                    'text': r.text,
                    'metadata': metadata,
                    'score': getattr(r, 'score', 1.0)
                })
        except Exception as e:
            continue
    
    return matched[:limit]

def format_result(result):
    """格式化显示结果"""
    print("\n" + "=" * 70)
    print(f"🚨 错误 ID: {result['error_id']}")
    print("=" * 70)
    print(f"\n📋 错误描述:\n{result['text']}\n")
    
    meta = result['metadata']
    
    print(f"📊 错误类型：{meta.get('error_type', 'N/A')}")
    print(f"⚠️  严重程度：{meta.get('severity', 'N/A')}")
    print(f"🔧 影响系统：{meta.get('affected_system', 'N/A')}")
    print(f"🔍 根因分类：{meta.get('root_cause_category', 'N/A')}")
    print(f"⏰ 发生时间：{meta.get('occurred_at', 'N/A')}")
    print(f"⏱️  解决时间：{meta.get('resolution_time_minutes', 'N/A')} 分钟")
    print()
    
    print(f"🔎 根本原因:\n{meta.get('root_cause', 'N/A')}\n")
    print(f"✅ 解决方案:\n{meta.get('solution', 'N/A')}\n")
    print(f"🛡️  预防措施:\n{meta.get('prevention', 'N/A')}\n")
    
    lessons = meta.get('lessons', [])
    if lessons:
        print(f"💡 经验教训:")
        for i, lesson in enumerate(lessons, 1):
            print(f"   {i}. {lesson}")
        print()
    
    print(f"🏷️  标签：{', '.join(meta.get('tags', []))}")
    print(f"📄 相关文件：{', '.join(meta.get('related_files', []))}")
    print(f"📅 审查日期：{meta.get('review_date', 'N/A')}")
    print()

def main():
    parser = argparse.ArgumentParser(description='错误归因记忆检索工具')
    parser.add_argument('--error_type', type=str, help='按错误类型搜索')
    parser.add_argument('--system', type=str, help='按影响系统搜索')
    parser.add_argument('--root_cause', type=str, help='按根因分类搜索')
    parser.add_argument('--tag', type=str, action='append', help='按标签搜索（可多个）')
    parser.add_argument('--limit', type=int, default=5, help='返回结果数量')
    parser.add_argument('--list', action='store_true', help='列出所有错误记忆')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔍 错误归因记忆检索")
    print("=" * 70)
    
    results = []
    
    if args.list:
        print("\n📋 列出所有错误记忆...\n")
        results = search_by_tags(['错误归因'], limit=args.limit)
    
    elif args.error_type:
        print(f"\n🔍 搜索错误类型：{args.error_type}\n")
        results = search_by_metadata('error_type', args.error_type, limit=args.limit)
    
    elif args.system:
        print(f"\n🔍 搜索影响系统：{args.system}\n")
        results = search_by_metadata('affected_system', args.system, limit=args.limit)
    
    elif args.root_cause:
        print(f"\n🔍 搜索根因分类：{args.root_cause}\n")
        results = search_by_metadata('root_cause_category', args.root_cause, limit=args.limit)
    
    elif args.tag:
        print(f"\n🔍 搜索标签：{', '.join(args.tag)}\n")
        results = search_by_tags(args.tag, limit=args.limit)
    
    else:
        parser.print_help()
        return
    
    if not results:
        print("\n❌ 未找到匹配的错误记忆\n")
        return
    
    print(f"✅ 找到 {len(results)} 条错误记忆:\n")
    
    for result in results:
        format_result(result)
    
    print("=" * 70)
    print(f"📊 共找到 {len(results)} 条错误记忆")
    print("=" * 70)

if __name__ == "__main__":
    main()
