#!/usr/bin/env python3
"""
话题切换检测 + 自动记忆保存

功能：
1. 检测用户是否开始新话题
2. 自动保存当前对话到记忆文件
3. 清空 context（通过标记）

使用方式：
- 在 Gateway 启动时运行
- 或作为独立脚本调用
"""

import os
import json
from datetime import datetime
from pathlib import Path

WORKSPACE = Path('/home/kyj/.openclaw/workspace')
MEMORY_DIR = WORKSPACE / 'memory'
CONTEXT_FILE = WORKSPACE / '.current_topic.json'

# 话题切换触发词
TOPIC_SWITCH_TRIGGERS = [
    '新的话题', '换个话题', '聊点别的', '说点别的',
    '准备', '开始', '结束', '完成', '告一段落',
    'ok', '好的', '明白了', '懂了',
    '下一个', '继续', '然后',
]

def detect_topic_switch(text: str) -> bool:
    """检测是否是话题切换"""
    text_lower = text.lower()
    
    # 检查触发词
    for trigger in TOPIC_SWITCH_TRIGGERS:
        if trigger in text_lower:
            return True
    
    # 检查是否包含总结性表述
    if any(x in text for x in ['总结一下', '总结一下', '完成总结', '记录一下']):
        return True
    
    return False


def save_current_topic(topic_name: str, summary: str, key_points: list):
    """保存当前话题到记忆文件"""
    MEMORY_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    memory = {
        'topic': topic_name,
        'timestamp': timestamp,
        'summary': summary,
        'key_points': key_points,
        'file': f'topic-{topic_name.lower().replace(" ", "-")}.md'
    }
    
    # 写入 Markdown 文件
    md_file = MEMORY_DIR / memory['file']
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# 💾 记忆载入：{topic_name}\n\n")
        f.write(f"**时间**: {timestamp}\n\n")
        f.write(f"## 📋 摘要\n\n{summary}\n\n")
        f.write(f"## 🔑 关键点\n\n")
        for i, point in enumerate(key_points, 1):
            f.write(f"{i}. {point}\n")
        f.write(f"\n---\n**状态**: ✅ 已保存\n")
    
    # 更新上下文文件
    with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'current_topic': None,  # 清空当前话题
            'last_topic': memory,
            'cleared_at': timestamp
        }, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 话题 '{topic_name}' 已保存到 {md_file}")
    return memory


def load_context() -> dict:
    """加载当前上下文"""
    if CONTEXT_FILE.exists():
        with open(CONTEXT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'current_topic': None, 'last_topic': None}


def set_current_topic(topic_name: str):
    """设置当前话题"""
    context = load_context()
    context['current_topic'] = topic_name
    context['started_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
        json.dump(context, f, ensure_ascii=False, indent=2)
    
    print(f"📝 当前话题：{topic_name}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法：python3 topic_memory.py [save|load|set] [args]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'save':
        topic = sys.argv[2] if len(sys.argv) > 2 else "未命名话题"
        summary = sys.argv[3] if len(sys.argv) > 3 else "无摘要"
        points = sys.argv[4:] if len(sys.argv) > 4 else []
        save_current_topic(topic, summary, points)
    
    elif command == 'load':
        context = load_context()
        print(json.dumps(context, ensure_ascii=False, indent=2))
    
    elif command == 'set':
        topic = sys.argv[2] if len(sys.argv) > 2 else "新话题"
        set_current_topic(topic)
    
    else:
        print(f"未知命令：{command}")
