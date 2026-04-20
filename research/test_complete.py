#!/usr/bin/env python3
"""
MemQ Pro 完整版测试

测试完整流程：BM25+ 向量→RRF→Rerank→质量分
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/plugins')

from memq_pro_complete import MemQPro, MemoryLayer
from datetime import datetime
import json
import time

print("="*70)
print("MemQ Pro 完整版测试（BM25+ 向量→RRF→Rerank→质量分）")
print("="*70)

print("\n🔧 初始化 MemQ Pro 完整版...")
memq = MemQPro(
    cache_dir="/home/kyj/.openclaw/workspace/memq/cache_complete",
    cache_ttl_days=7,
    max_cache_size=1000
)

# ============================================================================
# 1. 保存测试数据
# ============================================================================

print("\n📝 保存真实聊天数据...")

test_memories = [
    ("pref_code", "K 喜欢简洁的代码风格，讨厌过度工程化。偏好 Python。", "user/preferences"),
    ("pref_learning", "K 的学习方式：系统化学习，每天 2 篇论文，注重实践验证。", "user/preferences"),
    ("pref_values", "K 的价值观：核心是自由、平等。受母亲西方教育理念影响。", "user/preferences"),
    ("pref_tech", "技术栈：Linux (Debian/Arch/RedHat), OpenWrt, VPS, HTTP/SOCKS。AI 用 Ollama, vLLM。", "resources/tech"),
    ("proj_dss", "DSS 选股系统 v4.0：宏观分析、技术面分析、基本面分析、风险评估。Alpha Vantage API。", "resources/projects"),
    ("proj_openclaw", "OpenClaw 配置：~/.openclaw/openclaw.json。插件在 ~/.openclaw/plugins/。", "resources/projects"),
    ("proj_kimi", "Kimi Remote API：部署在 106.53.186.90，SSH 隧道 5000 端口，token: kimi-remote-api-token-2026。", "resources/api"),
    ("tech_git", "Git 命令：git add . && git commit -m 'msg' && git push origin main --force", "resources/code"),
    ("tech_ssh", "SSH 隧道：ssh -L 5000:localhost:5000 user@server", "resources/code"),
    ("tech_ollama", "Ollama GPU 加速：配置 HIP_VISIBLE_DEVICES=0 和 HSA_OVERRIDE_GFX_VERSION=10.3.0", "resources/docs"),
    ("noise_chat1", "好的，我来帮你。作为 AI 助手，我可以回答这个问题。请问有什么可以帮你的吗？", "general"),
    ("noise_chat2", "抱歉，我不知道。可能我无法回答这个问题。也许你可以问别人。", "general"),
    ("noise_chat3", "你好", "general"),
    ("quality_code", "def bm25_search(query, k=20):\n    tokens = tokenize(query)\n    scores = bm25.get_scores(tokens)\n    return top_k(scores, k)", "resources/code"),
    ("quality_doc", "OpenClaw 安装步骤：1. Node.js 24+ 2. npm install -g openclaw 3. openclaw onboard --install-daemon 4. openclaw channel 配置 Telegram", "resources/docs"),
]

for mem_id, content, category in test_memories:
    memory = memq.add_memory(mem_id, content, category)

print(f"   ✅ 保存了 {len(test_memories)} 条记忆")

# ============================================================================
# 2. 检索测试
# ============================================================================

print("\n" + "="*70)
print("2. 检索测试（混合检索+Rerank）")
print("="*70)

retrieval_tests = [
    ("喜欢什么样的代码？", "pref_code"),
    ("如何学习？", "pref_learning"),
    ("价值观是什么？", "pref_values"),
    ("用什么技术栈？", "pref_tech"),
    ("DSS 系统功能？", "proj_dss"),
    ("OpenClaw 配置在哪？", "proj_openclaw"),
    ("Kimi API 部署？", "proj_kimi"),
    ("Git 推送命令？", "tech_git"),
    ("SSH 隧道怎么配？", "tech_ssh"),
    ("Ollama GPU 配置？", "tech_ollama"),
]

print("\n🔍 检索测试...")

recall_at_1 = 0
recall_at_3 = 0
recall_at_5 = 0

for query, expected in retrieval_tests:
    start = time.time()
    results = memq.search(query, top_k=5, use_hybrid=True, use_rerank=True, use_quality=True)
    elapsed = time.time() - start
    
    result_ids = [r['memory_id'] for r in results]
    
    if expected in result_ids[:1]:
        recall_at_1 += 1
    if expected in result_ids[:3]:
        recall_at_3 += 1
    if expected in result_ids[:5]:
        recall_at_5 += 1
    
    status = "✅" if expected in result_ids[:1] else ("⚠️" if expected in result_ids else "❌")
    print(f"   {status} 查询：{query} ({elapsed*1000:.0f}ms)")
    print(f"      期望：{expected}")
    print(f"      结果：{result_ids[:3]}")

total = len(retrieval_tests)
print(f"\n📊 检索准确率:")
print(f"   Recall@1: {recall_at_1}/{total} = {recall_at_1/total*100:.1f}%")
print(f"   Recall@3: {recall_at_3}/{total} = {recall_at_3/total*100:.1f}%")
print(f"   Recall@5: {recall_at_5}/{total} = {recall_at_5/total*100:.1f}%")

# ============================================================================
# 3. 质量评分
# ============================================================================

print("\n" + "="*70)
print("3. 质量评分（优化版）")
print("="*70)

quality_scores = [m.quality_score for m in memq.memories.values()]

high_quality = sum(1 for s in quality_scores if s >= 0.7)
medium_quality = sum(1 for s in quality_scores if 0.4 <= s < 0.7)
low_quality = sum(1 for s in quality_scores if s < 0.4)

print(f"\n📊 质量分布:")
print(f"   高质量 (≥0.7): {high_quality} ({high_quality/len(quality_scores)*100:.1f}%)")
print(f"   中等 (0.4-0.7): {medium_quality} ({medium_quality/len(quality_scores)*100:.1f}%)")
print(f"   低质 (<0.4): {low_quality} ({low_quality/len(quality_scores)*100:.1f}%)")
print(f"   平均分：{sum(quality_scores)/len(quality_scores):.3f}")

print(f"\n📋 详细评分:")
for mem_id, memory in sorted(memq.memories.items(), key=lambda x: x[1].quality_score, reverse=True):
    score = memory.quality_score
    if score >= 0.7:
        label = "✅"
    elif score >= 0.4:
        label = "⚠️"
    else:
        label = "❌"
    print(f"   {label} {mem_id}: {score:.3f}")

# ============================================================================
# 4. 噪声识别
# ============================================================================

print("\n" + "="*70)
print("4. 噪声识别测试")
print("="*70)

noise_tests = [
    ("noise_chat1", True, "模板化回复"),
    ("noise_chat2", True, "破坏词"),
    ("noise_chat3", True, "太短"),
    ("quality_code", False, "代码"),
    ("quality_doc", False, "文档"),
]

correct = 0
for mem_id, is_noise, reason in noise_tests:
    if mem_id in memq.memories:
        memory = memq.memories[mem_id]
        predicted_noise = memory.quality_score < 0.4
        
        if predicted_noise == is_noise:
            correct += 1
            status = "✅"
        else:
            status = "❌"
        
        print(f"   {status} {mem_id}: {memory.quality_score:.3f} ({reason})")

noise_accuracy = correct / len(noise_tests) * 100
print(f"\n📊 噪声识别准确率：{noise_accuracy:.1f}%")

# ============================================================================
# 5. 最终统计
# ============================================================================

print("\n" + "="*70)
print("5. 最终统计")
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
""")

