#!/usr/bin/env python3
"""
MemQ 质量评分验证框架
包含：排序一致性检查、合成测试、端到端检索测试
"""

import json
import numpy as np
from scipy.stats import spearmanr, kendalltau
from typing import List, Dict, Tuple
import random

# ============ 1. 排序一致性检查 ============

def check_ranking_consistency(original_scores: List[float], 
                              improved_scores: List[float]) -> Dict:
    """
    检查改进版是否只是线性缩放
    """
    # Spearman 秩相关系数
    spearman_rho, spearman_p = spearmanr(original_scores, improved_scores)
    
    # Kendall Tau
    kendall_tau, kendall_p = kendalltau(original_scores, improved_scores)
    
    # Pearson 相关系数
    pearson_r = np.corrcoef(original_scores, improved_scores)[0, 1]
    
    # 判断
    if spearman_rho > 0.95:
        interpretation = "几乎完全线性相关，可能只是缩放"
    elif spearman_rho > 0.8:
        interpretation = "高度相关，但有一定排序变化"
    elif spearman_rho > 0.6:
        interpretation = "中度相关，排序有实质变化"
    else:
        interpretation = "低相关，排序发生显著变化"
    
    return {
        'spearman_rho': spearman_rho,
        'spearman_p': spearman_p,
        'kendall_tau': kendall_tau,
        'kendall_p': kendall_p,
        'pearson_r': pearson_r,
        'interpretation': interpretation
    }


# ============ 2. 合成干扰测试 ============

SYNTHETIC_TEST_CASES = [
    # 测试1: 信息密度
    {
        'id': 'density_1',
        'name': '信息密度对比 - 技术架构',
        'high': "项目架构：使用FastAPI+PostgreSQL+Redis，JWT认证，部署在K8s集群，CI/CD用GitHub Actions，监控用Prometheus+Grafana",
        'low': "项目用了一些技术和工具",
        'expected': 'high > low',
        'rationale': '高信息密度 vs 模糊描述'
    },
    {
        'id': 'density_2',
        'name': '信息密度对比 - 配置详情',
        'high': "DSS数据源配置：主用akshare东方财富接口(stock_zh_a_spot_em)，备用sina接口(stock_zh_a_spot)，故障自动切换",
        'low': "数据源配置了一下",
        'expected': 'high > low',
        'rationale': '具体配置 vs 模糊描述'
    },
    
    # 测试2: 否定模式
    {
        'id': 'negation_1',
        'name': '否定模式 - 纯否定',
        'pure_negative': "这个问题不是用Python解决的",
        'contrastive': "不用Python，改用Go，因为并发性能更好",
        'expected': 'contrastive > pure_negative',
        'rationale': '对比知识 vs 纯否定'
    },
    {
        'id': 'negation_2',
        'name': '否定模式 - 方案对比',
        'pure_negative': "但不是用于DSS项目",
        'contrastive': "方案A不是最优，但方案B在性能上提升30%",
        'expected': 'contrastive > pure_negative',
        'rationale': '有信息量的否定 vs 无信息否定'
    },
    
    # 测试3: 决策/行动性
    {
        'id': 'action_1',
        'name': '行动性对比',
        'high': "TODO: 周一检查iFinD API审批状态，获取refresh_token后配置access_token",
        'low': "iFinD API的事情到时候再说",
        'expected': 'high > low',
        'rationale': '可执行待办 vs 模糊计划'
    },
    {
        'id': 'action_2',
        'name': '完成状态',
        'high': "✅ Claude Plugin完成：6个模块全部实现，46个测试通过，代码已推送至notes仓库",
        'low': "Claude Plugin做得差不多了",
        'expected': 'high > low',
        'rationale': '明确完成状态 vs 模糊描述'
    },
    
    # 测试4: 时效性
    {
        'id': 'time_1',
        'name': '时效信息',
        'high': "2026-04-17申请iFinD API账号，预计3天审批，2026-04-20提醒检查",
        'low': "申请了iFinD API",
        'expected': 'high > low',
        'rationale': '具体时间线 vs 无时间信息'
    },
    
    # 测试5: 类别边界
    {
        'id': 'boundary_1',
        'name': '知识 vs 闲聊',
        'knowledge': "MemQ使用零样本质量评分，通过模板检测、实体密度、长度因子等指标区分噪声和知识",
        'conversation': "有人提到过类似的方案",
        'expected': 'knowledge > conversation',
        'rationale': '实质性知识 vs 模板化闲聊'
    },
    {
        'id': 'boundary_2',
        'name': '决策 vs 想法',
        'decision': "决定：使用sina备用数据源替代akshare，已实现fallback_data_source.py自动切换",
        'idea': "也许可以考虑用其他数据源",
        'expected': 'decision > idea',
        'rationale': '已执行决策 vs 模糊想法'
    }
]


