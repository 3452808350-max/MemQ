# @file: fusion.py
# @module: openclaw.core.index.fusion
# @purpose: "Fuse results from multiple indexes"
# @ai_maintained: true
# @version: "1.0.0"

from typing import List, Dict, Tuple
from dataclasses import dataclass

# @schema: SearchResult
# @ai_readable: true
@dataclass
class SearchResult:
    """@purpose: Search result"""
    
    # @field: id
    # @type: str
    id: str
    
    # @field: score
    # @type: float
    score: float
    
    # @field: source
    # @type: str
    source: str
    
    # @field: metadata
    # @type: Dict[str, any]
    metadata: Dict[str, any] = None

# @class: IndexFusion
# @purpose: "Fuse results from multiple indexes"
# @ai_testable: true
class IndexFusion:
    """
    @summary: Index fusion
    
    @features:
      - RRF (Reciprocal Rank Fusion)
      - Weighted fusion
      - Result deduplication
    """
    
    # @function: rrf_fuse
    # @purpose: "Fuse results using RRF"
    # @input: result_lists: List[List[Tuple[str, float]]], k: int
    # @output: List[SearchResult]
    # @ai_testable: true
    def rrf_fuse(
        self,
        result_lists: List[List[Tuple[str, float]]],
        k: int = 60
    ) -> List[SearchResult]:
        """
        @summary: RRF fusion
        
        @steps:
          1. Calculate RRF scores
          2. Aggregate scores
          3. Sort by aggregated score
          4. Return fused results
        """
        
        # @step: 1-2
        score_map = {}
        
        for result_list in result_lists:
            for rank, (id, score) in enumerate(result_list):
                if id not in score_map:
                    score_map[id] = 0.0
                
                # RRF formula: 1 / (k + rank)
                rrf_score = 1.0 / (k + rank)
                score_map[id] += rrf_score
        
        # @step: 3
        sorted_results = sorted(
            score_map.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # @step: 4
        return [
            SearchResult(id=id, score=score, source="rrf_fusion")
            for id, score in sorted_results
        ]
    
    # @function: weighted_fuse
    # @purpose: "Fuse results with weights"
    # @input: result_lists: List[List[Tuple[str, float]]], weights: List[float]
    # @output: List[SearchResult]
    # @ai_testable: true
    def weighted_fuse(
        self,
        result_lists: List[List[Tuple[str, float]]],
        weights: List[float] = None
    ) -> List[SearchResult]:
        """
        @summary: Weighted fusion
        
        @steps:
          1. Apply weights
          2. Aggregate scores
          3. Sort by weighted score
          4. Return fused results
        """
        
        if weights is None:
            weights = [1.0] * len(result_lists)
        
        # @step: 1-2
        score_map = {}
        
        for result_list, weight in zip(result_lists, weights):
            for id, score in result_list:
                if id not in score_map:
                    score_map[id] = 0.0
                
                score_map[id] += score * weight
        
        # @step: 3
        sorted_results = sorted(
            score_map.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # @step: 4
        return [
            SearchResult(id=id, score=score, source="weighted_fusion")
            for id, score in sorted_results
        ]
    
    # @function: deduplicate
    # @purpose: "Remove duplicate results"
    # @input: results: List[SearchResult]
    # @output: List[SearchResult]
    # @ai_testable: true
    def deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """@purpose: Deduplicate"""
        
        seen_ids = set()
        unique_results = []
        
        for result in results:
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                unique_results.append(result)
        
        return unique_results
    
    # @function: fuse_all
    # @purpose: "Complete fusion pipeline"
    # @input: result_lists: List[List[Tuple[str, float]]], method: str
    # @output: List[SearchResult]
    # @ai_testable: true
    def fuse_all(
        self,
        result_lists: List[List[Tuple[str, float]]],
        method: str = "rrf"
    ) -> List[SearchResult]:
        """
        @summary: Complete fusion
        
        @steps:
          1. Fuse results
          2. Deduplicate
          3. Return final results
        """
        
        # @step: 1
        if method == "rrf":
            fused = self.rrf_fuse(result_lists)
        elif method == "weighted":
            fused = self.weighted_fuse(result_lists)
        else:
            raise ValueError(f"Unknown fusion method: {method}")
        
        # @step: 2
        deduplicated = self.deduplicate(fused)
        
        # @step: 3
        return deduplicated