# 总体评分
overall_score = (recall_at_1/total*100 + noise_accuracy) / 2
print(f"\n📈 总体评分：{overall_score:.1f}分")

if overall_score >= 80:
    print(f"   ✅ 优秀")
elif overall_score >= 60:
    print(f"   ⚠️ 良好")
else:
    print(f"   🔴 需改进")

# 保存报告
report = {
    "timestamp": datetime.now().isoformat(),
    "version": "complete",
    "retrieval": {
        "recall_at_1": f"{recall_at_1/total*100:.1f}%",
        "recall_at_3": f"{recall_at_3/total*100:.1f}%",
        "recall_at_5": f"{recall_at_5/total*100:.1f}%"
    },
    "quality": {
        "high": high_quality,
        "medium": medium_quality,
        "low": low_quality,
        "avg": f"{sum(quality_scores)/len(quality_scores):.3f}"
    },
    "noise_recognition": {
        "accuracy": f"{noise_accuracy:.1f}%"
    },
    "overall_score": f"{overall_score:.1f}"
}

with open("/home/kyj/.openclaw/workspace/memq/test_report_complete.json", 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n📄 报告已保存：/home/kyj/.openclaw/workspace/memq/test_report_complete.json")

memq.close()

print("\n" + "="*70)
print("✅ 测试完成！")
print("="*70)
