#!/usr/bin/env python3
"""
MemQ OpenClaw 插件

将 MemQ Pro 集成到 OpenClaw 记忆系统

使用示例:
```python
from openclaw_plugin import MemQOpenClawPlugin

plugin = MemQOpenClawPlugin()

# 保存记忆
plugin.save_memory("user_pref", "喜欢简洁的代码风格", category="preferences")

# 检索记忆
results = plugin.search("代码风格偏好", top_k=3)
for r in results:
    print(f"{r['memory_id']}: {r['content']}")
```
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from plugins.memq_pro import MemQPro, MemoryLayer
from datetime import datetime


class MemQOpenClawPlugin:
    """OpenClaw 记忆插件接口"""
    
    def __init__(self, data_dir: str = "/home/kyj/.openclaw/workspace/memq",
                 cache_dir: str = None,
                 cache_ttl_days: int = 7,
                 max_cache_size: int = 1000,
                 enable_concurrent: bool = True):
        self.data_dir = data_dir
        self.cache_dir = cache_dir or f"{data_dir}/cache"
        self.memq = MemQPro(
            cache_dir=self.cache_dir,
            cache_ttl_days=cache_ttl_days,
            max_cache_size=max_cache_size,
            enable_concurrent=enable_concurrent
        )
        print(f"✅ MemQ OpenClaw 插件已初始化")
        print(f"   数据目录：{data_dir}")
        print(f"   缓存目录：{self.cache_dir}")
    
    def save_memory(self, memory_id: str, content: str, category: str = "general"):
        """
        保存记忆到 MemQ
        
        Args:
            memory_id: 记忆 ID（唯一标识）
            content: 记忆内容
            category: 分类（user/preferences, agent/skills, etc.）
        """
        memory = self.memq.add_memory(memory_id, content, category)
        print(f"   ✅ 保存记忆：{memory_id} ({category})")
        return memory
    
    def search(self, query: str, top_k: int = 5, layer: str = "l1"):
        """
        检索记忆
        
        Args:
            query: 查询文本
            top_k: 返回结果数
            layer: 返回层次 (l0/l1/l2)
        
        Returns:
            检索结果列表
        """
        # 转换 layer 参数
        layer_map = {
            "l0": MemoryLayer.L0_ABSTRACT,
            "l1": MemoryLayer.L1_OVERVIEW,
            "l2": MemoryLayer.L2_DETAILS
        }
        memory_layer = layer_map.get(layer.lower(), MemoryLayer.L1_OVERVIEW)
        
        # 执行检索
        results = self.memq.search(query, top_k=top_k, layer=memory_layer)
        
        # 转换为 OpenClaw 格式
        formatted_results = []
        for r in results:
            formatted_results.append({
                'id': r['memory_id'],
                'content': r['content'],
                'score': r['relevance_score'],
                'tokens': r['token_usage'],
                'category': r['memory'].category
            })
        
        return formatted_results
    
    def get_stats(self):
        """获取统计信息"""
        stats = self.memq.get_stats()
        return {
            'total_memories': stats.get('total_memories', 0),
            'token_savings_l0': stats.get('l0_savings', '0%'),
            'token_savings_l1': stats.get('l1_savings', '0%'),
            'cache_size': stats.get('cache_size', 0)
        }
    
    def close(self):
        """关闭插件（保存缓存）"""
        if hasattr(self.memq, '_save_cache'):
            self.memq._save_cache()


# ============================================================================
# 演示
# ============================================================================

def demo():
    print("="*70)
    print("MemQ OpenClaw 插件演示")
    print("="*70)
    
    # 初始化
    plugin = MemQOpenClawPlugin()
    
    # 保存记忆
    print("\n📝 保存记忆...")
    plugin.save_memory("kimi_api", """
Kimi Remote API 部署指南

本文介绍如何部署 Kimi Remote API 到远程服务器。

## 前置条件
1. 远程服务器（推荐 Ubuntu 20.04+）
2. SSH 访问权限
3. Python 3.8+
4. Kimi API Token

## 部署步骤
1. 准备服务器环境
2. 配置 Kimi API
3. 部署服务
4. 配置 SSH 隧道

## 验证部署
curl http://localhost:5000/health
""", category="agent/skills")
    
    plugin.save_memory("dss_system", """
DSS 选股系统使用指南

DSS 是一个基于 AI 的股票预测系统。

## 功能特性
- 宏观分析
- 技术面分析
- 基本面分析
- 风险评估

## 使用方法
python3 dss_v4.py --stock 00700
""", category="agent/memories")
    
    plugin.save_memory("user_pref", """
用户偏好设置

K 喜欢简洁的代码风格，讨厌过度工程化。

## 编程偏好
- Python 优先
- 单文件功能
- 避免复杂框架
- 重视可读性
""", category="user/preferences")
    
    # 检索测试
    print("\n🔍 检索测试...")
    
    test_queries = [
        "如何部署 Kimi API？",
        "用户喜欢什么样的代码？",
        "DSS 系统怎么用？"
    ]
    
    for query in test_queries:
        print(f"\n查询：{query}")
        results = plugin.search(query, top_k=2)
        
        for i, r in enumerate(results, 1):
            print(f"  {i}. [{r['category']}] {r['id']}")
            print(f"     相关性：{r['score']:.3f}")
            print(f"     内容：{r['content'][:100]}...")
    
    # 统计信息
    print("\n📊 统计信息:")
    stats = plugin.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 清理
    plugin.close()
    
    print("\n" + "="*70)
    print("✅ 演示完成！")
    print("="*70)


if __name__ == '__main__':
    demo()
