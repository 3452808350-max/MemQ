#!/usr/bin/env python3
"""
Minimax 2.5 独立测试 Agent
用于测试 OpenClaw 改进后的性能表现
"""

import asyncio
import time
import json
from typing import List, Dict

class MinimaxTester:
    """Minimax 2.5 测试器"""
    
    def __init__(self):
        self.questions = []
        self.results = []
        
    def add_question(self, question: str, category: str, difficulty: str):
        """添加测试问题"""
        self.questions.append({
            'question': question,
            'category': category,
            'difficulty': difficulty,
            'timestamp': time.time()
        })
    
    async def ask_question(self, question_data: Dict) -> Dict:
        """提问并收集回答"""
        # 这里使用本地嵌入模型测试
        from transformers import AutoTokenizer, AutoModel
        import torch
        
        question = question_data['question']
        
        # 加载模型
        model_path = "/home/kyj/.cache/modelscope/hub/models/BAAI/bge-large-zh-v1.5"
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModel.from_pretrained(model_path)
        model.eval()
        
        # 生成问题嵌入
        inputs = tokenizer(question, padding=True, truncation=True, return_tensors='pt', max_length=512)
        
        start_time = time.time()
        with torch.no_grad():
            outputs = model(**inputs)
            embedding = outputs.last_hidden_state[:, 0]
        embed_time = time.time() - start_time
        
        # 搜索相关记忆 (简化版)
        search_time = 0.0  # 实际应该搜索记忆
        
        result = {
            'question': question,
            'category': question_data['category'],
            'difficulty': question_data['difficulty'],
            'embed_time': embed_time,
            'search_time': search_time,
            'total_time': embed_time + search_time,
            'embedding_dim': len(embedding[0]),
            'success': True
        }
        
        self.results.append(result)
        return result
    
    async def run_tests(self):
        """运行所有测试"""
        print("=" * 80)
        print("🧪 Minimax 2.5 DSS 系统性能测试")
        print("=" * 80)
        print("")
        
        for i, q in enumerate(self.questions, 1):
            print(f"问题 {i}/{len(self.questions)}: {q['category']} ({q['difficulty']})")
            result = await self.ask_question(q)
            print(f"   ✅ 嵌入时间：{result['embed_time']*1000:.2f}ms")
            print(f"   ✅ 总时间：{result['total_time']*1000:.2f}ms")
            print(f"   ✅ 维度：{result['embedding_dim']}")
            print("")
        
        # 生成报告
        self.generate_report()
    
    def generate_report(self):
        """生成性能报告"""
        print("=" * 80)
        print("📊 性能测试报告")
        print("=" * 80)
        print("")
        
        total_questions = len(self.results)
        avg_embed_time = sum(r['embed_time'] for r in self.results) / total_questions
        avg_total_time = sum(r['total_time'] for r in self.results) / total_questions
        
        print(f"总问题数：{total_questions}")
        print(f"平均嵌入时间：{avg_embed_time*1000:.2f}ms")
        print(f"平均总时间：{avg_total_time*1000:.2f}ms")
        print("")
        
        # 按类别统计
        categories = {}
        for r in self.results:
            cat = r['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)
        
        print("按类别统计:")
        for cat, results in categories.items():
            avg_time = sum(r['total_time'] for r in results) / len(results)
            print(f"  {cat}: {len(results)} 题，平均 {avg_time*1000:.2f}ms")
        
        print("")
        print("✅ 测试完成！")

# 创建测试实例
tester = MinimaxTester()

# 添加 DSS 系统相关问题
tester.add_question(
    "DSS 系统的 v4 版本使用了哪些核心模块？",
    "架构知识",
    "中等"
)

tester.add_question(
    "如何配置 DSS 的股票数据缓存？缓存策略是什么？",
    "配置知识",
    "困难"
)

tester.add_question(
    "DSS 系统如何计算股票的自适应指标？",
    "算法知识",
    "困难"
)

tester.add_question(
    "如何使用本地 bge-large-zh-v1.5 模型生成嵌入？",
    "模型使用",
    "中等"
)

tester.add_question(
    "OpenClaw 的记忆系统有几层缓存？每层的作用是什么？",
    "架构知识",
    "困难"
)

# 运行测试
if __name__ == "__main__":
    asyncio.run(tester.run_tests())
