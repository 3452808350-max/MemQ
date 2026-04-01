#!/usr/bin/env python3
"""
Kimi + MemQ 集成测试

测试:
1. 记忆加载（MEMORY.md）
2. 记忆检索
3. 带记忆的对话
4. 股票分析
"""
import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace')

import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("Kimi + MemQ 持久化记忆Agent测试")
print("="*60)

from kimi_memq_agent import KimiMemQAgent

agent = KimiMemQAgent()

# 测试1: 加载记忆
print("\n【测试1: 加载MEMORY.md】")
print("-"*50)
memory_content = agent.load_memory_md()
if memory_content:
    print(f"✅ 加载成功，共{len(memory_content)}字符")
    print(f"   内容预览: {memory_content[:200]}...")
else:
    print("⚠️ MEMORY.md为空")

# 测试2: 搜索记忆
print("\n【测试2: 搜索记忆】")
print("-"*50)
memories = agent.search_memories("MemQ", top_k=3)
print(f"找到 {len(memories)} 条相关记忆")
for m in memories[:2]:
    content = m.get('content', m.get('text', ''))[:100]
    print(f"  - {content}...")

# 测试3: 简单对话（带记忆上下文）
print("\n【测试3: 带记忆的对话】")
print("-"*50)

result = agent.chat("根据你的记忆，MemQ项目的Recall@1是多少？", timeout=60)

if result['success']:
    print(f"回答: {result['response'][:300]}...")
    print(f"Token使用: {result['token_usage']}")
else:
    print(f"错误: {result.get('error')}")

# 测试4: 学习新知识
print("\n【测试4: 学习新知识】")
print("-"*50)
learn_result = agent.learn("DSS v4.2集成了去噪模块和新闻情绪分析，使用Kalman滤波效果最好", category="dss_knowledge")
print(learn_result)

# 测试5: 验证记忆
print("\n【测试5: 验证新记忆】")
print("-"*50)
recall_result = agent.recall("DSS去噪", top_k=3)
print(f"找到 {len(recall_result)} 条相关记忆")
for m in recall_result:
    content = m.get('content', m.get('text', ''))[:100]
    print(f"  - {content}...")

# 测试6: DSS股票分析
print("\n【测试6: DSS股票分析】")
print("-"*50)
print("分析茅台 (sh.600519)...")

analysis = agent.analyze_stock('sh.600519')

if analysis['success']:
    print(analysis['response'][:500])
else:
    print(f"分析失败: {analysis.get('error')}")

print("\n" + "="*60)
print("✅ 测试完成!")
print("="*60)