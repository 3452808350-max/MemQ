"""
Memory API 路由

提供 Memory 相关的 REST API 端点。
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models.memory import (
    Memory,
    MemoryCreate,
    MemoryPoolStats,
    MemorySearchResult,
    MemoryUpdate,
)
from ..services.memory_pool import MemoryPool, get_memory_pool

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("/", response_model=Memory)
async def create_memory(
    memory_create: MemoryCreate,
    pool: MemoryPool = Depends(get_memory_pool)
) -> Memory:
    """
    创建新的 Memory
    
    Args:
        memory_create: 创建 Memory 的请求数据
        
    Returns:
        创建的 Memory 对象
    """
    return await pool.add(memory_create)


@router.post("/batch", response_model=list[Memory])
async def create_memories_batch(
    memories_create: list[MemoryCreate],
    pool: MemoryPool = Depends(get_memory_pool)
) -> list[Memory]:
    """
    批量创建 Memory
    
    Args:
        memories_create: 创建 Memory 的请求数据列表
        
    Returns:
        创建的 Memory 对象列表
    """
    memories = []
    for memory_create in memories_create:
        memory = await pool.add(memory_create)
        memories.append(memory)
    return memories


@router.get("/{memory_id}", response_model=Memory)
async def get_memory(
    memory_id: UUID,
    pool: MemoryPool = Depends(get_memory_pool)
) -> Memory:
    """
    获取单个 Memory
    
    Args:
        memory_id: Memory ID
        
    Returns:
        Memory 对象
        
    Raises:
        HTTPException: Memory 不存在时返回 404
    """
    memory = await pool.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.put("/{memory_id}", response_model=Memory)
async def update_memory(
    memory_id: UUID,
    memory_update: MemoryUpdate,
    pool: MemoryPool = Depends(get_memory_pool)
) -> Memory:
    """
    更新 Memory
    
    Args:
        memory_id: Memory ID
        memory_update: 更新数据
        
    Returns:
        更新后的 Memory 对象
        
    Raises:
        HTTPException: Memory 不存在时返回 404
    """
    memory = await pool.update(memory_id, memory_update)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: UUID,
    pool: MemoryPool = Depends(get_memory_pool)
) -> dict:
    """
    删除 Memory
    
    Args:
        memory_id: Memory ID
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: Memory 不存在时返回 404
    """
    success = await pool.delete(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "deleted", "memory_id": str(memory_id)}


@router.get("/search", response_model=list[MemorySearchResult])
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
        tags: 标签过滤（逗号分隔）
        cluster_ids: Cluster ID 过滤（逗号分隔）
        
    Returns:
        搜索结果列表
    """
    tag_list = tags.split(",") if tags else None
    cluster_id_list = [UUID(cid) for cid in cluster_ids.split(",")] if cluster_ids else None
    
    return await pool.search(q, k, tag_list, cluster_id_list)


@router.get("/", response_model=list[Memory])
async def list_memories(
    limit: int = Query(default=100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    tags: Optional[str] = Query(default=None, description="标签过滤（逗号分隔）"),
    cluster_ids: Optional[str] = Query(default=None, description="Cluster ID 过滤（逗号分隔）"),
    pool: MemoryPool = Depends(get_memory_pool)
) -> list[Memory]:
    """
    列出 Memory
    
    Args:
        limit: 返回数量限制
        offset: 偏移量
        tags: 标签过滤（逗号分隔）
        cluster_ids: Cluster ID 过滤（逗号分隔）
        
    Returns:
        Memory 列表
    """
    tag_list = tags.split(",") if tags else None
    cluster_id_list = [UUID(cid) for cid in cluster_ids.split(",")] if cluster_ids else None
    
    return await pool.list_all(limit, offset, tag_list, cluster_id_list)


@router.get("/stats", response_model=MemoryPoolStats)
async def get_memory_stats(
    pool: MemoryPool = Depends(get_memory_pool)
) -> MemoryPoolStats:
    """
    获取 Memory Pool 统计信息
    
    Returns:
        统计信息对象
    """
    return await pool.get_stats()