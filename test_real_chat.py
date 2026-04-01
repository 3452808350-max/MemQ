#!/usr/bin/env python3
"""
MemQ 真实聊天数据测试

使用 subagent 调用 minimax2.5 进行对话，测试记忆系统的：
1. 自动捕获
2. 检索准确性
3. 质量评分
4. 噪声识别
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/plugins')

from memq_pro_full import MemQPro, MemoryLayer
from datetime import datetime
import json

# ============================================================================
# 初始化 MemQ
# ============================================================================

print("="*70)
print("MemQ 真实聊天数据测试")
print("="*70)

print("\n🔧 初始化 MemQ Pro...")
memq = MemQPro(
    cache_dir="/home/kyj/.openclaw/workspace/memq/cache_test",
    cache_ttl_days=7,
    max_cache_size=1000,
    enable_concurrent=True
)

print(f"✅ MemQ Pro 就绪")
print(f"   缓存：{len(memq.embeddings_cache)} 条")
print(f"   记忆：{len(memq.memories)} 条")

# ============================================================================
# 测试场景 1: 保存用户偏好
# ============================================================================

print("\n" + "="*70)
print("测试场景 1: 保存用户偏好")
print("="*70)

test_memories = [
    {
        "id": "user_pref_001",
        "content": "K 喜欢简洁的代码风格，讨厌过度工程化。偏好 Python，因为语法简洁易读。",
        "category": "user/preferences"
    },
    {
        "id": "user_pref_002",
        "content": "K 的学习方式：系统化学习，每天 2 篇论文，注重实践验证。不喜欢纯理论学习。",
        "category": "user/preferences"
    },
    {
        "id": "user_pref_003",
        "content": "K 的价值观：核心是自由、平等。受母亲西方教育理念影响。",
        "category": "user/preferences"
    },
    {
        "id": "tech_pref_001",
        "content": "技术栈偏好：Linux (Debian/Arch/RedHat), OpenWrt, VPS, HTTP/SOCKS 协议。AI 本地部署用 Ollama 和 vLLM。",
        "category": "resources/tech"
    },
    {
        "id": "project_001",
        "content": "DSS 选股系统 v4.0：包含宏观分析模块、技术面分析、基本面分析、风险评估。使用 Alpha Vantage API。",
        "category": "resources/projects"
    }
]

print("\n📝 保存测试记忆...")
for mem in test_memories:
    memory = memq.add_memory(mem['id'], mem['content'], mem['category'])
    print(f"   ✅ {mem['id']}: 质量分={memory.quality_score:.3f}")

# ============================================================================
# 测试场景 2: 检索测试
# ============================================================================

print("\n" + "="*70)
print("测试场景 2: 检索准确性")
print("="*70)

test_queries = [
    {
        "query": "K 喜欢什么样的代码？",
        "expected": "user_pref_001",
        "description": "代码风格偏好"
    },
    {
        "query": "如何学习最有效？",
        "expected": "user_pref_002",
        "description": "学习方式"
    },
    {
        "query": "K 的价值观是什么？",
        "expected": "user_pref_003",
        "description": "价值观"
    },
    {
        "query": "用什么技术栈？",
        "expected": "tech_pref_001",
        "description": "技术栈"
    },
    {
        "query": "DSS 系统有什么功能？",
        "expected": "project_001",
        "description": "项目功能"
    }
]

print("\n🔍 检索测试...")
correct = 0
for i, test in enumerate(test_queries, 1):
    results = memq.search(test['query'], top_k=3, use_quality=True)
    
    if results and results[0]['memory_id'] == test['expected']:
        correct += 1
        status = "✅"
    else:
        status = "❌"
    
    print(f"\n{i}. {test['description']}")
    print(f"   查询：{test['query']}")
    print(f"   期望：{test['expected']}")
    print(f"   结果：{results[0]['memory_id'] if results else '无结果'} {status}")
    
    if results:
        print(f"   相关性：{results[0]['relevance_score']:.3f}")
        print(f"   质量分：{results[0]['quality_score']:.3f}")

recall_at_1 = correct / len(test_queries) * 100
print(f"\n📊 Recall@1: {recall_at_1:.1f}%")

# ============================================================================
# 测试场景 3: 噪声识别
# ============================================================================

print("\n" + "="*70)
print("测试场景 3: 噪声识别")
print("="*70)

noise_memories = [
    {
        "id": "noise_001",
        "content": "好的，我来帮你。作为 AI 助手，我可以回答这个问题。请问有什么可以帮你的吗？",
        "category": "general"
    },
    {
        "id": "noise_002",
        "content": "抱歉，我不知道。可能我无法回答这个问题。也许你可以问别人。",
        "category": "general"
    },
    {
        "id": "noise_003",
        "content": "你好",
        "category": "general"
    },
    {
        "id": "quality_001",
        "content": "def hello_world():\n    print('Hello, World!')\n\n# 调用函数\nhello_world()",
        "category": "resources/code"
    },
    {
        "id": "quality_002",
        "content": "OpenClaw 配置指南：1. 安装 Node.js 24+ 2. npm install -g openclaw 3. openclaw onboard --install-daemon",
        "category": "resources/docs"
    }
]

print("\n🗑️ 测试噪声识别...")
for mem in noise_memories:
    memory = memq.add_memory(mem['id'], mem['content'], mem['category'])
    
    if memory.quality_score < 0.4:
        label = "❌ 噪声"
    elif memory.quality_score < 0.7:
        label = "⚠️ 中等"
    else:
        label = "✅ 高质量"
    
    print(f"   {mem['id']}: 质量分={memory.quality_score:.3f} {label}")

# ============================================================================
# 测试场景 4: 清理噪声
# ============================================================================

print("\n" + "="*70)
print("测试场景 4: 清理噪声")
print("="*70)

print("\n🧹 清理低质量记忆（min_quality=0.4）...")
removed = memq.cleanup_noise(min_quality=0.4)
print(f"   清理了 {removed} 条噪声记忆")

print("\n📊 清理后统计:")
stats = memq.get_stats()
print(f"   总记忆数：{stats['total_memories']}")
print(f"   高质量：{stats['high_quality_count']}")
print(f"   低质量：{stats['low_quality_count']}")
print(f"   平均质量：{stats['avg_quality']}")

# ============================================================================
# 测试场景 5: 缓存性能
# ============================================================================

print("\n" + "="*70)
print("测试场景 5: 缓存性能")
print("="*70)

import time

print("\n⏱️ 测试检索速度...")

# 首次检索（无缓存）
start = time.time()
results1 = memq.search("代码风格", top_k=5)
time1 = time.time() - start

# 第二次检索（有缓存）
start = time.time()
results2 = memq.search("代码风格", top_k=5)
time2 = time.time() - start

speedup = time1 / time2 if time2 > 0 else float('inf')

print(f"   首次检索：{time1*1000:.1f}ms")
print(f"   缓存命中：{time2*1000:.1f}ms")
print(f"   加速比：{speedup:.1f}x")

# ============================================================================
# 最终统计
# ============================================================================

print("\n" + "="*70)
print("最终统计")
print("="*70)

stats = memq.get_stats()

print(f"""
📊 记忆统计:
   总记忆数：{stats['total_memories']}
   Token 节省 (L0): {stats['l0_savings']}
   Token 节省 (L1): {stats['l1_savings']}
   
🎯 质量统计:
   平均质量：{stats['avg_quality']}
   高质量：{stats['high_quality_count']}
   低质量：{stats['low_quality_count']}
   
💾 缓存统计:
   缓存大小：{stats['cache_size']}
   查询缓存：{stats['query_cache_size']}
""")

# 保存缓存
print("\n💾 保存缓存...")
memq.close()

print("\n" + "="*70)
print("✅ 测试完成！")
print("="*70)

# 生成报告
report = {
    "timestamp": datetime.now().isoformat(),
    "recall_at_1": recall_at_1,
    "total_memories": stats['total_memories'],
    "avg_quality": float(stats['avg_quality']),
    "high_quality": stats['high_quality_count'],
    "low_quality": stats['low_quality_count'],
    "cache_size": stats['cache_size'],
    "speedup": f"{speedup:.1f}x"
}

with open("/home/kyj/.openclaw/workspace/memq/test_report.json", 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n📄 报告已保存：/home/kyj/.openclaw/workspace/memq/test_report.json")
