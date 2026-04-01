#!/usr/bin/env python3
"""
从 OpenClaw 真实对话中收集反馈数据 V2

简化版：直接提取所有用户查询，然后从 LanceDB 检索记忆
"""

import json
import os
import lancedb
from pathlib import Path
from datetime import datetime
import random

# 配置
SESSIONS_DIR = '/home/kyj/.openclaw/agents/main/sessions'
DB_PATH = '/home/kyj/.openclaw/workspace/lancedb'
OUTPUT_DIR = '/home/kyj/.openclaw/workspace/memory-lancedb-pro/datasets'
LABELING_FILE = f'{OUTPUT_DIR}/feedback_labeling.jsonl'

def load_recent_sessions(top_n=20):
    """加载最近的会话"""
    sessions = []
    
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
                
                if len(messages) > 5:
                    sessions.append({
                        'file': str(f),
                        'messages': messages
                    })
        except:
            continue
    
    return sessions

def extract_user_queries(sessions, max_queries=100):
    """从会话中提取用户查询"""
    queries = []
    
    for session in sessions:
        for msg in session['messages']:
            if msg.get('message', {}).get('role') != 'user':
                continue
            
            content_list = msg['message'].get('content', [])
            if not content_list or not isinstance(content_list, list):
                continue
            
            text = content_list[0].get('text', '')
            
            # 过滤
            if not text or text.startswith('<') or text.startswith('System:') or text.startswith('[cron:'):
                continue
            
            # 限制长度
            if len(text) > 300:
                text = text[:300]
            
            queries.append({
                'query': text,
                'session': Path(session['file']).name
            })
            
            if len(queries) >= max_queries:
                break
        
        if len(queries) >= max_queries:
            break
    
    return queries

def retrieve_memories_for_query(query_text, db, top_k=5):
    """从 LanceDB 检索相关记忆"""
    try:
        table = db.open_table('memories')
        
        # 简单关键词检索
        results = table.search(query_text).limit(top_k).to_list()
        
        return [r.get('text', '') for r in results]
    except Exception as e:
        print(f"   检索失败：{e}")
        return []

def create_labeling_tasks(queries, db, output_file):
    """创建标注任务"""
    tasks = []
    
    print(f"\n开始创建标注任务...")
    
    for i, query_item in enumerate(queries):
        query = query_item['query']
        
        # 检索记忆
        memories = retrieve_memories_for_query(query, db, top_k=3)
        
        # 为每个记忆创建标注任务
        for memory in memories:
            task = {
                'id': f"task_{len(tasks)}",
                'query': query,
                'memory': memory,
                'label': None,  # 待标注
                'query_source': query_item['session']
            }
            tasks.append(task)
        
        if (i + 1) % 20 == 0:
            print(f"   进度：{i+1}/{len(queries)}")
    
    # 保存
    with open(output_file, 'w') as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')
    
    return tasks

def main():
    print("="*60)
    print("OpenClaw 真实反馈数据收集 V2")
    print("="*60)
    
    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. 加载会话
    print("\n1. 加载最近的会话...")
    sessions = load_recent_sessions(top_n=20)
    print(f"   找到 {len(sessions)} 个会话")
    
    # 2. 提取查询
    print("\n2. 提取用户查询...")
    queries = extract_user_queries(sessions, max_queries=100)
    print(f"   提取 {len(queries)} 个查询")
    
    # 3. 连接数据库
    print("\n3. 连接 LanceDB...")
    try:
        db = lancedb.connect(DB_PATH)
        print(f"   ✅ 已连接：{DB_PATH}")
    except Exception as e:
        print(f"   ❌ 连接失败：{e}")
        print(f"   使用备用记忆数据...")
        db = None
    
    # 4. 创建标注任务
    print("\n4. 创建标注任务...")
    
    if db:
        tasks = create_labeling_tasks(queries, db, LABELING_FILE)
    else:
        # 备用：使用 synthetic 记忆
        print("   使用备用记忆数据...")
        tasks = []
        with open('/home/kyj/.openclaw/workspace/synthetic_perltqa/memories_small.json') as f:
            memories = json.load(f)
        
        for query_item in queries[:50]:
            for memory in random.sample(memories, min(3, len(memories))):
                task = {
                    'id': f"task_{len(tasks)}",
                    'query': query_item['query'],
                    'memory': memory['content'],
                    'label': None,
                    'query_source': query_item['session']
                }
                tasks.append(task)
        
        with open(LABELING_FILE, 'w') as f:
            for task in tasks:
                f.write(json.dumps(task, ensure_ascii=False) + '\n')
    
    print(f"   创建 {len(tasks)} 个标注任务")
    print(f"   标注文件：{LABELING_FILE}")
    
    # 5. 显示说明
    print("\n" + "="*60)
    print("标注说明")
    print("="*60)
    print(f"""
下一步：
1. 打开标注文件：{LABELING_FILE}
2. 手动标注每个任务的相关性（每行一个 JSON）：
   - "label": 1 (记忆与查询相关/有用)
   - "label": 0 (记忆与查询无关/无用)
3. 标注完成后运行：
   python scripts/collect_real_feedback_v2.py --export

示例标注任务：
""")
    
    random.shuffle(tasks)
    for i, task in enumerate(tasks[:2]):
        print(f"\n任务 {i+1}:")
        print(f"  查询：{task['query'][:80]}...")
        print(f"  记忆：{task['memory'][:80]}...")
        print(f"  标注：\"label\": ? (填写 0 或 1)")
    
    print("\n" + "="*60)
    print("✅ 标注任务已创建！")
    print("="*60)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--export':
        # 导出已标注的数据集
        print("导出已标注的数据集...")
        
        labeled_data = []
        with open(LABELING_FILE, 'r') as f:
            for line in f:
                task = json.loads(line)
                if task.get('label') is not None:
                    labeled_data.append({
                        'query': task['query'],
                        'memory': task['memory'],
                        'label': task['label'],
                        'source': task.get('query_source', 'unknown')
                    })
        
        output_file = f'{OUTPUT_DIR}/openclaw_real_labeled.jsonl'
        with open(output_file, 'w') as f:
            for item in labeled_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        positive = sum(1 for d in labeled_data if d['label'] == 1)
        negative = sum(1 for d in labeled_data if d['label'] == 0)
        
        print(f"\n数据集统计:")
        print(f"   总样本：{len(labeled_data)}")
        print(f"   正样本：{positive} ({positive/len(labeled_data)*100:.1f}%)")
        print(f"   负样本：{negative} ({negative/len(labeled_data)*100:.1f}%)")
        print(f"\n✅ 已导出：{output_file}")
    else:
        main()
