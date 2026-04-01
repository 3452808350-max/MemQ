#!/usr/bin/env python3
"""
自动标注 + 人工审核

流程：
1. 使用简单规则自动标注（关键词匹配）
2. 导出低置信度样本供人工审核
3. 合并自动 + 人工标注
"""

import json
import os
from datetime import datetime

LABELING_FILE = '/home/kyj/.openclaw/workspace/memory-lancedb-pro/datasets/feedback_labeling.jsonl'
AUTO_LABELD_FILE = '/home/kyj/.openclaw/workspace/memory-lancedb-pro/datasets/auto_labeled.jsonl'
REVIEW_FILE = '/home/kyj/.openclaw/workspace/memory-lancedb-pro/datasets/need_review.jsonl'
FINAL_FILE = '/home/kyj/.openclaw/workspace/memory-lancedb-pro/datasets/openclaw_real_labeled.jsonl'

def extract_keywords(text):
    """提取关键词"""
    # 简化：提取项目名、技术名词等
    keywords = []
    
    # 项目名
    projects = ['OpenClaw', 'DSS', 'Kimi', 'RAG', 'LanceDB', 'BM25', 'vLLM', 'Ollama']
    for p in projects:
        if p.lower() in text.lower():
            keywords.append(p)
    
    # 技术词
    techs = ['API', 'GPU', 'API', '部署', '检索', '记忆', '记忆']
    for t in techs:
        if t.lower() in text.lower():
            keywords.append(t)
    
    return keywords

def auto_label(query, memory):
    """
    自动标注规则
    
    规则：
    1. 有共同关键词 → label=1
    2. 无共同关键词 → label=0
    """
    query_keywords = set(extract_keywords(query))
    memory_keywords = set(extract_keywords(memory))
    
    # 计算重叠
    overlap = query_keywords & memory_keywords
    
    if len(overlap) >= 1:
        # 有重叠，标注为相关
        return 1, f"关键词匹配：{overlap}"
    else:
        # 无重叠，标注为不相关
        return 0, "无关键词匹配"

def main():
    print("="*60)
    print("自动标注 + 人工审核")
    print("="*60)
    
    # 1. 加载任务
    print("\n1. 加载任务...")
    tasks = []
    with open(LABELING_FILE, 'r') as f:
        for line in f:
            tasks.append(json.loads(line))
    print(f"   共 {len(tasks)} 个任务")
    
    # 2. 自动标注
    print("\n2. 自动标注...")
    auto_labeled = []
    need_review = []
    
    for task in tasks:
        label, reason = auto_label(task['query'], task['memory'])
        
        task['auto_label'] = label
        task['auto_reason'] = reason
        task['confidence'] = 'high' if label == 1 else 'low'
        task['timestamp'] = datetime.now().isoformat()
        
        if label == 1:
            auto_labeled.append(task)
        else:
            need_review.append(task)
    
    print(f"   自动标注：{len(auto_labeled)} 个（相关）")
    print(f"   需要审核：{len(need_review)} 个（不相关，需人工确认）")
    
    # 3. 保存自动标注结果
    print("\n3. 保存结果...")
    
    with open(AUTO_LABELD_FILE, 'w') as f:
        for task in auto_labeled:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')
    
    with open(REVIEW_FILE, 'w') as f:
        for task in need_review:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')
    
    print(f"   ✅ 自动标注：{AUTO_LABELD_FILE}")
    print(f"   ✅ 待审核：{REVIEW_FILE}")
    
    # 4. 显示审核样本
    print("\n4. 待审核样本（前 10 个）:")
    for i, task in enumerate(need_review[:10]):
        print(f"\n   样本 {i+1}:")
        print(f"   查询：{task['query'][:80]}...")
        print(f"   记忆：{task['memory'][:80]}...")
        print(f"   自动标注：❌ 不相关")
        print(f"   理由：{task['auto_reason']}")
        print(f"   人工标注：[待填写]")
    
    # 5. 审核说明
    print("\n" + "="*60)
    print("人工审核说明")
    print("="*60)
    print(f"""
下一步：
1. 打开审核文件：{REVIEW_FILE}
2. 为每个任务添加人工标注：
   "manual_label": 1  (确实不相关，确认自动标注)
   "manual_label": 0  (实际相关，纠正自动标注)

3. 合并结果：
   python scripts/auto_label_with_review.py --merge

示例审核任务：
""")
    
    for i, task in enumerate(need_review[:2]):
        print(f"\n样本 {i+1}:")
        print(f"  查询：{task['query'][:60]}...")
        print(f"  记忆：{task['memory'][:60]}...")
        print(f"  添加：\"manual_label\": 0 或 1")

def merge_results():
    """合并自动标注和人工审核结果"""
    print("合并标注结果...")
    
    # 加载自动标注
    auto_labeled = []
    with open(AUTO_LABELD_FILE, 'r') as f:
        for line in f:
            task = json.loads(line)
            # 为自动标注样本设置 label
            task['label'] = task.get('auto_label', 0)
            auto_labeled.append(task)
    
    # 加载人工审核
    manual_reviewed = []
    with open(REVIEW_FILE, 'r') as f:
        for line in f:
            task = json.loads(line)
            if task.get('manual_label') is not None:
                # 使用人工标注覆盖自动标注
                task['label'] = task['manual_label']
                manual_reviewed.append(task)
    
    # 合并
    all_labeled = auto_labeled + manual_reviewed
    
    # 保存最终结果
    with open(FINAL_FILE, 'w') as f:
        for task in all_labeled:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')
    
    # 统计
    total = len(all_labeled)
    positive = sum(1 for t in all_labeled if t.get('label') == 1)
    negative = total - positive
    manual_count = len(manual_reviewed)
    
    print(f"\n📊 最终数据集:")
    print(f"   总样本：{total}")
    print(f"   正样本：{positive} ({positive/total*100:.1f}%)")
    print(f"   负样本：{negative} ({negative/total*100:.1f}%)")
    print(f"   人工审核：{manual_count}/{len(all_labeled)}")
    print(f"\n✅ 已导出：{FINAL_FILE}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--merge':
        merge_results()
    else:
        main()
