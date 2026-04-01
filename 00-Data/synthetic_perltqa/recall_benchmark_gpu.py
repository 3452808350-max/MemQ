#!/usr/bin/env python3
"""
Synthetic PerLTQA 召回率基准测试 - 本地 GPU 加速版
AMD RX 6800 ROCm
"""

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import json
import time
import lancedb
from sentence_transformers import SentenceTransformer

# ============ 配置 ============
DB_PATH = '/home/kyj/.openclaw/workspace/lancedb'
DATA_DIR = '/home/kyj/.openclaw/workspace/synthetic_perltqa'
SCALES = ['baseline', 'small', 'medium', 'medium-large', 'large']

# ============ 加载模型 ============
print("🚀 加载模型 (CPU 优化模式)...")
model = SentenceTransformer('BAAI/bge-m3', device='cpu')
print("✅ 模型就绪\n")

# ============ 测试逻辑 ============

class RecallMetrics:
    def __init__(self):
        self.results = []
    
    def record(self, query, target_id, retrieved):
        hit = any(str(r['id']) == str(target_id) for r in retrieved[:5])
        rank = next((i+1 for i, r in enumerate(retrieved) if str(r['id']) == str(target_id)), -1)
        
        self.results.append({
            'query_id': query['id'],
            'target_id': target_id,
            'hit_at_5': hit,
            'rank': rank
        })
    
    def get_recall_at_k(self, k=5):
        hits = sum(1 for r in self.results if r['hit_at_5'])
        return hits / len(self.results) if self.results else 0
    
    def get_mrr(self):
        total = 0
        for r in self.results:
            if r['rank'] > 0:
                total += 1 / r['rank']
        return total / len(self.results) if self.results else 0
    
    def get_summary(self):
        return {
            'total_queries': len(self.results),
            'recall_at_5': f"{self.get_recall_at_k(5):.3f}",
            'recall_at_10': f"{self.get_recall_at_k(10):.3f}",
            'mrr': f"{self.get_mrr():.3f}"
        }

def run_scale_test(db, scale_name):
    print(f"\n{'='*70}")
    print(f"📊 测试规模：{scale_name}")
    print(f"{'='*70}")
    
    # 加载数据
    with open(f"{DATA_DIR}/memories_{scale_name}.json") as f:
        memories = json.load(f)
    with open(f"{DATA_DIR}/queries_{scale_name}.json") as f:
        queries = json.load(f)
    
    print(f"  📚 记忆数：{len(memories)}")
    print(f"  ❓ 查询数：{len(queries)}")
    
    # 生成 scope 名称
    scope = f"perltqa-gpu-{scale_name}-{int(time.time())}"
    
    # 删除旧表
    try:
        db.drop_table(scope)
    except:
        pass
    
    # 生成记忆 embedding
    print(f"\n  🚀 生成记忆 embedding (GPU)...")
    start = time.time()
    memory_texts = [m['content'] for m in memories]
    memory_embeddings = model.encode(memory_texts, batch_size=128, show_progress_bar=True).tolist()
    embed_time = time.time() - start
    print(f"  ✅ 记忆 embedding 完成 ({embed_time:.1f}s, {len(memories)/embed_time:.0f} 条/s)")
    
    # 创建表并插入
    table = db.create_table(scope, data=[{
        'id': memories[0]['id'],
        'text': memories[0]['content'],
        'embedding': memory_embeddings[0]
    }])
    table.delete(f"id = '{memories[0]['id']}'")
    
    # 批量插入
    batch_size = 500
    for i in range(0, len(memories), batch_size):
        batch = memories[i:i+batch_size]
        embeddings = memory_embeddings[i:i+batch_size]
        records = [{
            'id': m['id'],
            'text': m['content'],
            'embedding': emb
        } for m, emb in zip(batch, embeddings)]
        table.add(records)
    
    print(f"  ✅ 插入完成\n")
    
    # 生成查询 embedding
    print(f"  🚀 生成查询 embedding...")
    query_texts = [q['query'] for q in queries]
    query_embeddings = model.encode(query_texts, batch_size=128, show_progress_bar=False).tolist()
    print(f"  ✅ 查询 embedding 完成\n")
    
    # 运行检索
    print(f"  🔍 运行检索测试...")
    metrics = RecallMetrics()
    search_start = time.time()
    
    for i, (query, emb) in enumerate(zip(queries, query_embeddings)):
        if i % 100 == 0:
            print(f"  进度：{i+1}/{len(queries)}")
        
        retrieved = table.search(emb).limit(10).to_list()
        metrics.record(query, query['target_memory_id'], retrieved)
    
    search_time = time.time() - search_start
    print(f"  ✅ 检索完成 ({search_time:.1f}s, {len(queries)/search_time:.0f} 查询/s)")
    
    # 清理
    db.drop_table(scope)
    
    return metrics, embed_time + search_time

def main():
    print("="*70)
    print("🧪 Synthetic PerLTQA 召回率基准测试 (本地 GPU 加速)")
    print("🎮 GPU: AMD RX 6800 ROCm")
    print("📦 模型：BAAI/bge-m3")
    print("="*70)
    
    db = lancedb.connect(DB_PATH)
    
    all_results = {}
    all_timings = {}
    
    for scale in SCALES:
        start = time.time()
        metrics, proc_time = run_scale_test(db, scale)
        total_time = time.time() - start
        
        all_results[scale] = metrics.get_summary()
        all_timings[scale] = {
            'total': total_time,
            'processing': proc_time
        }
        
        summary = all_results[scale]
        print(f"\n📈 {scale} 结果:")
        print(f"   Recall@5:  {summary['recall_at_5']}")
        print(f"   Recall@10: {summary['recall_at_10']}")
        print(f"   MRR:       {summary['mrr']}")
        print(f"   ⏱️  总耗时：{total_time:.1f}s")
    
    # 保存报告
    report = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'gpu': 'AMD RX 6800 ROCm',
        'model': 'BAAI/bge-m3',
        'results': all_results,
        'timings': {k: v['total'] for k, v in all_timings.items()}
    }
    
    output_path = f"{DATA_DIR}/benchmark_result_gpu.json"
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # 汇总表格
    print("\n" + "="*70)
    print("✅ 测试完成！报告已保存:", output_path)
    print("\n📊 完整结果汇总:")
    print("="*70)
    print(f"| 规模 | 记忆数 | 查询数 | Recall@5 | Recall@10 | MRR | 耗时 |")
    print(f"|------|--------|--------|----------|-----------|-----|------|")
    
    for scale in SCALES:
        with open(f"{DATA_DIR}/stats_{scale}.json") as f:
            stats = json.load(f)
        r = all_results[scale]
        t = all_timings[scale]['total']
        print(f"| {scale:<13} | {stats['num_memories']:6d} | {stats['num_queries']:6d} | {r['recall_at_5']:>8s} | {r['recall_at_10']:>9s} | {r['mrr']:>5s} | {t:>5.1f}s |")
    
    print("="*70)
    
    # CSV 格式
    print("\n📈 绘图数据 (CSV):")
    print("scale,num_memories,recall_at_5,recall_at_10,mrr,time_seconds")
    for scale in SCALES:
        with open(f"{DATA_DIR}/stats_{scale}.json") as f:
            stats = json.load(f)
        r = all_results[scale]
        t = all_timings[scale]['total']
        print(f"{scale},{stats['num_memories']},{r['recall_at_5']},{r['recall_at_10']},{r['mrr']},{t:.1f}")

if __name__ == "__main__":
    main()
