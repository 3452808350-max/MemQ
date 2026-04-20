#!/usr/bin/env python3
"""
MemQ 详细测试报告

测试：
1. 检索准确率（Recall@1, Recall@5）
2. 质量评分分布
3. 噪声识别准确率
4. 改进建议
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__) + '/plugins')

from memq_pro_full import MemQPro, MemoryLayer, QualityScorer
from datetime import datetime
import json

# ============================================================================
# 初始化
# ============================================================================

print("="*70)
print("MemQ 详细测试报告")
print("="*70)

memq = MemQPro(
    cache_dir="/home/kyj/.openclaw/workspace/memq/cache_test2",
    cache_ttl_days=7,
    max_cache_size=1000
)

# ============================================================================
# 1. 保存真实聊天数据
# ============================================================================

print("\n📝 保存真实聊天数据...")

real_chat_memories = [
    # 用户偏好
    ("pref_code", "K 喜欢简洁的代码风格，讨厌过度工程化。偏好 Python。", "user/preferences"),
    ("pref_learning", "K 的学习方式：系统化学习，每天 2 篇论文，注重实践验证。", "user/preferences"),
    ("pref_values", "K 的价值观：核心是自由、平等。受母亲西方教育理念影响。", "user/preferences"),
    ("pref_tech", "技术栈：Linux (Debian/Arch/RedHat), OpenWrt, VPS, HTTP/SOCKS。AI 用 Ollama, vLLM。", "resources/tech"),
    
    # 项目信息
    ("proj_dss", "DSS 选股系统 v4.0：宏观分析、技术面分析、基本面分析、风险评估。Alpha Vantage API。", "resources/projects"),
    ("proj_openclaw", "OpenClaw 配置：~/.openclaw/openclaw.json。插件在 ~/.openclaw/plugins/。", "resources/projects"),
    ("proj_kimi", "Kimi Remote API：部署在 106.53.186.90，SSH 隧道 5000 端口，token: kimi-remote-api-token-2026。", "resources/api"),
    
    # 技术知识
    ("tech_git", "Git 命令：git add . && git commit -m 'msg' && git push origin main --force", "resources/code"),
    ("tech_ssh", "SSH 隧道：ssh -L 5000:localhost:5000 user@server", "resources/code"),
    ("tech_ollama", "Ollama GPU 加速：配置 HIP_VISIBLE_DEVICES=0 和 HSA_OVERRIDE_GFX_VERSION=10.3.0", "resources/docs"),
    
    # 噪声数据（应该低分）
    ("noise_chat1", "好的，我来帮你。作为 AI 助手，我可以回答这个问题。请问有什么可以帮你的吗？", "general"),
    ("noise_chat2", "抱歉，我不知道。可能我无法回答这个问题。也许你可以问别人。", "general"),
    ("noise_chat3", "你好", "general"),
    ("noise_chat4", "嗯...让我想想...这个...那个...", "general"),
    
    # 高质量内容
    ("quality_code", "def bm25_search(query, k=20):\n    tokens = tokenize(query)\n    scores = bm25.get_scores(tokens)\n    return top_k(scores, k)", "resources/code"),
    ("quality_doc", "OpenClaw 安装步骤：1. Node.js 24+ 2. npm install -g openclaw 3. openclaw onboard --install-daemon 4. openclaw channel 配置 Telegram", "resources/docs"),
]

for mem_id, content, category in real_chat_memories:
    memory = memq.add_memory(mem_id, content, category)

print(f"   ✅ 保存了 {len(real_chat_memories)} 条记忆")

# ============================================================================
# 2. 检索准确率测试
# ============================================================================

print("\n" + "="*70)
print("2. 检索准确率测试")
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
    results = memq.search(query, top_k=5, use_quality=True)
    
    result_ids = [r['memory_id'] for r in results]
    
    if expected in result_ids[:1]:
        recall_at_1 += 1
    if expected in result_ids[:3]:
        recall_at_3 += 1
    if expected in result_ids[:5]:
        recall_at_5 += 1
    
    status = "✅" if expected in result_ids[:1] else ("⚠️" if expected in result_ids else "❌")
    print(f"   {status} 查询：{query}")
    print(f"      期望：{expected}")
    print(f"      结果：{result_ids[:3]}")

total = len(retrieval_tests)
print(f"\n📊 检索准确率:")
print(f"   Recall@1: {recall_at_1}/{total} = {recall_at_1/total*100:.1f}%")
print(f"   Recall@3: {recall_at_3}/{total} = {recall_at_3/total*100:.1f}%")
print(f"   Recall@5: {recall_at_5}/{total} = {recall_at_5/total*100:.1f}%")

# ============================================================================
# 3. 质量评分分布
# ============================================================================

print("\n" + "="*70)
print("3. 质量评分分布")
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
print(f"   最高分：{max(quality_scores):.3f}")
print(f"   最低分：{min(quality_scores):.3f}")

# 详细评分
print(f"\n📋 详细评分:")
for mem_id, memory in sorted(memq.memories.items(), key=lambda x: x[1].quality_score, reverse=True):
    score = memory.quality_score
    if score >= 0.7:
        label = "✅ 高质量"
    elif score >= 0.4:
        label = "⚠️ 中等"
    else:
        label = "❌ 低质"
    print(f"   {mem_id}: {score:.3f} {label}")

# ============================================================================
# 4. 噪声识别准确率
# ============================================================================

print("\n" + "="*70)
print("4. 噪声识别准确率")
print("="*70)

noise_tests = [
    ("noise_chat1", True, "模板化回复"),
    ("noise_chat2", True, "破坏词"),
    ("noise_chat3", True, "太短"),
    ("noise_chat4", True, "无意义"),
    ("quality_code", False, "代码"),
    ("quality_doc", False, "文档"),
    ("pref_code", False, "偏好"),
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
        
        print(f"   {status} {mem_id}: 质量分={memory.quality_score:.3f} ({reason})")
        print(f"      预期：{'噪声' if is_noise else '非噪声'}, 预测：{'噪声' if predicted_noise else '非噪声'}")

noise_accuracy = correct / len(noise_tests) * 100
print(f"\n📊 噪声识别准确率：{noise_accuracy:.1f}%")

# ============================================================================
# 5. 改进建议
# ============================================================================

print("\n" + "="*70)
print("5. 改进建议")
print("="*70)

print("\n💡 基于测试结果的建议:\n")

# 检索准确率建议
if recall_at_1 < 60:
    print("🔴 检索准确率低 (<60%)")
    print("   建议:")
    print("   1. 增加向量检索（当前只有 BM25）")
    print("   2. 调整 BM25 参数（k1, b）")
    print("   3. 增加 RRF 融合")
    print("   4. 扩展查询（同义词、拼写纠错）")
else:
    print("✅ 检索准确率良好")

# 质量评分建议
if low_quality > len(quality_scores) * 0.3:
    print("\n🔴 低质量记忆过多 (>30%)")
    print("   建议:")
    print("   1. 定期清理噪声记忆")
    print("   2. 提高保存阈值")
    print("   3. 优化质量评分权重")
else:
    print("\n✅ 质量分布合理")

# 噪声识别建议
if noise_accuracy < 80:
    print("\n🔴 噪声识别准确率低 (<80%)")
    print("   建议:")
    print("   1. 增加破坏词列表")
    print("   2. 优化模板检测")
    print("   3. 添加更多特征（困惑度、重复率）")
else:
    print("\n✅ 噪声识别准确")

print("\n📈 总体评估:")
overall_score = (recall_at_1/total*100 + noise_accuracy) / 2
if overall_score >= 80:
    print(f"   ✅ 优秀 ({overall_score:.1f}分)")
elif overall_score >= 60:
    print(f"   ⚠️ 良好 ({overall_score:.1f}分)")
else:
    print(f"   🔴 需改进 ({overall_score:.1f}分)")

# ============================================================================
# 6. 保存报告
# ============================================================================

print("\n" + "="*70)
print("6. 保存报告")
print("="*70)

report = {
    "timestamp": datetime.now().isoformat(),
    "retrieval": {
        "total_tests": total,
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

with open("/home/kyj/.openclaw/workspace/memq/test_report_detailed.json", 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n📄 报告已保存：/home/kyj/.openclaw/workspace/memq/test_report_detailed.json")

# 清理
memq.close()

print("\n" + "="*70)
print("✅ 测试完成！")
print("="*70)
