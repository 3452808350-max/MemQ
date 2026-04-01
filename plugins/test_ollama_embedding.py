#!/usr/bin/env python3
"""测试 Ollama 向量化 + Reranker"""

import urllib.request
import json

def get_embedding(text: str, model: str = "modelscope.cn/Qwen/Qwen3-Embedding-0.6B-GGUF"):
    """获取文本向量"""
    req_data = {
        "model": model,
        "prompt": text,
        "stream": False
    }
    
    req = urllib.request.Request(
        "http://localhost:11434/api/embeddings",
        data=json.dumps(req_data).encode(),
        headers={"Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode())
    
    return result.get("embedding", [])

def test_embedding():
    print("="*60)
    print("Ollama 向量化测试")
    print("="*60)
    
    texts = [
        "如何部署 Kimi API？",
        "DSS 选股系统使用方法",
        "OpenClaw 记忆检索原理",
    ]
    
    print("\n获取向量...")
    for text in texts:
        embedding = get_embedding(text)
        print(f"✅ '{text[:20]}...' → {len(embedding)} 维向量")
    
    # 计算相似度（简单余弦相似度）
    import numpy as np
    
    embeddings = [get_embedding(t) for t in texts]
    vectors = np.array(embeddings)
    
    # 归一化
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    
    # 相似度矩阵
    similarity = np.dot(vectors, vectors.T)
    
    print("\n相似度矩阵:")
    for i, t1 in enumerate(texts):
        for j, t2 in enumerate(texts):
            if i <= j:
                print(f"  [{i}]vs[{j}]: {similarity[i][j]:.3f}")
    
    print("\n" + "="*60)
    print("✅ 测试完成！")
    print("="*60)

if __name__ == '__main__':
    test_embedding()
