#!/usr/bin/env python3
"""
批量标注记忆相关性数据

使用关键词匹配来判断查询和记忆的相关性
"""

import json
import re

INPUT_FILE = '/home/kyj/.openclaw/workspace/memory-lancedb-pro/datasets/need_review.jsonl'
OUTPUT_FILE = '/home/kyj/.openclaw/workspace/memory-lancedb-pro/datasets/need_review.jsonl'

# 项目/主题关键词映射
PROJECT_KEYWORDS = {
    'DSS': ['dss', '选股', '股票', '金融', '量化', '交易', '开盘', '收盘', '预测', '建模', '数学论文'],
    'OpenClaw': ['openclaw'],
    'subagent': ['subagent', 'multi-agent', '多 agent', '暗号', 'skill', '多 agant'],
    'Kimi': ['kimi', 'kimi-remote'],
    'RAG': ['rag', '检索', 'rerank', '向量检索', 'bm25', 'embedding'],
    'Ollama': ['ollama', '部署'],
    'vLLM': ['vllm', '性能优化'],
    '知识图谱': ['知识图谱', '图谱'],
    '智能客服': ['智能客服', '客服'],
    'AI-Agent': ['ai-agent', 'agent', '智能体'],
    'memory-lancedb': ['memory-lancedb', 'lancedb', '记忆'],
    '雅思': ['雅思', 'ielts', '听力', '阅读', '写作', '口语', '单词', '学习提醒'],
    'Qwen': ['qwen', '通义千问'],
}

def extract_topics(text):
    """提取文本中的所有主题"""
    text_lower = text.lower()
    topics = set()
    
    for project, keywords in PROJECT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                topics.add(project)
                break
    
    return topics

def should_label_as_relevant(query, memory):
    """
    判断是否应该标注为相关 (label=1)
    
    相关的情况：
    1. 查询和记忆有共同的主题/关键词
    2. 记忆能帮助回答查询
    """
    query_topics = extract_topics(query)
    memory_topics = extract_topics(memory)
    
    # 计算共同主题
    common_topics = query_topics & memory_topics
    
    if common_topics:
        return True, f"共同主题：{common_topics}"
    
    # 特殊情况：subagent 相关
    if 'subagent' in query.lower() and 'subagent' in memory.lower():
        return True, "都包含 subagent"
    
    # 默认：不相关
    return False, "无共同主题"

def main():
    print("="*60)
    print("批量标注记忆相关性")
    print("="*60)
    
    # 读取数据
    tasks = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            tasks.append(json.loads(line))
    
    print(f"\n共 {len(tasks)} 个任务需要标注")
    
    # 标注统计
    stats = {'label_1': 0, 'label_0': 0}
    
    # 标注结果
    labeled_tasks = []
    
    for i, task in enumerate(tasks):
        query = task['query']
        memory = task['memory']
        
        # 判断相关性
        is_relevant, reason = should_label_as_relevant(query, memory)
        manual_label = 1 if is_relevant else 0
        
        task['manual_label'] = manual_label
        task['label_reason'] = reason
        
        stats[f'label_{manual_label}'] += 1
        labeled_tasks.append(task)
        
        # 显示进度
        if (i + 1) % 50 == 0:
            print(f"已处理 {i+1}/{len(tasks)} ...")
    
    # 保存结果（覆盖原文件）
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for task in labeled_tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')
    
    print(f"\n✅ 标注完成！")
    print(f"\n📊 标注统计:")
    print(f"   相关 (label=1): {stats['label_1']}")
    print(f"   不相关 (label=0): {stats['label_0']}")
    print(f"\n📁 结果已保存到：{OUTPUT_FILE}")
    
    # 显示一些标注为相关的样本
    relevant_samples = [t for t in labeled_tasks if t['manual_label'] == 1]
    if relevant_samples:
        print(f"\n📋 标注为相关的样本（前 10 个）:")
        for i, task in enumerate(relevant_samples[:10]):
            print(f"\n   {i+1}. {task['id']}")
            print(f"      查询：{task['query'][:60]}...")
            print(f"      记忆：{task['memory'][:60]}...")
            print(f"      理由：{task['label_reason']}")

if __name__ == '__main__':
    main()