def run_synthetic_tests(memq_original_scorer, memq_improved_scorer) -> Dict:
    """
    运行合成测试
    """
    results = {
        'passed': 0,
        'failed': 0,
        'details': []
    }
    
    for case in SYNTHETIC_TEST_CASES:
        detail = {
            'id': case['id'],
            'name': case['name'],
            'rationale': case['rationale']
        }
        
        # 判断测试类型
        if 'high' in case and 'low' in case:
            # 高低对比测试
            orig_high = memq_original_scorer(case['high'])
            orig_low = memq_original_scorer(case['low'])
            impr_high = memq_improved_scorer(case['high'])
            impr_low = memq_improved_scorer(case['low'])
            
            orig_pass = orig_high > orig_low
            impr_pass = impr_high > impr_low
            
            detail['original'] = {'high': orig_high, 'low': orig_low, 'pass': orig_pass}
            detail['improved'] = {'high': impr_high, 'low': impr_low, 'pass': impr_pass}
            
        elif 'pure_negative' in case and 'contrastive' in case:
            # 否定模式测试
            orig_neg = memq_original_scorer(case['pure_negative'])
            orig_con = memq_original_scorer(case['contrastive'])
            impr_neg = memq_improved_scorer(case['pure_negative'])
            impr_con = memq_improved_scorer(case['contrastive'])
            
            orig_pass = orig_con > orig_neg
            impr_pass = impr_con > impr_neg
            
            detail['original'] = {'contrastive': orig_con, 'negative': orig_neg, 'pass': orig_pass}
            detail['improved'] = {'contrastive': impr_con, 'negative': impr_neg, 'pass': impr_pass}
            
        elif 'knowledge' in case and 'conversation' in case:
            # 类别边界测试
            orig_k = memq_original_scorer(case['knowledge'])
            orig_c = memq_original_scorer(case['conversation'])
            impr_k = memq_improved_scorer(case['knowledge'])
            impr_c = memq_improved_scorer(case['conversation'])
            
            orig_pass = orig_k > orig_c
            impr_pass = impr_k > impr_c
            
            detail['original'] = {'knowledge': orig_k, 'conversation': orig_c, 'pass': orig_pass}
            detail['improved'] = {'knowledge': impr_k, 'conversation': impr_c, 'pass': impr_pass}
            
        elif 'decision' in case and 'idea' in case:
            # 决策边界测试
            orig_d = memq_original_scorer(case['decision'])
            orig_i = memq_original_scorer(case['idea'])
            impr_d = memq_improved_scorer(case['decision'])
            impr_i = memq_improved_scorer(case['idea'])
            
            orig_pass = orig_d > orig_i
            impr_pass = impr_d > impr_i
            
            detail['original'] = {'decision': orig_d, 'idea': orig_i, 'pass': orig_pass}
            detail['improved'] = {'decision': impr_d, 'idea': impr_i, 'pass': impr_pass}
        
        if impr_pass:
            results['passed'] += 1
        else:
            results['failed'] += 1
        
        results['details'].append(detail)
    
    results['accuracy'] = results['passed'] / (results['passed'] + results['failed'])
    return results


# ============ 3. 端到端检索测试框架 ============

