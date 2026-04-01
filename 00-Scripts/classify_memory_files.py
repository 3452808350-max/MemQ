#!/usr/bin/env python3
"""
为 memory 目录下的 Markdown 文件分类和打分

评分标准:
A - 高价值个人记忆（性格、价值观、重要决策、技术实践）
B - 项目相关重要文档（DSS 分析、架构设计）
C - 一般性日志（系统状态、日常记录）
D - 临时性内容（待办事项、短暂信息）
"""

import os
from pathlib import Path
from datetime import datetime

MEMORY_DIR = Path('/home/kyj/.openclaw/workspace/memory')

# 文件分类规则
CLASSIFICATION_RULES = {
    'A': {
        'keywords': ['人格', '性格', '价值观', '特长', '留学', '申请', '技术实践', '重要决策', '偏好'],
        'min_size': 1000,
        'description': '高价值个人记忆'
    },
    'B': {
        'keywords': ['DSS', '架构', '设计', '分析', '人民币', '项目', '优化'],
        'min_size': 2000,
        'description': '项目相关重要文档'
    },
    'C': {
        'keywords': ['日志', '状态', '系统', '运行', '任务'],
        'min_size': 500,
        'description': '一般性日志'
    },
    'D': {
        'keywords': ['待办', '提醒', '临时'],
        'min_size': 0,
        'description': '临时性内容'
    }
}

def analyze_file(file_path):
    """分析文件并评分"""
    content = file_path.read_text(encoding='utf-8')
    filename = file_path.stem
    size = file_path.stat().st_size
    
    score = 'C'  # 默认
    confidence = 0
    matched_keywords = []
    
    # 检查每个等级
    for grade, rules in CLASSIFICATION_RULES.items():
        matches = sum(1 for kw in rules['keywords'] if kw in content)
        
        if matches > 0 and size >= rules['min_size']:
            # 计算得分
            grade_score = matches / len(rules['keywords'])
            
            # A 级特殊处理
            if grade == 'A' and matches >= 2:
                score = 'A'
                confidence = matches
                matched_keywords = [kw for kw in rules['keywords'] if kw in content]
                break
            elif grade == 'B' and matches >= 2 and size >= 3000:
                score = 'B'
                confidence = matches
                matched_keywords = [kw for kw in rules['keywords'] if kw in content]
                break
            elif grade == 'C' and score == 'C':
                score = 'C'
                confidence = matches
                matched_keywords = [kw for kw in rules['keywords'] if kw in content]
    
    # 日期日志特殊处理
    if filename.startswith('2026-0') and len(filename) == 10:
        # 检查是否有高价值内容
        if any(kw in content for kw in ['人格', '价值观', '偏好', '留学']):
            score = 'A' if '人格' in content or '价值观' in content else 'B'
        elif size > 3000:
            score = 'B'
        elif size > 1000:
            score = 'C'
        else:
            score = 'D'
    
    return {
        'file': file_path,
        'filename': filename,
        'score': score,
        'size': size,
        'matched_keywords': matched_keywords,
        'confidence': confidence
    }

def rename_file(file_path, score):
    """重命名文件，添加等级标记"""
    stem = file_path.stem
    suffix = file_path.suffix
    
    # 如果已经有等级标记，先移除
    if '(' in stem and ')' in stem:
        stem = stem.split('(')[0]
    
    new_name = f"{stem}({score}){suffix}"
    new_path = file_path.parent / new_name
    
    return new_path

def main():
    print("=" * 70)
    print("📊 Memory 文档分类和打分")
    print("=" * 70)
    print()
    
    # 获取所有 Markdown 文件
    md_files = list(MEMORY_DIR.glob('*.md'))
    
    print(f"📂 发现 {len(md_files)} 个 Markdown 文件\n")
    
    # 分析和分类
    results = []
    for file in sorted(md_files, key=lambda x: x.stat().st_mtime, reverse=True):
        result = analyze_file(file)
        results.append(result)
    
    # 按等级统计
    by_grade = {'A': [], 'B': [], 'C': [], 'D': []}
    for r in results:
        by_grade[r['score']].append(r)
    
    # 显示结果
    for grade in ['A', 'B', 'C', 'D']:
        files = by_grade[grade]
        if files:
            print(f"\n{'='*70}")
            print(f"等级 {grade}: {CLASSIFICATION_RULES[grade]['description']} ({len(files)} 个文件)")
            print(f"{'='*70}")
            
            total_size = sum(f['size'] for f in files)
            
            for f in files:
                size_kb = f['size'] / 1024
                keywords = ', '.join(f['matched_keywords'][:3]) if f['matched_keywords'] else '无'
                print(f"  📄 {f['filename']}.md ({size_kb:.1f}KB)")
                print(f"     匹配关键词：{keywords}")
            
            print(f"\n  小计：{len(files)} 个文件，{total_size/1024:.1f}KB")
    
    # 总结
    print(f"\n{'='*70}")
    print("📊 总结")
    print(f"{'='*70}")
    print(f"  A 级（高价值个人记忆）: {len(by_grade['A'])} 个文件")
    print(f"  B 级（项目重要文档）: {len(by_grade['B'])} 个文件")
    print(f"  C 级（一般性日志）: {len(by_grade['C'])} 个文件")
    print(f"  D 级（临时性内容）: {len(by_grade['D'])} 个文件")
    print(f"\n  总计：{len(results)} 个文件")
    
    # 询问是否重命名
    print(f"\n{'='*70}")
    response = input("是否要重命名文件（添加等级标记）? (y/n): ")
    
    if response.lower() == 'y':
        print("\n📝 开始重命名...\n")
        
        for r in results:
            old_path = r['file']
            new_path = rename_file(old_path, r['score'])
            
            if old_path != new_path:
                try:
                    old_path.rename(new_path)
                    print(f"  ✅ {old_path.name} → {new_path.name}")
                except Exception as e:
                    print(f"  ❌ {old_path.name} 重命名失败：{e}")
            else:
                print(f"  ⏭️  {old_path.name} 已有标记，跳过")
        
        print("\n✅ 重命名完成！")
    
    print(f"\n{'='*70}")

if __name__ == "__main__":
    main()
