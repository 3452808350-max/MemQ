#!/usr/bin/env python3
"""
交互式标注工具 - 分段批量处理

功能：
1. 每次显示 10 个任务
2. 批量标注（输入 1010101010）
3. 自动保存进度
4. 支持随时退出
"""

import json
import os
from datetime import datetime

LABELING_FILE = '/home/kyj/.openclaw/workspace/memory-lancedb-pro/datasets/feedback_labeling.jsonl'
PROGRESS_FILE = '/home/kyj/.openclaw/workspace/memory-lancedb-pro/datasets/labeling_progress.json'
BATCH_SIZE = 10

def load_tasks():
    """加载所有任务"""
    tasks = []
    with open(LABELING_FILE, 'r') as f:
        for line in f:
            tasks.append(json.loads(line))
    return tasks

def save_tasks(tasks):
    """保存所有任务"""
    with open(LABELING_FILE, 'w') as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')

def load_progress():
    """加载进度"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'current_index': 0, 'labeled_count': 0}

def save_progress(progress):
    """保存进度"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def display_task(task, index):
    """显示单个任务"""
    print(f"\n--- 任务 {index + 1} ---")
    print(f"查询：{task['query'][:150]}...")
    print(f"记忆：{task['memory'][:150]}...")
    
    if task.get('label') is not None:
        print(f"已标注：{'✅ 相关' if task['label'] == 1 else '❌ 不相关'}")
    else:
        print(f"标注：[待标注]")

def label_batch(tasks, start_index):
    """标注一批任务"""
    print(f"\n{'='*60}")
    print(f"批次 {start_index // BATCH_SIZE + 1}")
    print(f"{'='*60}")
    
    batch_end = min(start_index + BATCH_SIZE, len(tasks))
    labels = []
    
    # 显示本批次任务
    for i in range(start_index, batch_end):
        display_task(tasks[i], i)
    
    # 批量输入
    print(f"\n{'='*60}")
    print(f"请输入 {batch_end - start_index} 个标注（1=相关，0=不相关）")
    print(f"示例：1010101010")
    print(f"输入 'q' 退出，'s' 跳过本批次")
    print(f"{'='*60}")
    
    user_input = input("\n标注：").strip()
    
    if user_input.lower() == 'q':
        print("\n✅ 已保存进度，下次继续！")
        return False
    
    if user_input.lower() == 's':
        print("\n⏭️  跳过本批次")
        return True
    
    # 验证输入
    if len(user_input) != (batch_end - start_index) or not all(c in '01' for c in user_input):
        print(f"\n❌ 输入错误！需要 {batch_end - start_index} 个 0 或 1")
        return True
    
    # 应用标注
    for i, char in enumerate(user_input):
        task_index = start_index + i
        tasks[task_index]['label'] = int(char)
        labels.append(int(char))
    
    # 统计本批次
    positive_count = sum(labels)
    negative_count = len(labels) - positive_count
    
    print(f"\n✅ 本批次标注完成！")
    print(f"   相关：{positive_count} 条")
    print(f"   不相关：{negative_count} 条")
    
    return True

def export_labeled():
    """导出已标注的数据集"""
    tasks = load_tasks()
    
    labeled_tasks = [t for t in tasks if t.get('label') is not None]
    
    if not labeled_tasks:
        print("\n❌ 还没有标注数据！")
        return
    
    # 导出
    output_file = '/home/kyj/.openclaw/workspace/memory-lancedb-pro/datasets/openclaw_real_labeled.jsonl'
    with open(output_file, 'w') as f:
        for task in labeled_tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')
    
    # 统计
    positive = sum(1 for t in labeled_tasks if t['label'] == 1)
    negative = len(labeled_tasks) - positive
    
    print(f"\n📊 数据集统计:")
    print(f"   总样本：{len(labeled_tasks)}")
    print(f"   正样本：{positive} ({positive/len(labeled_tasks)*100:.1f}%)")
    print(f"   负样本：{negative} ({negative/len(labeled_tasks)*100:.1f}%)")
    print(f"   输出文件：{output_file}")

def main():
    print("="*60)
    print("交互式标注工具 - 分段批量处理")
    print("="*60)
    
    # 加载任务
    print("\n1. 加载任务...")
    tasks = load_tasks()
    print(f"   共 {len(tasks)} 个任务")
    
    # 加载进度
    print("\n2. 加载进度...")
    progress = load_progress()
    labeled_count = sum(1 for t in tasks if t.get('label') is not None)
    print(f"   已标注：{labeled_count}/{len(tasks)}")
    
    # 主循环
    current_index = progress.get('current_index', 0)
    
    while current_index < len(tasks):
        # 标注一批
        if not label_batch(tasks, current_index):
            # 用户退出
            save_progress({'current_index': current_index, 'labeled_count': labeled_count})
            save_tasks(tasks)
            return
        
        # 更新进度
        current_index += BATCH_SIZE
        labeled_count = sum(1 for t in tasks if t.get('label') is not None)
        save_progress({'current_index': current_index, 'labeled_count': labeled_count})
        save_tasks(tasks)
    
    # 完成
    print("\n" + "="*60)
    print("🎉 所有任务标注完成！")
    print("="*60)
    
    # 导出
    export_labeled()
    
    # 清理进度文件
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
    print("\n✅ 完成！")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--export':
        export_labeled()
    else:
        main()
