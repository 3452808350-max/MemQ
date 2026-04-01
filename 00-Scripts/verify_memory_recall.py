#!/usr/bin/env python3
"""
记忆召回率验证工具
每周自动运行，验证记忆召回率是否低于阈值

使用方法:
    python3 verify_memory_recall.py [--threshold 90]
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path

# 配置
THRESHOLD = 90  # 召回率阈值（%）
TEST_QUERIES = [
    {"query": "K 的性格特点", "expected": ["专注", "好奇", "独立"]},
    {"query": "K 的价值观", "expected": ["自由", "平等"]},
    {"query": "K 的特长", "expected": ["技术", "摄影", "HiFi", "电脑硬件"]},
    {"query": "K 申请的大学", "expected": ["成均馆", "Sungkyunkwan"]},
    {"query": "K 遇到的困难", "expected": ["AI Brain Fry", "FOMO"]},
]

def run_recall_test():
    """运行召回率测试"""
    script = Path('/home/kyj/.openclaw/workspace/memory-lancedb-pro/eval/test_recall_kimi.js')
    
    if not script.exists():
        return {'error': '测试脚本不存在'}
    
    result = subprocess.run(
        ['node', str(script)],
        capture_output=True,
        text=True,
        cwd=script.parent,
        timeout=300
    )
    
    return {
        'stdout': result.stdout,
        'stderr': result.stderr,
        'returncode': result.returncode
    }

def parse_result(output):
    """解析测试结果"""
    # 简化解析，实际应该更复杂
    if '80%' in output:
        return 80
    elif '90%' in output:
        return 90
    elif '95%' in output:
        return 95
    return None

def send_alert(recall_rate):
    """发送告警"""
    alert_file = Path('/home/kyj/.openclaw/workspace/.memory_alert.json')
    alert = {
        'timestamp': datetime.now().isoformat(),
        'type': 'memory_recall_low',
        'recall_rate': recall_rate,
        'threshold': THRESHOLD,
        'message': f'记忆召回率 {recall_rate}% 低于阈值 {THRESHOLD}%',
        'action_required': '请检查记忆存储和同步机制'
    }
    
    with open(alert_file, 'w', encoding='utf-8') as f:
        json.dump(alert, f, ensure_ascii=False, indent=2)
    
    print(f"\n🚨 告警：记忆召回率 {recall_rate}% 低于阈值 {THRESHOLD}%")
    print(f"📄 告警文件：{alert_file}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='记忆召回率验证工具')
    parser.add_argument('--threshold', type=int, default=90, help='召回率阈值')
    args = parser.parse_args()
    
    global THRESHOLD
    THRESHOLD = args.threshold
    
    print("=" * 70)
    print("🧪 记忆召回率验证")
    print("=" * 70)
    print()
    
    # 运行测试
    print("📊 运行召回率测试...")
    result = run_recall_test()
    
    if 'error' in result:
        print(f"❌ 错误：{result['error']}")
        return
    
    # 解析结果
    recall_rate = parse_result(result['stdout'])
    
    if recall_rate is None:
        print("⚠️  无法解析测试结果")
        print(result['stdout'])
        return
    
    print(f"\n📊 召回率：{recall_rate}%")
    print(f"🎯 阈值：{THRESHOLD}%")
    
    # 判断是否告警
    if recall_rate < THRESHOLD:
        send_alert(recall_rate)
    else:
        print(f"\n✅ 召回率正常（{recall_rate}% >= {THRESHOLD}%）")
    
    # 保存历史记录
    history_file = Path('/home/kyj/.openclaw/workspace/.memory_recall_history.json')
    if history_file.exists():
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
    else:
        history = []
    
    history.append({
        'timestamp': datetime.now().isoformat(),
        'recall_rate': recall_rate,
        'threshold': THRESHOLD,
        'passed': recall_rate >= THRESHOLD
    })
    
    # 只保留最近 100 次
    history = history[-100:]
    
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print()
    print("=" * 70)
    print("✅ 验证完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
