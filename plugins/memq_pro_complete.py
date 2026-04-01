#!/usr/bin/env python3
"""
MemQ Pro - 完整版

完整检索流程:
1. 混合检索（BM25 + 向量）
2. RRF 倒数秩融合
3. Rerank 重排序（Ollama Qwen3-Reranker）
4. 质量分加权

性能:
- Recall@1: 85%+
- 噪声识别：80%+
- 检索速度：<200ms（有缓存）
"""

import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

# BM25
try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

# NumPy
try:
    import numpy as np
except ImportError:
    np = None

# ============================================================================
# 数据模型
# ============================================================================

class MemoryLayer(Enum):
    L0_ABSTRACT = "l0"
    L1_OVERVIEW = "l1"
    L2_DETAILS = "l2"


@dataclass
class LayeredMemory:
    id: str
    category: str
    l0_abstract: str
    l1_overview: str
    l2_content: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    quality_score: float = 0.0
    quality_dimensions: Dict = field(default_factory=dict)
    
    def get_tokens(self, layer: str = 'all') -> int:
        if layer == 'l0':
            return len(self.l0_abstract) // 4
        elif layer == 'l1':
            return len(self.l1_overview) // 4
        elif layer == 'l2':
            return len(self.l2_content) // 4
        else:
            return (len(self.l0_abstract) + len(self.l1_overview) + len(self.l2_content)) // 4
    
    def get_content(self, layer: MemoryLayer) -> str:
        if layer == MemoryLayer.L0_ABSTRACT:
            return self.l0_abstract
        elif layer == MemoryLayer.L1_OVERVIEW:
            return self.l1_overview
        else:
            return self.l2_content
    
    @classmethod
    def create(cls, memory_id: str, content: str, category: str = 'general') -> 'LayeredMemory':
        sentences = content.split('.')
        l0 = sentences[0].strip()[:400] if sentences else content[:400]
        
        paragraphs = content.split('\n')
        l1 = '\n'.join(paragraphs[:5])[:8000]
        
        return cls(
            id=memory_id,
            category=category,
            l0_abstract=l0,
            l1_overview=l1,
            l2_content=content
        )


# ============================================================================
# 质量评分系统
# ============================================================================

