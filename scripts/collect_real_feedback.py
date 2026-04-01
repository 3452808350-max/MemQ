#!/usr/bin/env python3
"""
从 OpenClaw 真实对话中收集反馈数据

流程：
1. 提取用户查询和检索到的记忆
2. 生成标注任务（用户标注相关性）
3. 导出标注数据集
"""

import json
import os
from pathlib import Path
from datetime import datetime
import random

# 配置
SESSIONS_DIR = '/home/kyj/.openclaw/agents/main/sessions'
OUTPUT_DIR = '/home/kyj/.openclaw/workspace/memory-lancedb-pro/datasets'
LABELING_FILE = '/home/kyj/.openclaw/workspace/memory-lancedb-pro/datasets/feedback_labeling.jsonl'

def load_recent_sessions(top_n=50):
    """加载最近的会话"""
    sessions = []
    
    # 按修改时间排序
    session_files = sorted(
        Path(SESSIONS_DIR).glob('*.jsonl'),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    
    for f in session_files[:top_n]:
        if '.deleted' in str(f) or '.reset' in str(f) or '.lock' in str(f):
            continue
        
        try:
            with open(f, 'r') as file:
                messages = []
                for line in file:
                    try:
                        data = json.loads(line)
                        if data.get('type') == 'message':
                            messages.append(data)
                    except:
                        continue
                
                if len(messages) > 10:
                    sessions.append({
                        'file': str(f),
                        'messages': messages,
                        'modified': datetime.fromtimestamp(f.stat().st_mtime)
                    })
        except:
            continue
    
    return sessions

def extract_queries_with_memories(sessions):
    """提取用户查询和对应的记忆引用"""
    samples = []
    
    for session in sessions:
        messages = session['messages']
        
        for i, msg in enumerate(messages):
            # 查找用户查询
            if msg.get('message', {}).get('role') != 'user':
                continue
            
            content_list = msg['message'].get('content', [])
            if not content_list or not isinstance(content_list, list):
                continue
            
            query_text = content_list[0].get('text', '')
            
            # 过滤系统消息
            if not query_text or query_text.startswith('<') or query_text.startswith('System:'):
                continue
            
            # 查找前一个 AI 回复中的记忆引用
            memory_snippets = []
            for j in range(i-1, max(0, i-5), -1):
                prev_msg = messages[j].get('message', {})
                if prev_msg.get('role') == 'assistant':
                    prev_content = prev_msg.get('content', [{}])[0].get('text', '')
                    
                    # 提取记忆相关段落
                    if '记忆' in prev_content or 'memory' in prev_content.lower():
                        # 简单分割段落
                        paragraphs = prev_content.split('\n')
                        for para in paragraphs[:10]:
                            if len(para) > 30 and len(para) < 300:
                                memory_snippets.append(para.strip())
                    break
            
            # 添加样本
            if query_text and memory_snippets:
                samples.append({
                    'query': query_text[:200],
                    'memories': memory_snippets[:5],  # 最多 5 条记忆
                    'session': Path(session['file']).name,
                    'timestamp': session['modified'].isoformat()
                })
    
    return samples

def create_labeling_tasks(samples, output_file):
    """创建标注任务文件"""
    tasks = []
    
    for sample in samples:
        for memory in sample['memories']:
            task = {
                'id': f"task_{len(tasks)}",
                'query': sample['query'],
                'memory': memory,
                'label': None,  # 待标注
                'query_source': sample['session'],
                'timestamp': sample['timestamp']
            }
            tasks.append(task)
    
    # 保存标注任务
    with open(output_file, 'w') as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')
    
    return tasks

def export_labeled_dataset(input_file, output_file):
    """导出已标注的数据集"""
    labeled_data = []
    
    with open(input_file, 'r') as f:
        for line in f:
            task = json.loads(line)
            if task.get('label') is not None:  # 已标注
                labeled_data.append({
                    'query': task['query'],
                    'memory': task['memory'],
                    'label': task['label'],  # 1=相关，0=不相关
                    'source': task['query_source']
                })
    
    with open(output_file, 'w') as f:
        for item in labeled_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    # 统计
    positive = sum(1 for d in labeled_data if d['label'] == 1)
    negative = sum(1 for d in labeled_data if d['label'] == 0)
    
    print(f"\n数据集统计:")
    print(f"   总样本：{len(labeled_data)}")
    print(f"   正样本：{positive} ({positive/len(labeled_data)*100:.1f}%)")
    print(f"   负样本：{negative} ({negative/len(labeled_data)*100:.1f}%)")
    
    return labeled_data

def main():
    print("="*60)
    print("OpenClaw 真实反馈数据收集")
    print("="*60)
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. 加载会话
    print("\n1. 加载最近的会话...")
    sessions = load_recent_sessions(top_n=50)
    print(f"   找到 {len(sessions)} 个会话")
    
    if not sessions:
        print("   ❌ 未找到会话文件")
        return
    
    # 显示最近的几个会话
    print("\n   最近的会话:")
    for i, session in enumerate(sessions[:5]):
        print(f"   {i+1}. {Path(session['file']).name}: {len(session['messages'])} 条消息")
    
    # 2. 提取查询和记忆
    print("\n2. 提取查询和记忆...")
    samples = extract_queries_with_memories(sessions)
    print(f"   提取 {len(samples)} 个查询样本")
    
    if not samples:
        print("   ❌ 未找到有效样本")
        return
    
    # 3. 创建标注任务
    print("\n3. 创建标注任务...")
    tasks = create_labeling_tasks(samples, LABELING_FILE)
    print(f"   创建 {len(tasks)} 个标注任务")
    print(f"   标注文件：{LABELING_FILE}")
    
    # 4. 显示标注说明
    print("\n" + "="*60)
    print("标注说明")
    print("="*60)
    print(f"""
下一步：
1. 打开标注文件：{LABELING_FILE}
2. 手动标注每个任务的相关性：
   - label: 1 (记忆与查询相关/有用)
   - label: 0 (记忆与查询无关/无用)
3. 标注完成后运行：
   python scripts/collect_real_feedback.py --export

示例标注任务：
""")
    
    for i, task in enumerate(tasks[:2]):
        print(f"\n任务 {i+1}:")
        print(f"  查询：{task['query'][:80]}...")
        print(f"  记忆：{task['memory'][:80]}...")
        print(f"  标注：label = ? (填写 0 或 1)")
    
    print("\n" + "="*60)
    print("✅ 标注任务已创建！")
    print("="*60)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--export':
        # 导出已标注的数据集
        print("导出已标注的数据集...")
        labeled_data = export_labeled_dataset(
            LABELING_FILE,
            f'{OUTPUT_DIR}/openclaw_real_labeled.jsonl'
        )
        print(f"\n✅ 已导出：{OUTPUT_DIR}/openclaw_real_labeled.jsonl")
    else:
        # 创建标注任务
        main()
