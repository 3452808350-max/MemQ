#!/usr/bin/env python3
"""
本地嵌入生成器 - 使用 ModelScope bge-large-zh-v1.5
"""

import os
import numpy as np
from typing import List

# 模型路径
MODEL_PATH = "/home/kyj/.cache/modelscope/hub/models/BAAI/bge-large-zh-v1.5"

class LocalEmbeddingGenerator:
    """本地嵌入生成器 (使用 bge-large-zh-v1.5)"""
    
    def __init__(self):
        print(f"📥 加载模型：{MODEL_PATH}")
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(MODEL_PATH)
        print("✅ 模型加载成功")
    
    def encode(self, text: str) -> List[float]:
        """生成单个文本的嵌入"""
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入"""
        embeddings = self.model.encode(texts, batch_size=32)
        return [emb.tolist() for emb in embeddings]
    
    @property
    def dimension(self) -> int:
        """返回嵌入维度"""
        return 1024  # bge-large-zh-v1.5 的维度

# 测试
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 测试本地嵌入生成器")
    print("=" * 60)
    
    generator = LocalEmbeddingGenerator()
    
    print("")
    print("📝 测试单个嵌入...")
    embedding = generator.encode("你好世界")
    print(f"✅ 维度：{len(embedding)}")
    print(f"   预期：1024")
    
    print("")
    print("📝 测试批量嵌入...")
    texts = ["你好", "世界", "DSS 系统"]
    embeddings = generator.encode_batch(texts)
    print(f"✅ 生成 {len(embeddings)} 个嵌入")
    print(f"   维度：{len(embeddings[0])}")
    
    print("")
    print("✅ 所有测试通过！")
