#!/usr/bin/env python3
"""
批量载入所有记忆文档到混合记忆架构

智能过滤：
1. 排除第三方库文档 (skills/scrapling 等)
2. 优先载入项目核心文档
3. 按类别分类存储
4. 生成详细报告
"""

import os
import glob
from datetime import datetime
from memory_enhanced import memory_store_enhanced

print('=' * 80)
print('📚 批量载入所有记忆文档')
print('=' * 80)
print()

workspace = '/home/kyj/.openclaw/workspace'

# 定义载入类别
categories = {
    '项目核心': {
        'patterns': ['*.md', 'README*.md', 'USER.md', 'SOUL.md', 'AGENTS.md'],
        'exclude': ['skills/scrapling', 'skills/everything-claude-code'],
        'importance': 0.9
    },
    'DSS 系统': {
        'patterns': ['*DSS*.md', 'dss*.md'],
        'exclude': [],
        'importance': 0.8
    },
    '混合记忆架构': {
        'patterns': ['*MEMORY*.md', '*GPU*.md', '*HYBRID*.md', '*MINIMAX*.md'],
        'exclude': [],
        'importance': 0.85
    },
    '基础设施': {
        'patterns': ['*WEBDAV*.md', '*DEBIAN*.md', '*FARA*.md', '*SSH*.md'],
        'exclude': [],
        'importance': 0.7
    },
    'IELTS': {
        'patterns': ['*IELTS*.md', 'ielts*.md'],
        'exclude': [],
        'importance': 0.6
    },
    '记忆文件': {
        'patterns': ['memory/*.md', 'MEMORY.md', 'memory-*.md'],
        'exclude': [],
        'importance': 0.75
    }
}

# 收集所有文档
all_docs = []

print('📂 收集文档...')
print()

for category, config in categories.items():
    docs = []
    
    for pattern in config['patterns']:
        files = glob.glob(os.path.join(workspace, '**', pattern), recursive=True)
        
        # 排除指定目录
        for filepath in files:
            excluded = False
            for exclude_path in config['exclude']:
                if exclude_path in filepath:
                    excluded = True
                    break
            
            if not excluded:
                docs.append({
                    'file': os.path.basename(filepath),
                    'path': os.path.relpath(filepath, workspace),
                    'category': category,
                    'importance': config['importance']
                })
    
    # 去重
    unique_docs = []
    seen_paths = set()
    for doc in docs:
        if doc['path'] not in seen_paths:
            unique_docs.append(doc)
            seen_paths.add(doc['path'])
    
    all_docs.extend(unique_docs)
    print(f'  {category:15s}: {len(unique_docs)} 个文档')

print()
print(f'总计：{len(all_docs)} 个文档')
print()
print('=' * 80)
print('📖 开始载入文档...')
print('=' * 80)
print()

# 载入文档
loaded_docs = []
failed_docs = []
total_size = 0

for i, doc in enumerate(all_docs, 1):
    try:
        filepath = os.path.join(workspace, doc['path'])
        
        # 读取文件
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_size = len(content)
        total_size += file_size
        
        # 提取标题
        lines = content.split('\n')
        title = doc['file']
        for line in lines[:10]:
            if line.startswith('#'):
                title = line.lstrip('#').strip()
                break
        
        # 存储到混合记忆
        memory_id = memory_store_enhanced(
            text=f"文档：{title}\n\n{content[:3000]}...",  # 截取前 3000 字
            category=doc['category'].lower().replace(' ', '_'),
            importance=doc['importance'],
            tags=[doc['category'], doc['file']],
            scope="global"
        )
        
        loaded_docs.append({
            'file': doc['file'],
            'path': doc['path'],
            'category': doc['category'],
            'size': file_size,
            'memory_id': memory_id
        })
        
        # 显示进度
        if i % 10 == 0 or i == len(all_docs):
            print(f'  ✅ 已载入 {i}/{len(all_docs)} 个文档 ({i/len(all_docs)*100:.1f}%)')
        
    except Exception as e:
        failed_docs.append({
            'file': doc['file'],
            'error': str(e)
        })
        print(f'  ❌ {doc["file"]}: {e}')

print()
print('=' * 80)
print('📊 载入完成统计')
print('=' * 80)
print()

print(f'  成功载入：{len(loaded_docs)} 个文档')
print(f'  失败：{len(failed_docs)} 个文档')
print(f'  总大小：{total_size/1024:.1f} KB ({total_size/1024/1024:.2f} MB)')
print(f'  平均大小：{total_size/len(loaded_docs):.1f} KB/文档')
print()

# 按类别统计
category_stats = {}
for doc in loaded_docs:
    cat = doc['category']
    if cat not in category_stats:
        category_stats[cat] = {'count': 0, 'size': 0}
    category_stats[cat]['count'] += 1
    category_stats[cat]['size'] += doc['size']

print('📂 按类别统计:')
print()
for cat, stats in sorted(category_stats.items(), key=lambda x: x[1]['count'], reverse=True):
    print(f'  {cat:20s}: {stats["count"]:3d} 个文档，{stats["size"]/1024:.1f} KB')

print()

if failed_docs:
    print('⚠️  失败文档:')
    for doc in failed_docs[:10]:
        print(f'  ❌ {doc["file"]}: {doc["error"]}')
    if len(failed_docs) > 10:
        print(f'  ... 还有 {len(failed_docs) - 10} 个')
    print()

print('=' * 80)
print('✅ 所有记忆文档载入完成！')
print('=' * 80)
print()

# 生成报告
report_path = os.path.join(workspace, 'ALL_MEMORY_LOAD_REPORT.md')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write('# 所有记忆文档载入报告\n\n')
    f.write(f'> **载入时间**: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    f.write(f'> **成功载入**: {len(loaded_docs)} 个\n')
    f.write(f'> **失败**: {len(failed_docs)} 个\n')
    f.write(f'> **总大小**: {total_size/1024:.1f} KB\n\n')
    
    f.write('## 📂 按类别统计\n\n')
    f.write('| 类别 | 文档数 | 大小 (KB) |\n')
    f.write('|------|--------|----------|\n')
    for cat, stats in sorted(category_stats.items(), key=lambda x: x[1]['count'], reverse=True):
        f.write(f'| {cat} | {stats["count"]} | {stats["size"]/1024:.1f} |\n')
    
    f.write('\n## 📄 已载入文档列表\n\n')
    f.write('| 序号 | 文件名 | 类别 | 大小 (KB) |\n')
    f.write('|------|--------|------|----------|\n')
    for i, doc in enumerate(loaded_docs[:100], 1):
        f.write(f'| {i} | {doc["file"]} | {doc["category"]} | {doc["size"]/1024:.1f} |\n')
    
    if len(loaded_docs) > 100:
        f.write(f'\n... 还有 {len(loaded_docs) - 100} 个文档\n')
    
    if failed_docs:
        f.write('\n## ⚠️ 失败文档\n\n')
        for doc in failed_docs[:20]:
            f.write(f'- {doc["file"]}: {doc["error"]}\n')

print(f'📝 详细报告已保存：{report_path}')
print()
print('🎯 下一步:')
print('  1. 使用混合记忆检索所有文档')
print('  2. 查看载入报告')
print('  3. 测试检索性能')
print()
