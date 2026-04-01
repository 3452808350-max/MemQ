#!/usr/bin/env python3
"""
AMD RX 6800 ROCm Embedding 速度测试
测试 BGE-M3 在本地 GPU 上的性能
"""

import os
import time
import torch

# 使用镜像源加速下载
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from sentence_transformers import SentenceTransformer

# ========== 配置 ==========
MODEL_NAME = 'BAAI/bge-m3'
BATCH_SIZES = [1, 8, 16, 32, 64, 128]
NUM_SAMPLES = 1000

# ========== 测试数据 ==========
test_texts = [
    "在 OpenClaw 项目中，我们讨论了 API 的实现方案",
    "明天要和 K 讨论 RAG 系统 的进度",
    "K 喜欢用 向量检索 来处理 memory-lancedb-pro 相关任务",
    "有人提到过类似的 subagent 方案但不是用于 DSS 选股系统",
    "Alex 推荐的 BM25 方案是什么",
    "哪个项目需要优化 性能优化",
    "关于 缓存策略 的最佳实践是什么",
    "吴博士 在 Kimi Remote API 中怎么使用 日志系统",
    "详细说说 Ollama 部署 中 embedding 的使用",
    "vLLM 优化 的 rerank 怎么配置",
] * (NUM_SAMPLES // 10 + 1)

test_texts = test_texts[:NUM_SAMPLES]

# ========== 测试函数 ==========

def test_device(device_name, device, model):
    """测试特定设备的速度"""
    print(f"\n{'='*60}")
    print(f"🔬 测试设备：{device_name}")
    print(f"{'='*60}\n")
    
    results = []
    
    for batch_size in BATCH_SIZES:
        batches = [test_texts[i:i+batch_size] for i in range(0, min(200, NUM_SAMPLES), batch_size)]
        
        start = time.time()
        total_encoded = 0
        
        for batch in batches:
            embeddings = model.encode(batch, batch_size=batch_size, show_progress_bar=False)
            total_encoded += len(batch)
        
        elapsed = time.time() - start
        throughput = total_encoded / elapsed
        
        results.append({
            'batch_size': batch_size,
            'total': total_encoded,
            'time': elapsed,
            'throughput': throughput,
            'ms_per_sample': (elapsed / total_encoded) * 1000
        })
        
        print(f"Batch {batch_size:3d}: {total_encoded:4d} 条 | "
              f"耗时 {elapsed:6.2f}s | "
              f"速度 {throughput:7.1f} 条/s | "
              f"{results[-1]['ms_per_sample']:.1f} ms/条")
    
    return results

def main():
    print("🚀 AMD RX 6800 ROCm Embedding 速度测试")
    print(f"模型：{MODEL_NAME}")
    print(f"总样本数：{NUM_SAMPLES}\n")
    
    all_results = {}
    
    # ========== 测试 CPU ==========
    print("\n⏳ 加载模型 (CPU)...")
    model_cpu = SentenceTransformer(MODEL_NAME, device='cpu')
    all_results['cpu'] = test_device('CPU', 'cpu', model_cpu)
    del model_cpu
    torch.cuda.empty_cache() if torch.cuda.is_available() else None
    
    # ========== 测试 ROCm GPU ==========
    if torch.cuda.is_available():
        print(f"\n✅ CUDA/ROCm 可用！设备：{torch.cuda.get_device_name(0)}")
        print(f"   显存：{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB\n")
        
        print("⏳ 加载模型 (GPU)...")
        model_gpu = SentenceTransformer(MODEL_NAME, device='cuda')
        all_results['gpu'] = test_device(f'GPU ({torch.cuda.get_device_name(0)})', 'cuda', model_gpu)
    else:
        print("\n⚠️  CUDA/ROCm 不可用，跳过 GPU 测试")
    
    # ========== 汇总对比 ==========
    print("\n" + "="*60)
    print("📊 速度对比汇总")
    print("="*60)
    
    print(f"\n{'Batch Size':<12} | {'CPU (ms/条)':<14} | {'GPU (ms/条)':<14} | {'加速比':<10}")
    print("-" * 60)
    
    for i, batch_size in enumerate(BATCH_SIZES):
        cpu_ms = all_results['cpu'][i]['ms_per_sample']
        if 'gpu' in all_results:
            gpu_ms = all_results['gpu'][i]['ms_per_sample']
            speedup = cpu_ms / gpu_ms if gpu_ms > 0 else float('inf')
            print(f"{batch_size:<12} | {cpu_ms:<14.1f} | {gpu_ms:<14.1f} | {speedup:<10.1f}x")
        else:
            print(f"{batch_size:<12} | {cpu_ms:<14.1f} | {'N/A':<14} | {'-':<10}")
    
    # ========== 预测完整测试时间 ==========
    print("\n" + "="*60)
    print("⏱️ 预测：召回率基准测试完整运行时间")
    print("="*60)
    
    scales = [
        ('baseline', 200, 200),
        ('small', 500, 500),
        ('medium', 2000, 2000),
        ('medium-large', 5000, 5000),
        ('large', 10000, 10000),
    ]
    
    # 使用最佳 batch size 的速度
    best_cpu_throughput = max(r['throughput'] for r in all_results['cpu'])
    best_gpu_throughput = max(r['throughput'] for r in all_results['gpu']) if 'gpu' in all_results else 0
    
    print(f"\n{'规模':<15} | {'记忆 + 查询':<12} | {'CPU 预计':<12} | {'GPU 预计':<12}")
    print("-" * 60)
    
    for name, mem, qry in scales:
        total = mem + qry
        cpu_time = total / best_cpu_throughput
        gpu_time = total / best_gpu_throughput if best_gpu_throughput > 0 else 0
        
        print(f"{name:<15} | {total:<12} | {cpu_time:<10.1f}s | {gpu_time:<10.1f}s" if gpu_time > 0 else f"{name:<15} | {total:<12} | {cpu_time:<10.1f}s | {'N/A':<12}")
    
    print("\n✅ 测试完成！\n")

if __name__ == "__main__":
    main()
