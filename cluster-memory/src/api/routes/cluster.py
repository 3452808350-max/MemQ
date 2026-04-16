"""
Cluster API 路由

提供 Cluster 相关的 REST API 端点。
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models.cluster import (
    Cluster,
    ClusterCreate,
    ClusterMergeRequest,
    ClusterSplitRequest,
    ClusterTree,
    ClusterUpdate,
)
from ..models.memory import Memory
from ..services.cluster_manager import ClusterManager, get_cluster_manager
from ..services.memory_pool import MemoryPool, get_memory_pool

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.post("/", response_model=Cluster)
async def create_cluster(
    cluster_create: ClusterCreate,
    manager: ClusterManager = Depends(get_cluster_manager)
) -> Cluster:
    """
    创建新的 Cluster
    
    Args:
        cluster_create: 创建 Cluster 的请求数据
        
    Returns:
        创建的 Cluster 对象
    """
    return await manager.create(cluster_create)


@router.get("/{cluster_id}", response_model=Cluster)
async def get_cluster(
    cluster_id: UUID,
    manager: ClusterManager = Depends(get_cluster_manager)
) -> Cluster:
    """
    获取单个 Cluster
    
    Args:
        cluster_id: Cluster ID
        
    Returns:
        Cluster 对象
        
    Raises:
        HTTPException: Cluster 不存在时返回 404
    """
    cluster = await manager.get(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster


@router.put("/{cluster_id}", response_model=Cluster)
async def update_cluster(
    cluster_id: UUID,
    cluster_update: ClusterUpdate,
    manager: ClusterManager = Depends(get_cluster_manager)
) -> Cluster:
    """
    更新 Cluster
    
    Args:
        cluster_id: Cluster ID
        cluster_update: 更新数据
        
    Returns:
        更新后的 Cluster 对象
        
    Raises:
        HTTPException: Cluster 不存在时返回 404
    """
    cluster = await manager.update(cluster_id, cluster_update)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster


@router.delete("/{cluster_id}")
async def delete_cluster(
    cluster_id: UUID,
    manager: ClusterManager = Depends(get_cluster_manager)
) -> dict:
    """
    删除 Cluster
    
    Args:
        cluster_id: Cluster ID
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: Cluster 不存在时返回 404
    """
    success = await manager.delete(cluster_id)
    if not success:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return {"status": "deleted", "cluster_id": str(cluster_id)}


@router.get("/{cluster_id}/memories", response_model=list[Memory])
async def get_cluster_memories(
    cluster_id: UUID,
    manager: ClusterManager = Depends(get_cluster_manager),
    pool: MemoryPool = Depends(get_memory_pool)
) -> list[Memory]:
    """
    获取 Cluster 内的所有 Memory
    
    Args:
        cluster_id: Cluster ID
        
    Returns:
        Memory 列表
        
    Raises:
        HTTPException: Cluster 不存在时返回 404
    """
    cluster = await manager.get(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    memories = []
    for memory_id in cluster.memory_ids:
        memory = await pool.get(memory_id)
        if memory:
            memories.append(memory)
    
    return memories


@router.post("/{cluster_id}/memories/{memory_id}", response_model=Cluster)
async def add_memory_to_cluster(
    cluster_id: UUID,
    memory_id: UUID,
    manager: ClusterManager = Depends(get_cluster_manager)
) -> Cluster:
    """
    将 Memory 添加到 Cluster
    
    Args:
        cluster_id: Cluster ID
        memory_id: Memory ID
        
    Returns:
        更新后的 Cluster 对象
        
    Raises:
        HTTPException: Cluster 不存在时返回 404
    """
    cluster = await manager.add_memory(cluster_id, memory_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster


@router.delete("/{cluster_id}/memories/{memory_id}", response_model=Cluster)
async def remove_memory_from_cluster(
    cluster_id: UUID,
    memory_id: UUID,
    manager: ClusterManager = Depends(get_cluster_manager)
) -> Cluster:
    """
    从 Cluster 移除 Memory
    
    Args:
        cluster_id: Cluster ID
        memory_id: Memory ID
        
    Returns:
        更新后的 Cluster 对象
        
    Raises:
        HTTPException: Cluster 不存在时返回 404
    """
    cluster = await manager.remove_memory(cluster_id, memory_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return cluster


@router.get("/", response_model=list[Cluster])
async def list_clusters(
    parent_id: Optional[UUID] = Query(default=None, description="父 Cluster ID"),
    manager: ClusterManager = Depends(get_cluster_manager)
) -> list[Cluster]:
    """
    列出 Cluster
    
    Args:
        parent_id: 父 Cluster ID 过滤
        
    Returns:
        Cluster 列表
    """
    return await manager.list_all(parent_id)


@router.get("/tree", response_model=list[ClusterTree])
async def get_cluster_tree(
    root_id: Optional[UUID] = Query(default=None, description="根 Cluster ID"),
    manager: ClusterManager = Depends(get_cluster_manager)
) -> list[ClusterTree]:
    """
    获取 Cluster 树结构
    
    Args:
        root_id: 根 Cluster ID (None 表示从根 Cluster 开始)
        
    Returns:
        ClusterTree 列表
    """
    return await manager.get_tree(root_id)


@router.post("/auto", response_model=list[Cluster])
async def auto_cluster(
    manager: ClusterManager = Depends(get_cluster_manager),
    pool: MemoryPool = Depends(get_memory_pool),
    method: str = Query(default="similarity", description="聚类方法"),
    limit: int = Query(default=100, description="处理的 Memory 数量")
) -> list[Cluster]:
    """
    自动聚类
    
    Args:
        method: 聚类方法 ('similarity', 'tag', 'kmeans')
        limit: 处理的 Memory 数量
        
    Returns:
        创建的 Cluster 列表
    """
    memories = await pool.list_all(limit=limit)
    return await manager.auto_cluster(memories, method)


@router.post("/merge", response_model=Cluster)
async def merge_clusters(
    merge_request: ClusterMergeRequest,
    manager: ClusterManager = Depends(get_cluster_manager)
) -> Cluster:
    """
    合并多个 Cluster
    
    Args:
        merge_request: 合并请求
        
    Returns:
        合并后的 Cluster 对象
        
    Raises:
        HTTPException: 目标 Cluster 不存在时返回 404
    """
    cluster = await manager.merge(merge_request)
    if not cluster:
        raise HTTPException(status_code=404, detail="Target cluster not found")
    return cluster


@router.post("/split", response_model=list[Cluster])
async def split_cluster(
    split_request: ClusterSplitRequest,
    manager: ClusterManager = Depends(get_cluster_manager)
) -> list[Cluster]:
    """
    拆分 Cluster
    
    Args:
        split_request: 拆分请求
        
    Returns:
        创建的新 Cluster 列表
        
    Note:
        当前为占位符实现
    """
    # TODO: 实现真实的拆分逻辑
    cluster = await manager.get(split_request.cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    
    # 占位符：返回空列表
    return []