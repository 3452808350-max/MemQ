#!/usr/bin/env python3
"""
Bug 排查记忆检索工具
通过现象特征快速查找历史 Bug 和解决方案

核心：现象特征优先，原因辅助

使用方法:
    python3 search_bug_memory.py --symptom "召回率低"
    python3 search_bug_memory.py --system memory-lancedb-pro
    python3 search_bug_memory.py --operation "查询"
    python3 search_bug_memory.py --environment OpenClaw
"""

import json
import argparse
from pathlib import Path

def load_bug_memories():
    """加载所有 Bug 记忆"""
    bug_files = list(Path('.').glob('bug_*.json'))
    bugs = []
    
    for file in bug_files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        bug = data.get('bug_memory', {})
        bugs.append({
            'file': file,
            'bug': bug,
            'metadata': bug.get('metadata', {})
        })
    
    return bugs

def match_symptom(bug_metadata, symptom_keywords):
    """匹配症状特征"""
    score = 0
    
    # 检查现象特征
    symptom_feat = bug_metadata.get('🔍 现象特征', {})
    symptom_text = symptom_feat.get('symptom', '')
    error_msg = symptom_feat.get('error_message', '')
    
    # 检查文本描述
    bug_text = bug_metadata.get('text', '')
    
    # 合并所有文本
    all_text = f"{symptom_text} {error_msg} {bug_text}".lower()
    
    # 匹配关键词
    for kw in symptom_keywords:
        if kw.lower() in all_text:
            score += 1
    
    return score

def match_environment(bug_metadata, env_keywords):
    """匹配环境特征"""
    score = 0
    
    env_feat = bug_metadata.get('🔍 现象特征', {})
    env_text = env_feat.get('environment', '').lower()
    
    for kw in env_keywords:
        if kw.lower() in env_text:
            score += 1
    
    return score

def match_operation(bug_metadata, op_keywords):
    """匹配操作特征"""
    score = 0
    
    env_feat = bug_metadata.get('🔍 现象特征', {})
    op_text = env_feat.get('operation', '').lower()
    
    for kw in op_keywords:
        if kw.lower() in op_text:
            score += 1
    
    return score

def match_system(bug_metadata, system):
    """匹配影响系统"""
    impact = bug_metadata.get('📊 影响范围', {})
    affected = impact.get('affected_system', '').lower()
    return 1 if system.lower() in affected else 0

def search_bugs(symptom=None, system=None, operation=None, environment=None, limit=10):
    """搜索 Bug"""
    bugs = load_bug_memories()
    
    if not bugs:
        return []
    
    results = []
    
    # 关键词处理
    symptom_keywords = symptom.split() if symptom else []
    env_keywords = environment.split() if environment else []
    op_keywords = operation.split() if operation else []
    
    for bug_data in bugs:
        meta = bug_data['metadata']
        
        # 计算匹配分数
        total_score = 0
        
        # 症状匹配（权重最高）
        if symptom_keywords:
            symptom_score = match_symptom(meta, symptom_keywords)
            total_score += symptom_score * 3  # 症状权重 3x
        
        # 系统匹配（权重高）
        if system:
            system_score = match_system(meta, system)
            total_score += system_score * 2  # 系统权重 2x
        
        # 操作匹配（权重中）
        if op_keywords:
            op_score = match_operation(meta, op_keywords)
            total_score += op_score * 1.5  # 操作权重 1.5x
        
        # 环境匹配（权重低）
        if env_keywords:
            env_score = match_environment(meta, env_keywords)
            total_score += env_score * 1  # 环境权重 1x
        
        if total_score > 0:
            results.append({
                'bug': bug_data['bug'],
                'metadata': meta,
                'score': total_score
            })
    
    # 按分数排序
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results[:limit]

