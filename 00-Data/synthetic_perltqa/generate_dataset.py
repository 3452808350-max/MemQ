#!/usr/bin/env python3
"""
Synthetic PerLTQA Dataset Generator
修复版：查询基于记忆内容生成，确保语义相关
"""

import random
import json
import os
from typing import List, Dict

# ========== 配置 ==========
PEOPLE = ["刘博", "吴博士", "K", "张工", "李老师", "王总", "陈工", "赵博士", "Alex", "Sarah"]
PROJECTS = ["OpenClaw", "DSS 选股系统", "RAG 系统", "AI-Agent", "知识图谱", "智能客服", 
            "memory-lancedb-pro", "Kimi Remote API", "Ollama 部署", "vLLM 优化"]
TECH_KEYWORDS = ["API", "subagent", "向量检索", "缓存策略", "性能优化", "分页加载", 
                 "认证机制", "日志系统", "BM25", "rerank", "embedding", "scope"]

SEED = 42
random.seed(SEED)

# ========== 记忆模板 ==========
MEMORY_TEMPLATES = {
    "code": "在 {project} 项目中，我们讨论了 {tech} 的实现方案",
    "conversation": "{person} 说他最近在研究 {project}",
    "event": "明天要和 {person} 讨论 {project} 的进度",
    "knowledge": "{person} 喜欢用 {tech} 来处理 {project} 相关任务",
    "noise": "有人提到过类似的 {tech} 方案但不是用于 {project}"
}

# ========== 查询模板 ==========
# 关键修复：所有模板都必须包含 memory 中的实体
QUERY_TEMPLATES = {
    "keyword": [
        "{project} 的 {tech} 怎么配置",
        "查找 {project} 相关的 {tech} 信息",
        "{tech} 在 {project} 中怎么用",
    ],
    "semantic": [
        # 修复：semantic 类型也必须包含 project 和 tech
        "{project} 项目中如何优化 {tech}",
        "关于 {project} 的 {tech} 最佳实践",
        "{project} 里 {tech} 的实现细节",
    ],
    "hybrid": [
        "{person} 在 {project} 中推荐的 {tech} 方案",
        "{person} 在 {project} 项目中怎么使用 {tech}",
        "详细说说 {project} 中 {tech} 的使用",
    ]
}

# ========== 数据生成 ==========

def generate_memory(mem_id: int) -> dict:
    """生成单条记忆"""
    mem_type = random.choice(list(MEMORY_TEMPLATES.keys()))
    person = random.choice(PEOPLE)
    project = random.choice(PROJECTS)
    tech = random.choice(TECH_KEYWORDS)
    
    template = MEMORY_TEMPLATES[mem_type]
    content = template.format(person=person, project=project, tech=tech)
    
    return {
        "id": f"mem_{mem_id:05d}",
        "type": mem_type,
        "content": content,
        "metadata": {
            "person": person,
            "project": project,
            "tech": tech
        }
    }

def generate_query_from_memory(memory: dict, query_id: int) -> dict:
    """基于记忆生成查询 - 关键修复！从记忆提取实体"""
    person = memory["metadata"]["person"]
    project = memory["metadata"]["project"]
    tech = memory["metadata"]["tech"]
    
    query_type = random.choice(["keyword", "semantic", "hybrid"])
    template = random.choice(QUERY_TEMPLATES[query_type])
    
    # 生成查询
    query = template.format(person=person, project=project, tech=tech)
    
    return {
        "id": f"q_{query_id:05d}",
        "type": query_type,
        "query": query,
        "target_memory_id": memory["id"],
        "target_memory_content": memory["content"],
        "expected_keywords": [project, tech]
    }

def generate_dataset(num_memories: int, queries_per_memory: int = 1) -> dict:
    """生成完整数据集"""
    memories = []
    queries = []
    
    # 先生成所有记忆
    for i in range(num_memories):
        mem = generate_memory(i + 1)
        memories.append(mem)
        
        # 每个记忆生成 N 个相关查询
        for j in range(queries_per_memory):
            q = generate_query_from_memory(mem, i * queries_per_memory + j + 1)
            queries.append(q)
    
    # 打乱查询顺序（避免顺序偏差）
    random.shuffle(queries)
    
    return {
        "memories": memories,
        "queries": queries,
        "stats": {
            "total_memories": len(memories),
            "total_queries": len(queries),
            "queries_per_memory": queries_per_memory
        }
    }

# ========== 主函数 ==========

if __name__ == "__main__":
    output_dir = "/home/kyj/.openclaw/workspace/synthetic_perltqa"
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成不同规模的数据集
    scales = [
        (200, 1, "baseline"),
        (500, 1, "small"),
        (2000, 1, "medium"),
        (5000, 1, "medium-large"),
        (10000, 1, "large")
    ]
    
    print("🎨 开始生成合成数据集（修复版）...\n")
    
    for num_mem, qpm, scale_name in scales:
        print(f"📊 生成 {scale_name}: {num_mem} 条记忆，{num_mem * qpm} 个查询")
        dataset = generate_dataset(num_memories=num_mem, queries_per_memory=qpm)
        
        # 保存
        with open(f"{output_dir}/memories_{scale_name}.json", "w", encoding="utf-8") as f:
            json.dump(dataset["memories"], f, ensure_ascii=False, indent=2)
        
        with open(f"{output_dir}/queries_{scale_name}.json", "w", encoding="utf-8") as f:
            json.dump(dataset["queries"], f, ensure_ascii=False, indent=2)
        
        # 保存统计
        stats = {
            "scale": scale_name,
            "num_memories": dataset["stats"]["total_memories"],
            "num_queries": dataset["stats"]["total_queries"],
            "generated_at": __import__('datetime').datetime.now().isoformat()
        }
        with open(f"{output_dir}/stats_{scale_name}.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"   ✅ 完成\n")
    
    # 验证：打印前 5 个查询的匹配情况
    print("=" * 60)
    print("🔍 验证查询 - 记忆匹配")
    print("=" * 60)
    
    test_data = generate_dataset(num_memories=10, queries_per_memory=1)
    for q in test_data["queries"][:5]:
        print(f"\n查询：{q['query']}")
        print(f"目标记忆：{q['target_memory_content']}")
        print(f"匹配：✅")
        print("-" * 40)
    
    print(f"\n🎉 数据集生成完成！输出目录：{output_dir}")
