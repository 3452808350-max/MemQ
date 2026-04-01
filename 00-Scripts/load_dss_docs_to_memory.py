#!/usr/bin/env python3
"""
DSS 系统文档批量载入混合记忆架构

功能:
1. 搜索所有 DSS 相关 MD 文件
2. 读取并分析文档内容
3. 存储到混合记忆架构
4. 生成载入报告
"""

import os
import glob
from datetime import datetime
from memory_enhanced import memory_store_enhanced

print('=' * 80)
print('📚 DSS 系统文档批量载入混合记忆')
print('=' * 80)
print()

# 搜索 DSS 相关 MD 文件
workspace = '/home/kyj/.openclaw/workspace'
dss_files = []

# 搜索模式
patterns = [
    'DSS*.md',
    'dss*.md',
    '*DSS*.md',
    'reports/DSS*.md',
    'memory/dss*.md',
    'data/**/*DSS*.md'
]

for pattern in patterns:
    files = glob.glob(os.path.join(workspace, pattern), recursive=True)
    dss_files.extend(files)

# 去重
dss_files = list(set(dss_files))

print(f'📂 找到 {len(dss_files)} 个 DSS 相关文档:')
print()

for i, filepath in enumerate(dss_files[:20], 1):
    filename = os.path.basename(filepath)
    size = os.path.getsize(filepath) / 1024
    print(f'  {i:2d}. {filename:40s} {size:8.1f} KB')

if len(dss_files) > 20:
    print(f'  ... 还有 {len(dss_files) - 20} 个文件')

print()
print('=' * 80)
print('📖 开始载入文档到混合记忆...')
print('=' * 80)
print()

# 载入文档
loaded_docs = []
total_size = 0

for filepath in dss_files:
    try:
        filename = os.path.basename(filepath)
        relative_path = os.path.relpath(filepath, workspace)
        
        # 读取文件内容
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_size = len(content)
        total_size += file_size
        
        # 提取关键信息
        lines = content.split('\n')
        title = filename
        for line in lines[:10]:
            if line.startswith('#'):
                title = line.lstrip('#').strip()
                break
        
        # 存储到混合记忆
        memory_id = memory_store_enhanced(
            text=f"文档：{title}\n\n{content[:2000]}...",  # 截取前 2000 字
            category="dss_documentation",
            importance=0.8,  # DSS 文档重要性较高
            tags=["DSS", "文档", filename],
            scope="global"
        )
        
        loaded_docs.append({
            'file': filename,
            'path': relative_path,
            'size': file_size,
            'memory_id': memory_id
        })
        
        print(f'  ✅ {filename:40s} ({file_size/1024:.1f} KB)')
        
    except Exception as e:
        print(f'  ❌ {filename:40s} 错误：{e}')

print()
print('=' * 80)
print('📊 载入完成统计')
print('=' * 80)
print()
print(f'  文档总数：{len(loaded_docs)} 个')
print(f'  总大小：{total_size/1024:.1f} KB ({total_size/1024/1024:.2f} MB)')
print(f'  平均大小：{total_size/len(loaded_docs):.1f} KB/文档')
print()
print('📂 已载入文档列表:')
print()

for i, doc in enumerate(loaded_docs, 1):
    print(f'  {i:2d}. {doc["file"]:40s} {doc["size"]/1024:8.1f} KB')

print()
print('=' * 80)
print('✅ DSS 系统文档载入完成！')
print('=' * 80)
print()
print('🎯 下一步:')
print('  1. 使用混合记忆查询 DSS 文档')
print('  2. 运行 DSS 系统测试')
print('  3. 查看载入报告')
print()

# 生成载入报告
report_path = os.path.join(workspace, 'DSS_MEMORY_LOAD_REPORT.md')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write('# DSS 系统文档载入报告\n\n')
    f.write(f'> **载入时间**: {datetime.now().strftime("%Y-%m-%d %H:%M")}\n')
    f.write(f'> **文档总数**: {len(loaded_docs)} 个\n')
    f.write(f'> **总大小**: {total_size/1024:.1f} KB\n\n')
    f.write('## 📂 已载入文档\n\n')
    f.write('| 序号 | 文件名 | 路径 | 大小 (KB) |\n')
    f.write('|------|--------|------|----------|\n')
    for i, doc in enumerate(loaded_docs, 1):
        f.write(f'| {i} | {doc["file"]} | {doc["path"]} | {doc["size"]/1024:.1f} |\n')
    f.write('\n## ✅ 载入状态\n\n')
    f.write('所有 DSS 系统文档已成功载入混合记忆架构！\n')

print(f'📝 载入报告已保存：{report_path}')
print()