def format_bug(result):
    """格式化显示 Bug"""
    bug = result['bug']
    meta = result['metadata']
    score = result['score']
    
    print("\n" + "=" * 70)
    print(f"🐛 Bug ID: {meta.get('bug_id', 'N/A')}")
    print(f"   匹配度：{'⭐' * int(min(score, 5))} ({score:.1f})")
    print("=" * 70)
    
    print(f"\n📋 Bug 描述:\n{bug.get('text', 'N/A')}\n")
    
    # 现象特征
    print("🔍 现象特征:")
    symptom_feat = meta.get('🔍 现象特征', {})
    print(f"   环境：{symptom_feat.get('environment', 'N/A')}")
    print(f"   操作：{symptom_feat.get('operation', 'N/A')}")
    print(f"   症状：{symptom_feat.get('symptom', 'N/A')}")
    print(f"   错误：{symptom_feat.get('error_message', 'N/A')}")
    print(f"   频率：{symptom_feat.get('frequency', 'N/A')}")
    print(f"   可复现：{symptom_feat.get('reproducible', 'N/A')}")
    print()
    
    # 影响范围
    print("📊 影响范围:")
    impact = meta.get('📊 影响范围', {})
    print(f"   系统：{impact.get('affected_system', 'N/A')}")
    print(f"   模块：{impact.get('affected_module', 'N/A')}")
    print(f"   严重：{impact.get('severity', 'N/A')}")
    print(f"   影响：{impact.get('user_impact', 'N/A')}")
    print()
    
    # 根因
    print("🔎 根因:")
    root_cause = meta.get('🔎 根因分析', {})
    print(f"   原因：{root_cause.get('root_cause', 'N/A')}")
    print(f"   分类：{root_cause.get('cause_category', 'N/A')}")
    print()
    
    # 解决方案
    print("✅ 解决方案:")
    solution = meta.get('✅ 解决方案', {})
    print(f"   解决：{solution.get('solution', 'N/A')}")
    print(f"   临时：{solution.get('workaround', 'N/A')}")
    print(f"   时间：{solution.get('resolution_time', 'N/A')}")
    print()
    
    # 标签
    print(f"🏷️  标签：{', '.join(bug.get('tags', []))}")
    print()

def main():
    parser = argparse.ArgumentParser(description='Bug 排查记忆检索工具')
    parser.add_argument('--symptom', type=str, help='按症状搜索（如：召回率低、数据缺失）')
    parser.add_argument('--system', type=str, help='按影响系统搜索')
    parser.add_argument('--operation', type=str, help='按操作搜索')
    parser.add_argument('--environment', type=str, help='按环境搜索')
    parser.add_argument('--limit', type=int, default=5, help='返回结果数量')
    parser.add_argument('--list', action='store_true', help='列出所有 Bug')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔍 Bug 排查记忆检索")
    print("=" * 70)
    print()
    
    if args.list:
        print("📋 列出所有 Bug 记忆...\n")
        results = search_bugs(limit=args.limit)
    else:
        results = search_bugs(
            symptom=args.symptom,
            system=args.system,
            operation=args.operation,
            environment=args.environment,
            limit=args.limit
        )
    
    if not results:
        print("\n❌ 未找到匹配的 Bug 记忆\n")
        print("💡 建议:")
        print("   1. 尝试其他关键词")
        print("   2. 减少关键词数量")
        print("   3. 查看 bug_memory_spec.md 了解可用特征值")
        return
    
    print(f"✅ 找到 {len(results)} 个相关 Bug:\n")
    
    for result in results:
        format_bug(result)
    
    print("=" * 70)
    print(f"📊 共找到 {len(results)} 个 Bug")
    print("=" * 70)
    print()
    print("💡 检索提示:")
    print("   - 症状匹配权重最高（因为现象最重要）")
    print("   - 系统匹配权重次之")
    print("   - 操作和环境匹配权重较低")
    print("   - 新问题无匹配时，参考根因分类")
    print()

if __name__ == "__main__":
    main()
