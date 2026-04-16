"""
Search API 路由

提供全局搜索和搜索建议的 REST API 端点。
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ..models.cluster import Cluster, ClusterTree
from ..models.memory import Memory, MemorySearchResult
from ..services.cluster_manager import ClusterManager, get_cluster_manager
from ..services.memory_pool import MemoryPool, get_memory_pool

router = APIRouter(prefix="/search", tags=["search"])


class SearchResult:
    """全局搜索结果"""
    memories: list[MemorySearchResult]
    clusters: list[Cluster]
    total_count: int


@router.get("/", response_model=dict)
async def global_search(
    q: str = Query(..., min_length=1, description="搜索查询"),
    type: str = Query(default="all", description="搜索类型: all, memory, cluster"),
    k: int = Query(default=10, ge=1, le=100, description="返回数量"),
    tags: Optional[str] = Query(default=None, description="标签过滤（逗号分隔）"),
    pool: MemoryPool = Depends(get_memory_pool),
    manager: ClusterManager = Depends(get_cluster_manager)
) -> dict:
    """
    全局搜索
    
    Args:
        q: 搜索查询字符串
        type: 搜索类型 ('all', 'memory', 'cluster')
        k: 返回数量
        tags: 标签过滤
        
    Returns:
        搜索结果字典，包含 memories 和 clusters
    """
    tag_list = tags.split(",") if tags else None
    
    memories = []
    clusters = []
    
    if type in ("all", "memory"):
        memories = await pool.search(q, k, tag_list)
    
    if type in ("all", "cluster"):
        # Cluster 搜索：按名称和描述匹配
        all_clusters = await manager.list_all()
        for cluster in all_clusters:
            # 简单的字符串匹配
            if q.lower() in cluster.name.lower() or \
               (cluster.description and q.lower() in cluster.description.lower()):
                clusters.append(cluster)
            # 标签匹配
            if tag_list and any(tag in cluster.tags for tag in tag_list):
                clusters.append(cluster)
        
        # 限制数量
        clusters = clusters[:k]
    
    total_count = len(memories) + len(clusters)
    
    return {
        "memories": [m.model_dump() for m in memories],
        "clusters": [c.model_dump() for c in clusters],
        "total_count": total_count,
        "query": q,
        "type": type
    }


@router.get("/memories", response_model=list[MemorySearchResult])
async def search_memories(
    q: str = Query(..., min_length=1, description="搜索查询"),
    k: int = Query(default=10, ge=1, le=100, description="返回数量"),
    tags: Optional[str] = Query(default=None, description="标签过滤（逗号分隔）"),
    cluster_ids: Optional[str] = Query(default=None, description="Cluster ID 过滤（逗号分隔）"),
    pool: MemoryPool = Depends(get_memory_pool)
) -> list[MemorySearchResult]:
    """
    搜索 Memory
    
    Args:
        q: 搜索查询字符串
        k: 返回数量
        tags: 标签过滤
        cluster_ids: Cluster ID 过滤
        
    Returns:
        Memory 搜索结果列表
    """
    tag_list = tags.split(",") if tags else None
    cluster_id_list = [UUID(cid) for cid in cluster_ids.split(",")] if cluster_ids else None
    
    return await pool.search(q, k, tag_list, cluster_id_list)


@router.get("/clusters", response_model=list[Cluster])
async def search_clusters(
    q: str = Query(..., min_length=1, description="搜索查询"),
    k: int = Query(default=10, ge=1, le=100, description="返回数量"),
    tags: Optional[str] = Query(default=None, description="标签过滤（逗号分隔）"),
    manager: ClusterManager = Depends(get_cluster_manager)
) -> list[Cluster]:
    """
    搜索 Cluster
    
    Args:
        q: 搜索查询字符串
        k: 返回数量
        tags: 标签过滤
        
    Returns:
        Cluster 列表
    """
    all_clusters = await manager.list_all()
    tag_list = tags.split(",") if tags else None
    
    results = []
    for cluster in all_clusters:
        # 名称/描述匹配
        if q.lower() in cluster.name.lower() or \
           (cluster.description and q.lower() in cluster.description.lower()):
            results.append(cluster)
            continue
        
        # 标签匹配
        if tag_list and any(tag in cluster.tags for tag in tag_list):
            results.append(cluster)
            continue
        
        # 搜索 Cluster 内的 Memory（通过 Memory Pool）
        # 这里暂时不实现，因为这需要额外的服务依赖
    
    return results[:k]


@router.post("/suggest", response_model=list[str])
async def search_suggest(
    q: str = Query(..., min_length=1, description="搜索查询"),
    limit: int = Query(default=5, ge=1, le=20, description="建议数量"),
    pool: MemoryPool = Depends(get_memory_pool)
) -> list[str]:
    """
    搜索建议
    
    Args:
        q: 搜索查询字符串
        limit: 建议数量
        
    Returns:
        建议列表
        
    Note:
        当前为占位符实现，返回基于已有标签的建议
    """
    # 获取统计信息中的标签
    stats = await pool.get_stats()
    
    # 根据查询字符串匹配标签
    suggestions = []
    for tag, count in stats.tag_distribution.items():
        if q.lower() in tag.lower():
            suggestions.append(f"{tag} ({count} memories)")
    
    # 按数量排序
    suggestions.sort(key=lambda s: int(s.split("(")[1].split()[0]), reverse=True)
    
    return suggestions[:limit]


@router.get("/tags", response_model=dict)
async def get_tag_distribution(
    pool: MemoryPool = Depends(get_memory_pool)
) -> dict:
    """
    获取标签分布
    
    Returns:
        标签分布字典
    """
    stats = await pool.get_stats()
    return {
        "tags": stats.tag_distribution,
        "total_tags": stats.total_tags
    }