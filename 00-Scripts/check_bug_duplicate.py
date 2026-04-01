#!/usr/bin/env python3
"""
Bug 记忆查重工具
在归档新 Bug 前，检查是否已存在相似 Bug

核心：防止重复归档造成的浪费
"""

import json
import hashlib
from pathlib import Path
from difflib import SequenceMatcher

def load_existing_bugs():
    """加载所有现有 Bug"""
    bug_files = list(Path('.').glob('bug_*.json'))
    bugs = []
    
    for file in bug_files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        bug = data.get('bug_memory', {})
        bugs.append({
            'file': file,
            'bug_id': bug.get('metadata', {}).get('bug_id'),
            'text': bug.get('text', ''),
            'symptom': bug.get('metadata', {}).get('🔍 现象特征', {}).get('symptom', ''),
            'system': bug.get('metadata', {}).get('📊 影响范围', {}).get('affected_system', ''),
        })
    
    return bugs

def text_similarity(text1, text2):
    """计算文本相似度"""
    return SequenceMatcher(None, text1, text2).ratio()

def check_duplicate(new_bug, threshold=0.7):
    """
    检查新 Bug 是否重复
    
    Args:
        new_bug: 新 Bug 数据
        threshold: 相似度阈值（0-1）
    
    Returns:
        list: 相似 Bug 列表
    """
    existing_bugs = load_existing_bugs()
    
    similar_bugs = []
    
    for bug in existing_bugs:
        # 1. 症状相似度
        symptom_score = text_similarity(
            new_bug.get('symptom', ''),
            bug.get('symptom', '')
        )
        
        # 2. 描述相似度
        text_score = text_similarity(
            new_bug.get('text', ''),
            bug.get('text', '')
        )
        
        # 3. 系统匹配
        system_match = 1.0 if new_bug.get('system') == bug.get('system') else 0.5
        
        # 综合得分
        total_score = (symptom_score * 0.5 + text_score * 0.3 + system_match * 0.2)
        
        if total_score >= threshold:
            similar_bugs.append({
                'bug_id': bug['bug_id'],
                'file': bug['file'],
                'similarity': total_score,
                'symptom': bug['symptom']
            })
    
    # 按相似度排序
    similar_bugs.sort(key=lambda x: x['similarity'], reverse=True)
    
    return similar_bugs

def generate_fingerprint(bug):
    """生成 Bug 特征指纹（用于快速去重）"""
    # 提取关键特征
    key_features = [
        bug.get('symptom', ''),
        bug.get('system', ''),
        bug.get('operation', '')
    ]
    
    # 生成指纹
    fingerprint = hashlib.md5(
        '|'.join(key_features).encode()
    ).hexdigest()[:12]
    
    return fingerprint

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Bug 记忆查重工具')
    parser.add_argument('--symptom', type=str, help='新 Bug 症状')
    parser.add_argument('--text', type=str, help='新 Bug 描述')
    parser.add_argument('--system', type=str, help='影响系统')
    parser.add_argument('--threshold', type=float, default=0.7, help='相似度阈值')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔍 Bug 记忆查重")
    print("=" * 70)
    print()
    
    # 准备新 Bug
    new_bug = {
        'symptom': args.symptom or '',
        'text': args.text or '',
        'system': args.system or ''
    }
    
    print(f"📋 新 Bug 特征:")
    print(f"   症状：{new_bug['symptom']}")
    print(f"   系统：{new_bug['system']}")
    print()
    
    # 查重
    similar_bugs = check_duplicate(new_bug, threshold=args.threshold)
    
    if not similar_bugs:
        print("✅ 未发现相似 Bug，可以归档\n")
        
        # 生成指纹
        fingerprint = generate_fingerprint(new_bug)
        print(f"🔑 特征指纹：{fingerprint}")
        print()
    else:
        print(f"⚠️  发现 {len(similar_bugs)} 个相似 Bug，可能重复！\n")
        
        print("📋 相似 Bug 列表:\n")
        
        for i, bug in enumerate(similar_bugs, 1):
            print(f"{i}. 🐛 {bug['bug_id']}")
            print(f"   相似度：{bug['similarity']*100:.1f}%")
            print(f"   症状：{bug['symptom']}")
            print(f"   文件：{bug['file']}")
            print()
        
        print("=" * 70)
        print("\n💡 建议:")
        print("   1. 查看相似 Bug 的解决方案")
        print("   2. 如果是同一问题，不要重复归档")
        print("   3. 如果是不同问题，降低阈值后重试")
        print()

if __name__ == "__main__":
    main()