def create_test_queries() -> List[Dict]:
    """
    基于你的聊天记录构造真实查询
    """
    return [
        {
            'query': 'iFinD API 申请进度如何',
            'time': '2026-04-20',
            'keywords': ['iFinD', '2026-04-17', '3天审批', 'refresh_token'],
            'rationale': '检查特定项目状态'
        },
        {
            'query': 'DSS 数据源问题怎么解决的',
            'time': '2026-04-16',
            'keywords': ['akshare', 'sina', 'fallback', '东方财富'],
            'rationale': '技术问题解决方案'
        },
        {
            'query': 'Claude Plugin 完成了吗',
            'time': '2026-04-20',
            'keywords': ['2026-04-02', '46测试', 'Coordinator Mode'],
            'rationale': '项目完成状态'
        },
        {
            'query': 'MemQ 质量评分怎么改进',
            'time': '2026-04-20',
            'keywords': ['信息密度', '否定模式', '实体'],
            'rationale': '当前讨论主题'
        },
        {
            'query': 'DSS v4.3 准确率多少',
            'time': '2026-04-20',
            'keywords': ['58.2%', 'MemQ', 'Recall'],
            'rationale': '系统性能指标'
        },
        {
            'query': '这周股票收益怎么样',
            'time': '2026-04-18',
            'keywords': ['+0.57%', '1149', '伯特利', '华润三九'],
            'rationale': '投资收益查询'
        },
        {
            'query': 'code-flow 项目配置好了吗',
            'time': '2026-04-16',
            'keywords': ['Redis', 'PostgreSQL', 'Docker', '145测试'],
            'rationale': '项目部署状态'
        },
        {
            'query': 'Context Manager 完成了吗',
            'time': '2026-04-20',
            'keywords': ['2026-04-02', '90测试', 'TokenBudget'],
            'rationale': '项目完成状态'
        }
    ]


def mock_vector_search(query: str, memories: List[Dict], top_k: int = 20) -> List[Dict]:
    """
    模拟向量检索（实际使用时替换为真实embedding检索）
    """
    # 基于关键词匹配模拟
    query_keywords = set(query.lower().split())
    scored_memories = []
    
    for mem in memories:
        text = mem.get('text', '').lower()
        score = 0
        for kw in query_keywords:
            if kw in text:
                score += 1
        scored_memories.append((mem, score))
    
    # 按分数排序
    scored_memories.sort(key=lambda x: x[1], reverse=True)
    return [m for m, s in scored_memories[:top_k]]


def rerank_by_quality(results: List[Dict], 
                      quality_scores: Dict[str, float],
                      alpha: float = 0.5) -> List[Dict]:
    """
    用质量分数重排序
    final_score = (1-alpha) * vector_score + alpha * quality_score
    """
    reranked = []
    for i, mem in enumerate(results):
        vector_score = 1.0 - (i / len(results))  # 模拟向量分数
        quality_score = quality_scores.get(mem.get('id'), 0.5)
        final_score = (1 - alpha) * vector_score + alpha * quality_score
        reranked.append((mem, final_score))
    
    reranked.sort(key=lambda x: x[1], reverse=True)
    return [m for m, s in reranked]


def calculate_recall_at_k(relevant_ids: set, retrieved_ids: List[str], k: int = 5) -> float:
    """
    计算 Recall@K
    """
    retrieved_k = set(retrieved_ids[:k])
    if not relevant_ids:
        return 0.0
    return len(relevant_ids & retrieved_k) / len(relevant_ids)


def calculate_ndcg_at_k(relevant_ids: set, retrieved_ids: List[str], k: int = 5) -> float:
    """
    计算 NDCG@K
    """
    dcg = 0.0
    for i, doc_id in enumerate(retrieved_ids[:k]):
        if doc_id in relevant_ids:
            dcg += 1.0 / np.log2(i + 2)  # log2(i+2) because i starts from 0
    
    # Ideal DCG
    ideal_dcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant_ids), k)))
    
    if ideal_dcg == 0:
        return 0.0
    return dcg / ideal_dcg