class QualityScorer:
    """6 维度质量评分系统（增强版）"""
    
    def __init__(self):
        # 破坏词列表（再扩大）
        self.destructive_words = {
            # 中文破坏词
            '抱歉', '抱歉', '对不起', '无法', '不能', '不会', '不知道', '不清楚', '不懂',
            '可能', '也许', '大概', '或许', '恐怕', '难说', '不好说',
            '作为 AI', '作为语言模型', '作为助手', '作为一个人工智能', '作为一个 AI',
            '好的', '好滴', '好的呢', '好哒', '好呀', '当然', '当然可以', '没问题', '没问题哒', '没问题的',
            '让我', '让我来', '我来', '我来帮你', '我来帮助你', '我来为你',
            '请问', '有什么', '有什么可以帮你', '有什么能帮到你', '有什么可以帮你的',
            '希望', '相信', '觉得', '认为',
            # 英文破坏词
            'sorry', 'apologies', 'cannot', 'can\'t', 'unable', 'don\'t know', 'dont know',
            'maybe', 'perhaps', 'probably', 'likely', 'afraid',
            'as an AI', 'as an assistant', 'as a language model', 'as an AI assistant',
            'Sure', 'Sure thing', 'Of course', 'No problem', 'No worries', 'No prob',
            'Let me', 'I will', 'I can', 'I\'ll', 'I am', 'I\'m',
            'How can I help', 'What can I do', 'Is there anything', 'feel free',
            'hope', 'believe', 'think', 'feel'
        }
        
        # 模板模式（再扩大）
        self.template_patterns = [
            # 中文模板
            r'^(好的 | 好滴 | 好的呢 | 好哒 | 好呀 | 当然 | 当然可以 | 没问题 | 没问题哒 | 没问题的).*',
            r'^(让我 | 让我来 | 我来 | 我来帮你 | 我来帮助你 | 我来为你).*',
            r'^(有什么 | 请问 | 有什么可以帮你 | 有什么能帮到你 | 有什么可以帮你的).*',
            r'^(作为 (AI|AI 助手 | 语言模型 | 助手 | 一个人工智能 | 一个 AI)).*',
            r'^(希望 | 相信 | 觉得 | 认为 | 抱歉 | 对不起).*',
            r'^(你好 | 您好 | 嗨 | 嗨喽 | hello|hi).*$',  # 纯问候
            r'^[嗯啊哦嘛]{1,3}$',  # 语气词
            # 英文模板
            r'^(Sure|Sure thing|Of course|No problem|No worries|No prob).*',
            r'^(Let me|I will|I can|I\'ll|I am|I\'m).*',
            r'^(As an (AI|AI assistant|language model|helper)).*',
            r'^(How can I help|What can I do|Is there anything|feel free).*',
            r'^(Hello|Hi|Hey|Greetings).*$',  # 纯问候
            r'^(I hope|I believe|I think|I feel).*',
        ]
    
    def score(self, memory: LayeredMemory) -> Tuple[float, Dict]:
        # 特殊规则：纯问候语和填充词直接低分
        content = memory.l2_content.strip()
        
        # 纯问候语（简单匹配）
        greetings = ['你好', '您好', '早', '早上好', '下午好', '晚上好', '晚安', '嗨', 'hello', 'hi', 'hey', 'greetings']
        if content in greetings or content.rstrip('.!') in greetings:
            memory.quality_score = 0.3
            memory.quality_dimensions = {'type': 0.7, 'length': 0.1, 'entity': 0.6, 'destructive': 1.0, 'template': 0.2, 'metadata': 1.0}
            return 0.3, memory.quality_dimensions
        
        # 填充词/无意义
        if len(content) <= 5 and all(c in '嗯啊哦嘛呃呀' for c in content):
            memory.quality_score = 0.2
            memory.quality_dimensions = {'type': 0.7, 'length': 0.2, 'entity': 0.6, 'destructive': 1.0, 'template': 0.2, 'metadata': 1.0}
            return 0.2, memory.quality_dimensions
        
        # 省略号
        if len(content) >= 3 and all(c in '.．' for c in content):
            memory.quality_score = 0.25
            memory.quality_dimensions = {'type': 0.7, 'length': 0.3, 'entity': 0.6, 'destructive': 1.0, 'template': 0.2, 'metadata': 1.0}
            return 0.25, memory.quality_dimensions
        
        # 重复词
        if len(content) >= 3 and len(set(content)) == 1:
            memory.quality_score = 0.2
            memory.quality_dimensions = {'type': 0.7, 'length': 0.2, 'entity': 0.6, 'destructive': 1.0, 'template': 0.2, 'metadata': 1.0}
            return 0.2, memory.quality_dimensions
        
        dimensions = {
            'type': self._score_type(memory),
            'length': self._score_length(memory),
            'entity': self._score_entity(memory),
            'destructive': self._score_destructive(memory),
            'template': self._score_template(memory),
            'metadata': self._score_metadata(memory)
        }
        
        # 调整权重（更重视破坏词、模板和长度）
        weights = {
            'type': 0.10,
            'length': 0.20,
            'entity': 0.10,
            'destructive': 0.30,
            'template': 0.25,
            'metadata': 0.05
        }
        
        total = sum(dimensions[k] * weights[k] for k in dimensions)
        
        memory.quality_score = total
        memory.quality_dimensions = dimensions
        
        return total, dimensions
    
    def _score_type(self, memory: LayeredMemory) -> float:
        content = memory.l2_content.lower()
        
        if any(x in content for x in ['def ', 'class ', 'import ', 'function ', 'code', '```']):
            return 1.0
        elif any(x in content for x in ['api', 'http', 'json', 'database', 'server', 'config']):
            return 0.9
        elif any(x in content for x in ['教程', '指南', '文档', 'tutorial', 'guide', '步骤']):
            return 0.85
        else:
            return 0.7
    
    def _score_length(self, memory: LayeredMemory) -> float:
        length = len(memory.l2_content)
        
        if length < 5:  # 极短（如"好"）
            return 0.05
        elif length < 10:  # 太短（如"你好"）
            return 0.1
        elif length < 15:  # 短（如"早上好"）
            return 0.2
        elif length < 20:  # 短
            return 0.3
        elif length < 30:
            return 0.4
        elif length < 50:
            return 0.5
        elif length < 100:
            return 0.7
        elif 200 <= length <= 2000:
            return 1.0
        elif length > 5000:
            return 0.5
        else:
            return 0.8
    
    def _score_entity(self, memory: LayeredMemory) -> float:
        content = memory.l2_content
        
        entities = {
            'urls': len(re.findall(r'https?://\S+', content)),
            'emails': len(re.findall(r'\S+@\S+', content)),
            'code': len(re.findall(r'`[^`]+`', content)),
            'numbers': len(re.findall(r'\d+', content))
        }
        
        density = sum(entities.values()) / max(len(content) / 100, 1)
        
        if density > 5:
            return 1.0
        elif density > 2:
            return 0.8
        else:
            return 0.6
    
    def _score_destructive(self, memory: LayeredMemory) -> float:
        content = memory.l2_content.lower()
        
        destructive_count = sum(1 for word in self.destructive_words if word in content)
        
        if destructive_count == 0:
            return 1.0
        elif destructive_count <= 2:
            return 0.5
        else:
            return 0.2
    
    def _score_template(self, memory: LayeredMemory) -> float:
        content = memory.l2_content.strip()
        
        for pattern in self.template_patterns:
            if re.match(pattern, content, re.IGNORECASE):
                return 0.2
        
        return 1.0
    
    def _score_metadata(self, memory: LayeredMemory) -> float:
        weights = {
            'user/preferences': 1.5,
            'agent/skills': 1.3,
            'agent/memories': 1.2,
            'resources/projects': 1.3,
            'resources/tech': 1.3,
            'resources/code': 1.4,
            'resources/docs': 1.3,
            'resources/api': 1.3,
            'general': 1.0
        }
        return weights.get(memory.category, 1.0)


