# @file: vector_index.py
# @module: openclaw.core.index.vector_index
# @purpose: "Vector index for semantic search"
# @ai_maintained: true
# @version: "1.0.0"

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np
from datetime import datetime

# @schema: VectorItem
# @ai_readable: true
@dataclass
class VectorItem:
    """@purpose: Vector index item"""
    
    # @field: id
    # @type: str
    id: str
    
    # @field: embedding
    # @type: List[float]
    embedding: List[float]
    
    # @field: metadata
    # @type: Dict[str, any]
    metadata: Dict[str, any] = field(default_factory=dict)
    
    # @field: created_at
    # @type: datetime
    created_at: datetime = field(default_factory=datetime.now)

# @class: VectorIndex
# @purpose: "Vector index for semantic search"
# @ai_testable: true
class VectorIndex:
    """
    @summary: Vector index
    
    @features:
      - Vector storage
      - Similarity search
      - Batch operations
      - Index persistence
    """
    
    # @attribute: dimension
    # @type: int
    dimension: int
    
    # @attribute: items
    # @type: Dict[str, VectorItem]
    items: Dict[str, VectorItem]
    
    # @attribute: vectors
    # @type: np.ndarray
    vectors: np.ndarray
    
    # @constructor
    def __init__(self, dimension: int = 1536):
        """@purpose: Initialize index"""
        
        self.dimension = dimension
        self.items = {}
        self.vectors = np.array([]).reshape(0, dimension)
    
    # @function: add
    # @purpose: "Add vector to index"
    # @input: id: str, embedding: List[float], metadata: Dict
    # @side_effects: ["Add vector to index"]
    # @ai_testable: true
    def add(
        self,
        id: str,
        embedding: List[float],
        metadata: Dict = None
    ) -> None:
        """@purpose: Add vector"""
        
        item = VectorItem(
            id=id,
            embedding=embedding,
            metadata=metadata or {}
        )
        
        self.items[id] = item
        
        # Add to vectors array
        vector = np.array(embedding).reshape(1, -1)
        
        if self.vectors.size == 0:
            self.vectors = vector
        else:
            self.vectors = np.vstack([self.vectors, vector])
    
    # @function: search
    # @purpose: "Semantic search by vector similarity"
    # @input: query_embedding: List[float], top_k: int
    # @output: List[Tuple[str, float]]
    # @ai_testable: true
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        @summary: Semantic search
        
        @steps:
          1. Calculate similarities
          2. Sort by similarity
          3. Return top-k results
        """
        
        if len(self.items) == 0:
            return []
        
        # @step: 1
        query_vector = np.array(query_embedding).reshape(1, -1)
        
        # Cosine similarity
        similarities = self._cosine_similarity_batch(query_vector, self.vectors)
        
        # @step: 2
        sorted_indices = np.argsort(similarities[0])[::-1]
        
        # @step: 3
        results = []
        for idx in sorted_indices[:top_k]:
            id = list(self.items.keys())[idx]
            score = float(similarities[0][idx])
            results.append((id, score))
        
        return results
    
    # @function: _cosine_similarity_batch
    # @purpose: "Calculate cosine similarity for batch"
    # @input: query: np.ndarray, vectors: np.ndarray
    # @output: np.ndarray
    # @private: true
    def _cosine_similarity_batch(
        self,
        query: np.ndarray,
        vectors: np.ndarray
    ) -> np.ndarray:
        """@purpose: Batch similarity"""
        
        # Normalize
        query_norm = query / np.linalg.norm(query, axis=1, keepdims=True)
        vectors_norm = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        
        # Dot product
        similarities = np.dot(vectors_norm, query_norm.T)
        
        return similarities.flatten()
    
    # @function: remove
    # @purpose: "Remove vector from index"
    # @input: id: str
    # @output: bool
    # @ai_testable: true
    def remove(self, id: str) -> bool:
        """@purpose: Remove vector"""
        
        if id not in self.items:
            return False
        
        # Find index
        keys = list(self.items.keys())
        idx = keys.index(id)
        
        # Remove from items
        del self.items[id]
        
        # Remove from vectors
        self.vectors = np.delete(self.vectors, idx, axis=0)
        
        return True
    
    # @function: clear
    # @purpose: "Clear all vectors"
    # @side_effects: ["Clear all vectors"]
    # @ai_testable: true
    def clear(self) -> None:
        """@purpose: Clear index"""
        
        self.items.clear()
        self.vectors = np.array([]).reshape(0, self.dimension)
    
    # @function: get_stats
    # @purpose: "Get index statistics"
    # @output: Dict[str, any]
    # @ai_testable: true
    def get_stats(self) -> Dict[str, any]:
        """@purpose: Get statistics"""
        
        return {
            "total_vectors": len(self.items),
            "dimension": self.dimension,
            "memory_usage_mb": self.vectors.nbytes / (1024 * 1024)
        }
    
    # @function: save
    # @purpose: "Save index to file"
    # @input: path: str
    # @side_effects: ["Save index to file"]
    # @ai_testable: true
    def save(self, path: str) -> None:
        """@purpose: Save index"""
        
        import pickle
        
        with open(path, 'wb') as f:
            pickle.dump({
                'dimension': self.dimension,
                'items': self.items,
                'vectors': self.vectors
            }, f)
    
    # @function: load
    # @purpose: "Load index from file"
    # @input: path: str
    # @side_effects: ["Load index from file"]
    # @ai_testable: true
    def load(self, path: str) -> None:
        """@purpose: Load index"""
        
        import pickle
        
        with open(path, 'rb') as f:
            data = pickle.load(f)
            
            self.dimension = data['dimension']
            self.items = data['items']
            self.vectors = data['vectors']

# @class: FAISSIndex
# @purpose: "FAISS-based vector index for large scale"
# @ai_testable: true
class FAISSIndex:
    """
    @summary: FAISS vector index
    
    @features:
      - Large scale indexing
      - GPU acceleration
      - Multiple index types
    """
    
    # @attribute: index
    # @type: any
    index: any
    
    # @attribute: items
    # @type: Dict[str, VectorItem]
    items: Dict[str, VectorItem]
    
    # @constructor
    def __init__(self, dimension: int = 1536, use_gpu: bool = False):
        """@purpose: Initialize FAISS index"""
        
        try:
            import faiss
            
            if use_gpu:
                res = faiss.StandardGpuResources()
                self.index = faiss.GpuIndexFlatIP(res, dimension)
            else:
                self.index = faiss.IndexFlatIP(dimension)
            
            self.items = {}
            
        except ImportError:
            raise ImportError("FAISS not installed. Install with: pip install faiss-cpu")
    
    # @function: add
    # @purpose: "Add vector to FAISS index"
    # @input: id: str, embedding: List[float], metadata: Dict
    # @side_effects: ["Add vector to index"]
    # @ai_testable: true
    def add(
        self,
        id: str,
        embedding: List[float],
        metadata: Dict = None
    ) -> None:
        """@purpose: Add vector"""
        
        item = VectorItem(id=id, embedding=embedding, metadata=metadata or {})
        self.items[id] = item
        
        vector = np.array([embedding]).astype('float32')
        self.index.add(vector)
    
    # @function: search
    # @purpose: "Search in FAISS index"
    # @input: query_embedding: List[float], top_k: int
    # @output: List[Tuple[str, float]]
    # @ai_testable: true
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """@purpose: Search index"""
        
        query_vector = np.array([query_embedding]).astype('float32')
        
        distances, indices = self.index.search(query_vector, top_k)
        
        results = []
        keys = list(self.items.keys())
        
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx < len(keys):
                id = keys[idx]
                score = float(distances[0][i])
                results.append((id, score))
        
        return results
    
    # @function: get_stats
    # @purpose: "Get FAISS index statistics"
    # @output: Dict[str, any]
    # @ai_testable: true
    def get_stats(self) -> Dict[str, any]:
        """@purpose: Get statistics"""
        
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.index.d,
            "is_gpu": hasattr(self.index, 'resource')
        }