def run_end_to_end_test(memories: List[Dict],
                        original_scores: Dict[str, float],
                        improved_scores: Dict[str, float]) -> Dict:
    """
    运行端到端检索测试
    """
    queries = create_test_queries()
    
    results = {
        'baseline': {'recall@5': [], 'ndcg@5': []},
        'original': {'recall@5': [], 'ndcg@5': []},
        'improved': {'recall@5': [], 'ndcg@5': []}
    }
    
    for query_info in queries:
        query = query_info['query']
        keywords = query_info['keywords']
        
        # 确定相关记忆（基于关键词匹配）
        relevant_ids = set()
        for mem in memories:
            text = mem.get('text', '').lower()
            if any(kw.lower() in text for kw in keywords):
                relevant_ids.add(mem.get('id'))
        
        if not relevant_ids:
            continue
        
        # 1. Baseline: 纯向量检索
        baseline_results = mock_vector_search(query, memories, top_k=20)
        baseline_ids = [m.get('id') for m in baseline_results]
        results['baseline']['recall@5'].append(calculate_recall_at_k(relevant_ids, baseline_ids, k=5))
        results['baseline']['ndcg@5'].append(calculate_ndcg_at_k(relevant_ids, baseline_ids, k=5))
        
        # 2. MemQ原版: 向量 + 原版质量分数
        orig_reranked = rerank_by_quality(baseline_results, original_scores, alpha=0.3)
        orig_ids = [m.get('id') for m in orig_reranked]
        results['original']['recall@5'].append(calculate_recall_at_k(relevant_ids, orig_ids, k=5))
        results['original']['ndcg@5'].append(calculate_ndcg_at_k(relevant_ids, orig_ids, k=5))
        
        # 3. MemQ改进版: 向量 + 改进质量分数
        impr_reranked = rerank_by_quality(baseline_results, improved_scores, alpha=0.3)
        impr_ids = [m.get('id') for m in impr_reranked]
        results['improved']['recall@5'].append(calculate_recall_at_k(relevant_ids, impr_ids, k=5))
        results['improved']['ndcg@5'].append(calculate_ndcg_at_k(relevant_ids, impr_ids, k=5))
    
    # 计算平均值
    summary = {}
    for method in ['baseline', 'original', 'improved']:
        summary[method] = {
            'recall@5': np.mean(results[method]['recall@5']) if results[method]['recall@5'] else 0,
            'ndcg@5': np.mean(results[method]['ndcg@5']) if results[method]['ndcg@5'] else 0
        }
    
    return summary


# ============ 主函数 ============

def main():
    """
    主验证流程
    """
    print("=" * 60)
    print("MemQ 质量评分验证框架")
    print("=" * 60)
    
    # 加载数据
    print("\n[1/3] 加载数据...")
    try:
        with open('memq_comparison.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        original_scores = {item['id']: item['original_score'] for item in data}
        improved_scores = {item['id']: item['improved_score'] for item in data}
        
        print(f"  加载了 {len(data)} 条记忆的评分数据")
    except FileNotFoundError:
        print("  错误：找不到 memq_comparison.json")
        return
    
    # 1. 排序一致性检查
    print("\n[2/3] 排序一致性检查...")
    orig_list = [item['original_score'] for item in data]
    impr_list = [item['improved_score'] for item in data]
    
    consistency = check_ranking_consistency(orig_list, impr_list)
    print(f"  Spearman ρ: {consistency['spearman_rho']:.4f} (p={consistency['spearman_p']:.4e})")
    print(f"  Kendall τ: {consistency['kendall_tau']:.4f}")
    print(f"  Pearson r: {consistency['pearson_r']:.4f}")
    print(f"  结论: {consistency['interpretation']}")
    
    # 2. 合成测试（需要实现scorer函数）
    print("\n[3/3] 合成测试...")
    print("  注意：需要实现 memq_original_scorer 和 memq_improved_scorer 函数")
    print("  测试用例已定义，共 {} 个".format(len(SYNTHETIC_TEST_CASES)))
    
    print("\n" + "=" * 60)
    print("验证框架准备就绪")
    print("=" * 60)
    print("\n下一步：")
    print("1. 实现 memq_scorer.py 中的评分函数")
    print("2. 运行合成测试")
    print("3. 构造真实查询并运行端到端测试")


if __name__ == '__main__':
    main()