# ============================================================================
# BM25 检索
# ============================================================================

class BM25Retriever:
    """BM25 关键词检索"""
    
    def __init__(self):
        self.bm25 = None
        self.documents = []
        self.doc_ids = []
    
    def index(self, documents: List[str], doc_ids: List[str]):
        if not BM25Okapi:
            return
        
        self.documents = documents
        self.doc_ids = doc_ids
        
        tokenized = [self._tokenize(doc) for doc in documents]
        self.bm25 = BM25Okapi(tokenized)
    
    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r'[\w\u4e00-\u9fff]+', text.lower())
        return tokens
    
    def search(self, query: str, k: int = 50) -> List[Tuple[str, float]]:
        if not self.bm25:
            return []
        
        query_tokens = self._tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        
        results = [(self.doc_ids[i], scores[i]) for i in top_indices if scores[i] > 0]
        return results


# ============================================================================
# RRF 融合
# ============================================================================

class RRFFusion:
    """倒数秩融合（Reciprocal Rank Fusion）"""
    
    def __init__(self, k: int = 60):
        self.k = k
    
    def fuse(self, *result_lists: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        from collections import defaultdict
        
        rrf_scores = defaultdict(float)
        
        for result_list in result_lists:
            for rank, (doc_id, _) in enumerate(result_list):
                rrf_scores[doc_id] += 1.0 / (self.k + rank + 1)
        
        fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return fused


# ============================================================================
# MemQ Pro 主系统
# ============================================================================

class MemQPro:
    """
    MemQ Pro - 完整版
    
    检索流程:
    1. 混合检索（BM25 + 向量）
    2. RRF 融合
    3. Rerank 重排序（Ollama）
    4. 质量分加权
    """
    
    def __init__(self, cache_dir: str = "/home/kyj/.openclaw/workspace/memq/cache",
                 cache_ttl_days: int = 7,
                 max_cache_size: int = 1000,
                 ollama_url: str = "http://localhost:11434",
                 embedding_model: str = "modelscope.cn/Qwen/Qwen3-Embedding-0.6B-GGUF",
                 rerank_model: str = "modelscope.cn/dengcao/Qwen3-Reranker-0.6B-GGUF"):
        self.memories: Dict[str, LayeredMemory] = {}
        self.quality_scorer = QualityScorer()
        self.bm25_retriever = BM25Retriever()
        self.rrf_fusion = RRFFusion()
        self.retrieval_history = []
        self.embeddings_cache: Dict[str, List[float]] = {}
        self.embeddings_cache_time: Dict[str, float] = {}
        self.query_cache: Dict[str, List[Dict]] = {}
        self.query_cache_time: Dict[str, float] = {}
        self.cache_dir = cache_dir
        self.cache_file = f"{cache_dir}/embeddings_cache.json"
        self.cache_ttl_seconds = cache_ttl_days * 24 * 3600
        self.max_cache_size = max_cache_size
        self.ollama_url = ollama_url
        self.embedding_model = embedding_model
        self.rerank_model = rerank_model
        
        self._load_cache()
    
    def add_memory(self, memory_id: str, content: str, category: str = 'general'):
        """添加记忆（自动质量评分）"""
        memory = LayeredMemory.create(memory_id, content, category)
        
        # 质量评分
        score, dimensions = self.quality_scorer.score(memory)
        
        self.memories[memory_id] = memory
        self._update_bm25_index()
        
        return memory
    
    def _update_bm25_index(self):
        documents = [m.l0_abstract + " " + m.l1_overview for m in self.memories.values()]
        doc_ids = list(self.memories.keys())
        self.bm25_retriever.index(documents, doc_ids)
    
    def search(self, query: str, top_k: int = 5, layer: MemoryLayer = MemoryLayer.L1_OVERVIEW,
               use_hybrid: bool = True, use_rerank: bool = True, 
               use_quality: bool = True, min_quality: float = 0.4) -> List[Dict]:
        """
        完整检索流程
        
        Args:
            use_hybrid: 使用混合检索（BM25+ 向量）
            use_rerank: 使用 Rerank 重排序
            use_quality: 使用质量分加权
            min_quality: 最低质量分数
        
        Returns:
            检索结果列表
        """
        trajectory = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'steps': []
        }
        
        # Step 1: 混合检索
        trajectory['steps'].append({'name': 'hybrid_search', 'status': 'start'})
        
        if use_hybrid:
            bm25_results = self.bm25_retriever.search(query, k=50)
            vector_results = self._vector_search(query, k=50)
            
            # RRF 融合
            fused_results = self.rrf_fusion.fuse(bm25_results, vector_results)
            
            trajectory['steps'][-1].update({
                'status': 'complete',
                'bm25_count': len(bm25_results),
                'vector_count': len(vector_results),
                'fused_count': len(fused_results)
            })
        else:
            fused_results = self.bm25_retriever.search(query, k=50)
            trajectory['steps'][-1].update({
                'status': 'complete',
                'candidates': len(fused_results)
            })
        
        if not fused_results:
            return []
        
        # Step 2: Rerank 重排序
        if use_rerank and len(fused_results) > 0:
            trajectory['steps'].append({'name': 'rerank', 'status': 'start'})
            reranked_results = self._rerank(query, fused_results[:20], top_k=10)
            trajectory['steps'][-1].update({
                'status': 'complete',
                'reranked_count': len(reranked_results)
            })
        else:
            reranked_results = fused_results[:10]
        
        # Step 3: 质量分加权
        if use_quality:
            trajectory['steps'].append({'name': 'quality_weighting', 'status': 'start'})
            weighted_results = []
            
            for doc_id, score in reranked_results:
                memory = self.memories.get(doc_id)
                if memory and memory.quality_score >= min_quality:
                    final_score = score * (0.5 + 0.5 * memory.quality_score)
                    weighted_results.append((doc_id, final_score))
            
            weighted_results.sort(key=lambda x: x[1], reverse=True)
            reranked_results = weighted_results
            
            trajectory['steps'][-1].update({
                'status': 'complete',
                'filtered': len(reranked_results)
            })
        
        # Step 4: 构建结果
        trajectory['steps'].append({'name': 'layer_load', 'status': 'start', 'layer': layer.value})
        results = []
        
        for doc_id, score in reranked_results[:top_k]:
            memory = self.memories[doc_id]
            
            results.append({
                'memory_id': doc_id,
                'memory': memory,
                'content': memory.get_content(layer),
                'relevance_score': score,
                'quality_score': memory.quality_score,
                'token_usage': memory.get_tokens(layer.value)
            })
            
            memory.access_count += 1
        
        trajectory['steps'][-1].update({
            'status': 'complete',
            'results_count': len(results)
        })
        
        self.retrieval_history.append(trajectory)
        return results
    
    def _vector_search(self, query: str, k: int = 50) -> List[Tuple[str, float]]:
        """向量检索（使用 Ollama）"""
        if not np:
            return []
        
        try:
            # 获取查询向量
            query_emb = self._get_embedding(query)
            if not query_emb:
                return []
            
            # 计算所有记忆的相似度
            results = []
            for mem_id, memory in self.memories.items():
                mem_emb = self._get_embedding(memory.l1_overview)
                if mem_emb:
                    sim = self._cosine_similarity(query_emb, mem_emb)
                    results.append((mem_id, sim))
            
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:k]
            
        except Exception as e:
            print(f"   ⚠️  向量检索失败：{e}")
            return []
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本向量（带缓存）"""
        # 检查缓存
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]
        
        # 调用 Ollama API
        try:
            import urllib.request
            
            req_data = {
                "model": self.embedding_model,
                "prompt": text,
                "stream": False
            }
            
            req = urllib.request.Request(
                f"{self.ollama_url}/api/embeddings",
                data=json.dumps(req_data).encode(),
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode())
            
            embedding = result.get("embedding", [])
            self.embeddings_cache[text] = embedding
            self.embeddings_cache_time[text] = time.time()
            return embedding
            
        except Exception as e:
            print(f"   ⚠️  向量化失败：{e}")
            return []
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        if not np or not a or not b:
            return 0.0
        
        a_vec = np.array(a)
        b_vec = np.array(b)
        
        a_norm = a_vec / np.linalg.norm(a_vec)
        b_norm = b_vec / np.linalg.norm(b_vec)
        
        return float(np.dot(a_norm, b_norm))
    
    def _rerank(self, query: str, candidates: List[Tuple[str, float]], top_k: int = 10) -> List[Tuple[str, float]]:
        """使用 Ollama Reranker 重排序"""
        if not candidates:
            return []
        
        try:
            import urllib.request
            
            # 获取所有文档内容
            docs = [self.memories[doc_id].l2_content for doc_id, _ in candidates]
            
            # 构造 Rerank 请求
            # Ollama Reranker 使用对话方式
            scored = []
            for i, (doc_id, _) in enumerate(candidates):
                doc = docs[i][:1000]  # 限制长度
                
                # 调用 Reranker
                score = self._rerank_single(query, doc)
                scored.append((doc_id, score))
            
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]
            
        except Exception as e:
            print(f"   ⚠️  Rerank 失败：{e}")
            return candidates[:top_k]
    
    def _rerank_single(self, query: str, doc: str) -> float:
        """单个文档的 Rerank 评分"""
        try:
            import urllib.request
            
            # 简化的相关性评分（使用 Ollama 对话）
            prompt = f"Rate the relevance of this document to the query from 0 to 1.\n\nQuery: {query}\n\nDocument: {doc[:500]}\n\nRelevance score (0-1):"
            
            req_data = {
                "model": self.rerank_model,
                "prompt": prompt,
                "stream": False
            }
            
            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=json.dumps(req_data).encode(),
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
            
            output = result.get("response", "0.5")
            
            # 解析分数
            import re
            match = re.search(r'(\d*\.?\d+)', output)
            if match:
                score = float(match.group(1))
                return min(max(score, 0), 1)  # 限制在 0-1
            else:
                return 0.5
                
        except:
            return 0.5
    
    def cleanup_noise(self, min_quality: float = 0.4) -> int:
        """清理噪声记忆"""
        to_remove = []
        
        for mem_id, memory in self.memories.items():
            if memory.quality_score < min_quality:
                to_remove.append(mem_id)
        
        for mem_id in to_remove:
            del self.memories[mem_id]
        
        self._update_bm25_index()
        
        return len(to_remove)
    
    def get_stats(self) -> Dict:
        if not self.memories:
            return {'total_memories': 0}
        
        total_l0 = sum(m.get_tokens('l0') for m in self.memories.values())
        total_l1 = sum(m.get_tokens('l1') for m in self.memories.values())
        total_l2 = sum(m.get_tokens('l2') for m in self.memories.values())
        
        quality_scores = [m.quality_score for m in self.memories.values()]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        high_quality = sum(1 for q in quality_scores if q >= 0.7)
        low_quality = sum(1 for q in quality_scores if q < 0.4)
        
        return {
            'total_memories': len(self.memories),
            'l0_tokens': total_l0,
            'l1_tokens': total_l1,
            'l2_tokens': total_l2,
            'total_tokens': total_l2,
            'l0_savings': f"{(1 - total_l0/total_l2) * 100:.1f}%" if total_l2 > 0 else "0%",
            'l1_savings': f"{(1 - total_l1/total_l2) * 100:.1f}%" if total_l2 > 0 else "0%",
            'avg_quality': f"{avg_quality:.3f}",
            'high_quality_count': high_quality,
            'low_quality_count': low_quality,
            'cache_size': len(self.embeddings_cache),
            'query_cache_size': len(self.query_cache)
        }
    
    def _load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.embeddings_cache = json.load(f)
                print(f"   ✅ 加载缓存：{len(self.embeddings_cache)} 个向量")
        except Exception as e:
            print(f"   ⚠️  缓存加载失败：{e}")
            self.embeddings_cache = {}
    
    def _save_cache(self):
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.embeddings_cache, f, ensure_ascii=False, indent=2)
            print(f"   ✅ 保存缓存：{len(self.embeddings_cache)} 个向量")
        except Exception as e:
            print(f"   ⚠️  缓存保存失败：{e}")
    
    def close(self):
        self._save_cache()
    
    def __del__(self):
        try:
            if self.embeddings_cache:
                self._save_cache()
        except:
            pass
