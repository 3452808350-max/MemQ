"""
MemQ 抽象知识质量评分器 v1.0
针对 knowledge 类别的概念聚合度、框架完整性、抽象价值进行检测
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class ConceptCluster:
    """概念聚类特征"""
    enumeration_count: int  # 枚举概念数量（如：数组、链表、哈希表）
    hierarchy_depth: int    # 层级深度（如：L0/L1/L2 = 3层）
    framework_signals: int  # 框架信号数量（架构/体系/方法论等）
    abstraction_score: float  # 抽象度评分（概念 vs 实现）


class AbstractKnowledgeScorer:
    """抽象知识专用评分器"""
    
    # 技术概念枚举模式（顿号、逗号分隔的技术术语）
    ENUMERATION_PATTERNS = [
        r'(?:数组|链表|哈希表|树|图|队列|栈)[、，,]',
        r'(?:BFS|DFS|DP|递归|迭代|贪心|分治)[、，,]',
        r'(?:L\d+|热|温|冷|一级|二级|三级)[、，,]',
        r'(?:输入层|隐藏层|输出层|卷积层|池化层)[、，,]',
    ]
    
    # 层级架构关键词
    HIERARCHY_KEYWORDS = [
        '分层', '层级', '架构', '模块', '组件', '系统',
        'L0', 'L1', 'L2', 'L3', '一级', '二级', '三级',
        '上层', '下层', '底层', '顶层', '中间层'
    ]
    
    # 框架/方法论信号词
    FRAMEWORK_SIGNALS = [
        '框架', '体系', '方法论', '理念', '原则', '模式',
        '核心', '关键', '本质', '精髓', '思想', '理论',
        '范式', '模型', '机制', '流程', '策略'
    ]
    
    # 抽象度指标（概念词 vs 实现词）
    CONCEPT_WORDS = [
        '抽象', '封装', '继承', '多态', '解耦', '聚合',
        '模型', '范式', '架构', '设计', '原理', '机制'
    ]
    
    IMPLEMENTATION_WORDS = [
        '代码', '实现', '编写', '调用', '运行', '部署',
        '安装', '配置', '启动', '停止', '重启', '调试'
    ]
    
    def __init__(self):
        self.category_weights = {
            'knowledge': {
                'concept_cluster': 0.30,    # ↑ 概念聚合度（核心）
                'framework_integrity': 0.25, # ↑ 框架完整性
                'abstraction_level': 0.20,   # ↑ 抽象层次
                'info_density': 0.15,        # ↓ 信息密度（降低）
                'long_term_value': 0.10,     # → 长期价值
            },
            'code': {
                'concept_cluster': 0.10,
                'framework_integrity': 0.15,
                'abstraction_level': 0.10,
                'info_density': 0.35,        # 代码更看重实体密度
                'long_term_value': 0.30,
            },
            'decision': {
                'concept_cluster': 0.15,
                'framework_integrity': 0.20,
                'abstraction_level': 0.15,
                'info_density': 0.25,
                'long_term_value': 0.25,
            },
            'conversation': {
                'concept_cluster': 0.10,
                'framework_integrity': 0.10,
                'abstraction_level': 0.10,
                'info_density': 0.40,
                'long_term_value': 0.30,
            }
        }
    
    def detect_concept_cluster(self, text: str) -> ConceptCluster:
        """检测概念聚类特征"""
        
        # 1. 枚举概念计数
        enumeration_count = 0
        for pattern in self.ENUMERATION_PATTERNS:
            matches = re.findall(pattern, text)
            enumeration_count += len(matches)
        
        # 额外检测：顿号/逗号分隔的技术术语序列
        enum_sequences = re.findall(r'(?:[\u4e00-\u9fa5a-zA-Z0-9]+[、，,]){2,}[\u4e00-\u9fa5a-zA-Z0-9]+', text)
        enumeration_count += len(enum_sequences) * 2  # 序列权重更高
        
        # 2. 层级深度检测
        hierarchy_depth = 0
        for keyword in self.HIERARCHY_KEYWORDS:
            if keyword in text:
                hierarchy_depth += 1
        
        # 检测层级模式（如：L0/L1/L2）
        level_pattern = re.findall(r'L\d+|第[一二三四五]层|一级|二级|三级', text)
        hierarchy_depth += len(set(level_pattern))  # 去重计数
        
        # 3. 框架信号检测
        framework_signals = 0
        for signal in self.FRAMEWORK_SIGNALS:
            if signal in text:
                framework_signals += text.count(signal)
        
        # 4. 抽象度计算
        concept_count = sum(1 for word in self.CONCEPT_WORDS if word in text)
        impl_count = sum(1 for word in self.IMPLEMENTATION_WORDS if word in text)
        
        total = concept_count + impl_count
        if total > 0:
            abstraction_score = concept_count / total
        else:
            abstraction_score = 0.5  # 中性默认值
        
        return ConceptCluster(
            enumeration_count=min(enumeration_count, 10),  # 封顶
            hierarchy_depth=min(hierarchy_depth, 5),       # 封顶
            framework_signals=min(framework_signals, 10),   # 封顶
            abstraction_score=abstraction_score
        )
    
    def calculate_concept_cluster_score(self, cluster: ConceptCluster) -> float:
        """计算概念聚合度得分 (0-1)"""
        enum_score = min(cluster.enumeration_count / 5, 1.0)  # 5个枚举 = 满分
        hierarchy_score = min(cluster.hierarchy_depth / 3, 1.0)  # 3层 = 满分
        framework_score = min(cluster.framework_signals / 5, 1.0)  # 5个信号 = 满分
        
        # 加权组合
        score = (enum_score * 0.4 + hierarchy_score * 0.3 + 
                framework_score * 0.3)
        
        return round(score, 3)
    
    def calculate_framework_integrity(self, text: str, cluster: ConceptCluster) -> float:
        """计算框架完整性得分 (0-1)"""
        
        scores = []
        
        # 1. 是否有明确的结构（总分、分层、分点）
        structure_indicators = [
            r'[：:].*?[；;。]',  # 冒号引导的解释
            r'[（(].*?[)）]',     # 括号内的补充
            r'[①②③④⑤⑥⑦⑧⑨⑩]',  # 编号列表
        ]
        structure_score = sum(1 for p in structure_indicators if re.search(p, text)) / len(structure_indicators)
        scores.append(structure_score)
        
        # 2. 层级信号（是否有清晰的层次关系）
        scores.append(min(cluster.hierarchy_depth / 3, 1.0))
        
        # 3. 完整性信号（是否包含定义、原理、应用）
        completeness_signals = ['是', '指', '表示', '用于', '通过', '基于', '实现']
        completeness_score = sum(1 for s in completeness_signals if s in text) / len(completeness_signals)
        scores.append(completeness_score)
        
        return round(sum(scores) / len(scores), 3)
    
    def score(self, text: str, category: str = 'knowledge') -> Dict:
        """
        计算抽象知识质量评分
        
        Returns:
            {
                'total_score': float,  # 0-5 分
                'breakdown': {
                    'concept_cluster': float,
                    'framework_integrity': float,
                    'abstraction_level': float,
                    'info_density': float,
                    'long_term_value': float,
                },
                'features': ConceptCluster,
            }
        """
        # 检测特征
        cluster = self.detect_concept_cluster(text)
        
        # 计算各维度得分
        concept_cluster_score = self.calculate_concept_cluster_score(cluster)
        framework_integrity_score = self.calculate_framework_integrity(text, cluster)
        abstraction_level_score = cluster.abstraction_score
        
        # 信息密度（简化版：实体数/长度）
        entities = len(re.findall(r'[\u4e00-\u9fa5]{2,}|[A-Z][a-z]+|[a-z]+_[a-z]+', text))
        info_density_score = min(entities / (len(text) / 10), 1.0)  # 每10字1个实体
        
        # 长期价值（基于抽象度和框架完整性）
        long_term_score = (abstraction_level_score * 0.6 + framework_integrity_score * 0.4)
        
        # 加权总分
        weights = self.category_weights.get(category, self.category_weights['knowledge'])
        
        breakdown = {
            'concept_cluster': round(concept_cluster_score * 5, 2),
            'framework_integrity': round(framework_integrity_score * 5, 2),
            'abstraction_level': round(abstraction_level_score * 5, 2),
            'info_density': round(info_density_score * 5, 2),
            'long_term_value': round(long_term_score * 5, 2),
        }
        
        total_score = sum(
            breakdown[key] * weights[key] 
            for key in weights
        )
        
        return {
            'total_score': round(total_score, 2),
            'breakdown': breakdown,
            'features': cluster,
            'weights_used': weights,
        }


def test_on_knowledge_samples():
    """在 knowledge 样本上测试"""
    
    scorer = AbstractKnowledgeScorer()
    
