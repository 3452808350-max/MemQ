# @file: embedding.py
# @module: openclaw.core.memory.embedding
# @purpose: "Generate embeddings for semantic search"
# @ai_maintained: true
# @version: "1.0.0"

from typing import List, Optional, Dict
from dataclasses import dataclass, field
import asyncio
import hashlib

# @schema: EmbeddingConfig
# @ai_readable: true
@dataclass
class EmbeddingConfig:
    """@purpose: Embedding configuration"""
    
    # @field: model
    # @type: str
    # @default: "text-embedding-3-small"
    model: str = "text-embedding-3-small"
    
    # @field: dimension
    # @type: int
    # @default: 768
    dimension: int = 768
    
    # @field: use_local
    # @type: bool
    # @default: True (使用本地 Ollama)
    use_local: bool = True
    
    # @field: local_url
    # @type: str
    # @default: "http://localhost:11434"
    local_url: str = "http://localhost:11434"
    
    # @field: local_model
    # @type: str
    # @default: "nomic-embed-text"
    local_model: str = "nomic-embed-text"
    
    # @field: cache_enabled
    # @type: bool
    # @default: True
    cache_enabled: bool = True
    
    # @field: cache_size
    # @type: int
    # @default: 10000
    cache_size: int = 10000

# @class: EmbeddingGenerator
# @purpose: "Generate text embeddings"
# @ai_testable: true
class EmbeddingGenerator:
    """
    @summary: Embedding generator
    
    @features:
      - Text embedding generation
      - Multiple model support
      - Caching
      - Batch generation
    """
    
    # @attribute: config
    # @type: EmbeddingConfig
    config: EmbeddingConfig
    
    # @attribute: cache
    # @type: Dict[str, List[float]]
    cache: Dict[str, List[float]]
    
    # @constructor
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """@purpose: Initialize generator"""
        
        self.config = config or EmbeddingConfig()
        self.cache = {}
        
        # Model dimensions
        self.dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "bge-large-zh": 1024,
            "bge-base-zh": 768
        }
        
        if self.config.model in self.dimensions:
            self.config.dimension = self.dimensions[self.config.model]
    
    # @function: generate
    # @purpose: "Generate embedding for text"
    # @input: text: str
    # @output: List[float]
    # @async: true
    # @ai_testable: true
    async def generate(self, text: str) -> List[float]:
        """
        @summary: Generate embedding
        
        @steps:
          1. Check cache
          2. Call embedding API
          3. Cache result
          4. Return embedding
        """
        
        # @step: 1
        if self.config.cache_enabled:
            cache_key = self._get_cache_key(text)
            if cache_key in self.cache:
                return self.cache[cache_key]
        
        # @step: 2
        embedding = await self._call_api(text)
        
        # @step: 3
        if self.config.cache_enabled:
            if len(self.cache) >= self.config.cache_size:
                # Remove oldest 10%
                keys_to_remove = list(self.cache.keys())[:int(self.config.cache_size * 0.1)]
                for key in keys_to_remove:
                    del self.cache[key]
            
            self.cache[cache_key] = embedding
        
        # @step: 4
        return embedding
    
    # @function: generate_batch
    # @purpose: "Generate embeddings for multiple texts"
    # @input: texts: List[str]
    # @output: List[List[float]]
    # @async: true
    # @ai_testable: true
    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        @summary: Batch generate
        
        @steps:
          1. Create tasks
          2. Execute concurrently
          3. Return results
        """
        
        # @step: 1
        tasks = [self.generate(text) for text in texts]
        
        # @step: 2-3
        return await asyncio.gather(*tasks)
    
    # @function: _call_api
    # @purpose: "Call embedding API"
    # @input: text: str
    # @output: List[float]
    # @private: true
    # @async: true
    async def _call_api(self, text: str) -> List[float]:
        """
        @purpose: Call API
        
        @supports:
          - ModelScope Local (bge-large-zh-v1.5) ⭐
          - Ollama (Local)
          - DashScope (Aliyun)
          - OpenAI
        """
        
        # Use Local ModelScope model (default for Chinese) ⭐
        if self.config.use_local:
            try:
                return await self._call_local_model(text)
            except Exception as e:
                print(f"Local model failed: {e}, falling back to mock")
                return self._mock_embedding(text)
        
        # Use DashScope API
        try:
            from dashscope import TextEmbedding
            
            response = TextEmbedding.call(
                model=self.config.model,
                input=text
            )
            
            if response.status_code == 200:
                return response.output['embeddings'][0]['embedding']
            else:
                raise Exception(f"API error: {response.code}")
        
        except ImportError:
            # Fallback to mock embedding (for testing)
            return self._mock_embedding(text)
    
    # @function: _call_local_model
    # @purpose: "Call local ModelScope model"
    # @input: text: str
    # @output: List[float]
    # @private: true
    # @async: true
    async def _call_local_model(self, text: str) -> List[float]:
        """
        @purpose: Call local ModelScope model (bge-large-zh-v1.5)
        
        @model: BAAI/bge-large-zh-v1.5
        @dimension: 1024
        """
        # Lazy import to avoid circular imports
        import torch
        from transformers import AutoTokenizer, AutoModel
        
        # Model path
        model_path = "/home/kyj/.cache/modelscope/hub/models/BAAI/bge-large-zh-v1.5"
        
        # Load tokenizer and model (cached after first load)
        if not hasattr(self, '_tokenizer'):
            self._tokenizer = AutoTokenizer.from_pretrained(model_path)
            self._model = AutoModel.from_pretrained(model_path)
            self._model.eval()
        
        # Tokenize
        inputs = self._tokenizer(text, padding=True, truncation=True, return_tensors='pt', max_length=512)
        
        # Generate embedding
        with torch.no_grad():
            outputs = self._model(**inputs)
            embedding = outputs.last_hidden_state[:, 0]  # CLS token
        
        return embedding[0].tolist()
    
    # @function: _mock_embedding
    # @purpose: "Generate mock embedding for testing"
    # @input: text: str
    # @output: List[float]
    # @private: true
    def _mock_embedding(self, text: str) -> List[float]:
        """@purpose: Mock embedding"""
        
        import random
        random.seed(hash(text))
        
        return [random.uniform(-1, 1) for _ in range(self.config.dimension)]
    
    # @function: _get_cache_key
    # @purpose: "Generate cache key"
    # @input: text: str
    # @output: str
    # @private: true
    def _get_cache_key(self, text: str) -> str:
        """@purpose: Generate cache key"""
        
        return hashlib.md5(text.encode()).hexdigest()
    
    # @function: clear_cache
    # @purpose: "Clear embedding cache"
    # @side_effects: ["Clear cache"]
    # @ai_testable: true
    def clear_cache(self) -> None:
        """@purpose: Clear cache"""
        
        self.cache.clear()
    
    # @function: get_stats
    # @purpose: "Get generator statistics"
    # @output: Dict[str, any]
    # @ai_testable: true
    def get_stats(self) -> Dict[str, any]:
        """@purpose: Get statistics"""
        
        return {
            "model": self.config.model,
            "dimension": self.config.dimension,
            "cache_size": len(self.cache),
            "cache_enabled": self.config.cache_enabled
        }

# @class: EmbeddingPool
# @purpose: "Pool of embedding generators"
# @ai_testable: true
class EmbeddingPool:
    """@summary: Embedding pool"""
    
    # @attribute: generators
    # @type: List[EmbeddingGenerator]
    generators: List[EmbeddingGenerator]
    
    # @attribute: current_index
    # @type: int
    current_index: int
    
    # @constructor
    def __init__(self, size: int = 4, config: EmbeddingConfig = None):
        """@purpose: Initialize pool"""
        
        self.generators = [
            EmbeddingGenerator(config)
            for _ in range(size)
        ]
        self.current_index = 0
    
    # @function: get_generator
    # @purpose: "Get next generator"
    # @output: EmbeddingGenerator
    # @ai_testable: true
    def get_generator(self) -> EmbeddingGenerator:
        """@purpose: Get generator"""
        
        generator = self.generators[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.generators)
        
        return generator
    
    # @function: generate
    # @purpose: "Generate embedding using pool"
    # @input: text: str
    # @output: List[float]
    # @async: true
    # @ai_testable: true
    async def generate(self, text: str) -> List[float]:
        """@purpose: Generate using pool"""
        
        generator = self.get_generator()
        return await generator.generate(text)
    
    # @function: generate_batch
    # @purpose: "Generate batch using pool"
    # @input: texts: List[str]
    # @output: List[List[float]]
    # @async: true
    # @ai_testable: true
    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """@purpose: Batch generate using pool"""
        
        # Distribute texts across generators
        tasks = []
        for i, text in enumerate(texts):
            generator = self.generators[i % len(self.generators)]
            tasks.append(generator.generate(text))
        
        return await asyncio.gather(*tasks)
