#!/usr/bin/env python3
"""测试增强功能：缓存过期、并发检索、轨迹可视化"""

import sys
sys.path.insert(0, '/home/kyj/.openclaw/workspace/memq')

from plugins.memq_pro import MemQPro

print("="*70)
print("MemQ Pro 增强功能测试")
print("="*70)

# 初始化（带缓存配置）
print("\n🔧 初始化 MemQ Pro（缓存 7 天，最大 1000 条，启用并发）...")
memq = MemQPro(
    cache_dir="/home/kyj/.openclaw/workspace/memq/cache",
    cache_ttl_days=7,
    max_cache_size=1000,
    enable_concurrent=True
)

# 添加测试记忆（20 条，触发并发优化）
print("\n📝 添加测试记忆（20 条，触发并发优化）...")
for i in range(20):
    memq.add_memory(f"test_{i}", f"""
测试记忆 {i}

这是第 {i} 条测试内容，用于测试并发检索功能。

## 内容
- 主题：测试 {i % 5}
- 分类：category_{i % 3}
- 标签：tag_{i}
""", category=f"test/category_{i % 3}")

print(f"   ✅ 添加 {len(memq.memories)} 条记忆")

# 测试检索
print("\n🔍 测试检索（触发并发计算）...")
results = memq.search("测试 并发", top_k=5)
print(f"   ✅ 检索到 {len(results)} 条结果")

for i, r in enumerate(results, 1):
    print(f"   {i}. [{r['memory_id']}] 相关性：{r['relevance_score']:.3f}")

# 测试轨迹可视化
print("\n📍 检索轨迹可视化:")
print(memq.visualize_trajectory())

# 测试统计信息
print("\n📊 统计信息:")
stats = memq.get_stats()
for key, value in stats.items():
    print(f"   {key}: {value}")

# 测试导出轨迹
print("\n💾 导出检索轨迹...")
memq.export_trajectory("/home/kyj/.openclaw/workspace/memq/reports/test_trajectory.json")

# 清理（保存缓存）
print("\n💾 保存缓存...")
memq.close()

print("\n" + "="*70)
print("✅ 测试完成！")
print("="*70)
