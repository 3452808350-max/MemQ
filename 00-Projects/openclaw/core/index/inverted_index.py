# @file: inverted_index.py
# @module: openclaw.core.index.inverted_index
# @purpose: "Inverted index for fast keyword search"
# @ai_maintained: true
# @version: "1.0.0"

from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import re

# @schema: InvertedItem
# @ai_readable: true
@dataclass
class InvertedItem:
    """@purpose: Inverted index item"""
    
    # @field: id
    # @type: str
    id: str
    
    # @field: text
    # @type: str
    text: str
    
    # @field: metadata
    # @type: Dict[str, any]
    metadata: Dict[str, any] = field(default_factory=dict)

# @class: InvertedIndex
# @purpose: "Inverted index for keyword search"
# @ai_testable: true
class InvertedIndex:
    """
    @summary: Inverted index
    
    @features:
      - Fast keyword search
      - TF-IDF scoring
      - Phrase search
    """
    
    # @attribute: index
    # @type: Dict[str, Set[str]]
    index: Dict[str, Set[str]]
    
    # @attribute: items
    # @type: Dict[str, InvertedItem]
    items: Dict[str, InvertedItem]
    
    # @attribute: idf
    # @type: Dict[str, float]
    idf: Dict[str, float]
    
    # @constructor
    def __init__(self):
        """@purpose: Initialize index"""
        
        self.index = defaultdict(set)
        self.items = {}
        self.idf = {}
    
    # @function: add
    # @purpose: "Add document to index"
    # @input: id: str, text: str, metadata: Dict
    # @side_effects: ["Add document to index"]
    # @ai_testable: true
    def add(
        self,
        id: str,
        text: str,
        metadata: Dict = None
    ) -> None:
        """@purpose: Add document"""
        
        item = InvertedItem(id=id, text=text, metadata=metadata or {})
        self.items[id] = item
        
        # Tokenize
        tokens = self._tokenize(text)
        
        # Add to index
        for token in tokens:
            self.index[token].add(id)
        
        # Update IDF
        self._update_idf()
    
    # @function: search
    # @purpose: "Keyword search"
    # @input: query: str, top_k: int
    # @output: List[Tuple[str, float]]
    # @ai_testable: true
    def search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        @summary: Keyword search
        
        @steps:
          1. Tokenize query
          2. Find matching documents
          3. Score with TF-IDF
          4. Return top-k results
        """
        
        # @step: 1
        tokens = self._tokenize(query)
        
        if not tokens:
            return []
        
        # @step: 2
        doc_scores = defaultdict(float)
        
        for token in tokens:
            if token in self.index:
                for doc_id in self.index[token]:
                    # TF-IDF scoring
                    tf = self._tf(token, self.items[doc_id].text)
                    idf = self.idf.get(token, 0)
                    
                    doc_scores[doc_id] += tf * idf
        
        # @step: 3-4
        sorted_results = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_results[:top_k]
    
    # @function: _tokenize
    # @purpose: "Tokenize text"
    # @input: text: str
    # @output: List[str]
    # @private: true
    def _tokenize(self, text: str) -> List[str]:
        """@purpose: Tokenize"""
        
        # Simple tokenization
        tokens = re.findall(r'\b\w+\b', text.lower())
        
        # Remove stopwords
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at'}
        tokens = [t for t in tokens if t not in stopwords]
        
        return tokens
    
    # @function: _tf
    # @purpose: "Calculate term frequency"
    # @input: token: str, text: str
    # @output: float
    # @private: true
    def _tf(self, token: str, text: str) -> float:
        """@purpose: Calculate TF"""
        
        tokens = self._tokenize(text)
        
        if not tokens:
            return 0.0
        
        count = tokens.count(token)
        
        return count / len(tokens)
    
    # @function: _update_idf
    # @purpose: "Update IDF scores"
    # @side_effects: ["Update IDF scores"]
    # @private: true
    def _update_idf(self) -> None:
        """@purpose: Update IDF"""
        
        import math
        
        total_docs = len(self.items)
        
        for token, doc_ids in self.index.items():
            doc_count = len(doc_ids)
            self.idf[token] = math.log(total_docs / (1 + doc_count))
    
    # @function: remove
    # @purpose: "Remove document from index"
    # @input: id: str
    # @output: bool
    # @ai_testable: true
    def remove(self, id: str) -> bool:
        """@purpose: Remove document"""
        
        if id not in self.items:
            return False
        
        # Remove from index
        text = self.items[id].text
        tokens = self._tokenize(text)
        
        for token in tokens:
            if token in self.index:
                self.index[token].discard(id)
        
        # Remove item
        del self.items[id]
        
        # Update IDF
        self._update_idf()
        
        return True
    
    # @function: clear
    # @purpose: "Clear index"
    # @side_effects: ["Clear index"]
    # @ai_testable: true
    def clear(self) -> None:
        """@purpose: Clear index"""
        
        self.index.clear()
        self.items.clear()
        self.idf.clear()
    
    # @function: get_stats
    # @purpose: "Get index statistics"
    # @output: Dict[str, any]
    # @ai_testable: true
    def get_stats(self) -> Dict[str, any]:
        """@purpose: Get statistics"""
        
        return {
            "total_documents": len(self.items),
            "unique_tokens": len(self.index),
            "avg_tokens_per_doc": sum(len(self._tokenize(item.text)) for item in self.items.values()) / max(len(self.items), 1)
        }
