"""
Timeline API 路由

提供 Timeline 和 Conversation 相关的 REST API 端点。
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models.timeline import (
    Conversation,
    ConversationCreate,
    EventType,
    Timeline,
    TimelineCreate,
    TimelineExport,
    TimelineNode,
    TimelineNodeCreate,
    TimelineRangeQuery,
    TimelineStats,
)
from ..services.timeline_service import TimelineService, get_timeline_service

router = APIRouter(prefix="/timelines", tags=["timelines"])


# ==================== Timeline CRUD ====================


@router.post("/", response_model=Timeline)
async def create_timeline(
    timeline_create: TimelineCreate,
    service: TimelineService = Depends(get_timeline_service)
) -> Timeline:
    """
    创建新的 Timeline
    
    Args:
        timeline_create: 创建 Timeline 的请求数据
        
    Returns:
        创建的 Timeline 对象
    """
    return await service.create_timeline(timeline_create)


@router.get("/{timeline_id}", response_model=Timeline)
async def get_timeline(
    timeline_id: UUID,
    service: TimelineService = Depends(get_timeline_service)
) -> Timeline:
    """
    获取单个 Timeline
    
    Args:
        timeline_id: Timeline ID
        
    Returns:
        Timeline 对象
        
    Raises:
        HTTPException: Timeline 不存在时返回 404
    """
    timeline = await service.get_timeline(timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    return timeline


@router.delete("/{timeline_id}")
async def delete_timeline(
    timeline_id: UUID,
    service: TimelineService = Depends(get_timeline_service)
) -> dict:
    """
    删除 Timeline
    
    Args:
        timeline_id: Timeline ID
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: Timeline 不存在时返回 404
    """
    success = await service.delete_timeline(timeline_id)
    if not success:
        raise HTTPException(status_code=404, detail="Timeline not found")
    return {"status": "deleted", "timeline_id": str(timeline_id)}


@router.get("/{timeline_id}/stats", response_model=TimelineStats)
async def get_timeline_stats(
    timeline_id: UUID,
    service: TimelineService = Depends(get_timeline_service)
) -> TimelineStats:
    """
    获取 Timeline 统计信息
    
    Args:
        timeline_id: Timeline ID
        
    Returns:
        TimelineStats 对象
        
    Raises:
        HTTPException: Timeline 不存在时返回 404
    """
    timeline = await service.get_timeline(timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    
    return await service.get_stats(timeline_id)


@router.get("/{timeline_id}/export", response_model=TimelineExport)
async def export_timeline(
    timeline_id: UUID,
    service: TimelineService = Depends(get_timeline_service)
) -> TimelineExport:
    """
    导出 Timeline
    
    Args:
        timeline_id: Timeline ID
        
    Returns:
        TimelineExport 对象
        
    Raises:
        HTTPException: Timeline 不存在时返回 404
    """
    export = await service.export_timeline(timeline_id)
    if not export:
        raise HTTPException(status_code=404, detail="Timeline not found")
    return export


# ==================== TimelineNode ====================


@router.post("/{timeline_id}/node", response_model=TimelineNode)
async def add_timeline_node(
    timeline_id: UUID,
    node_create: TimelineNodeCreate,
    service: TimelineService = Depends(get_timeline_service)
) -> TimelineNode:
    """
    添加 Timeline 节点
    
    Args:
        timeline_id: Timeline ID
        node_create: 创建节点的请求数据
        
    Returns:
        创建的 TimelineNode 对象
        
    Raises:
        HTTPException: Timeline 不存在时返回 404
    """
    node = await service.add_node(timeline_id, node_create)
    if not node:
        raise HTTPException(status_code=404, detail="Timeline not found")
    return node


@router.get("/{timeline_id}/node/{node_id}", response_model=TimelineNode)
async def get_timeline_node(
    timeline_id: UUID,
    node_id: UUID,
    service: TimelineService = Depends(get_timeline_service)
) -> TimelineNode:
    """
    获取单个 Timeline 节点
    
    Args:
        timeline_id: Timeline ID
        node_id: 节点 ID
        
    Returns:
        TimelineNode 对象
        
    Raises:
        HTTPException: 节点不存在时返回 404
    """
    node = await service.get_node(node_id)
    if not node or node.timeline_id != timeline_id:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.delete("/{timeline_id}/node/{node_id}")
async def delete_timeline_node(
    timeline_id: UUID,
    node_id: UUID,
    service: TimelineService = Depends(get_timeline_service)
) -> dict:
    """
    删除 Timeline 节点
    
    Args:
        timeline_id: Timeline ID
        node_id: 节点 ID
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: 节点不存在时返回 404
    """
    node = await service.get_node(node_id)
    if not node or node.timeline_id != timeline_id:
        raise HTTPException(status_code=404, detail="Node not found")
    
    success = await service.delete_node(node_id)
    return {"status": "deleted", "node_id": str(node_id)}


@router.get("/{timeline_id}/range", response_model=list[TimelineNode])
async def get_timeline_range(
    timeline_id: UUID,
    start: str = Query(..., description="开始时间 (ISO format)"),
    end: str = Query(..., description="结束时间 (ISO format)"),
    event_types: Optional[str] = Query(default=None, description="事件类型过滤（逗号分隔）"),
    memory_id: Optional[UUID] = Query(default=None, description="Memory ID 过滤"),
    limit: int = Query(default=100, ge=1, le=1000, description="返回数量限制"),
    service: TimelineService = Depends(get_timeline_service)
) -> list[TimelineNode]:
    """
    获取时间范围内的节点
    
    Args:
        timeline_id: Timeline ID
        start: 开始时间 (ISO format)
        end: 结束时间 (ISO format)
        event_types: 事件类型过滤（逗号分隔）
        memory_id: Memory ID 过滤
        limit: 返回数量限制
        
    Returns:
        TimelineNode 列表
        
    Raises:
        HTTPException: Timeline 不存在时返回 404
    """
    timeline = await service.get_timeline(timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    
    from datetime import datetime
    
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")
    
    event_type_list = None
    if event_types:
        event_type_list = [EventType(et) for et in event_types.split(",")]
    
    query = TimelineRangeQuery(
        start=start_dt,
        end=end_dt,
        event_types=event_type_list,
        memory_id=memory_id,
        limit=limit
    )
    
    return await service.get_range(query)


@router.get("/{timeline_id}/memory/{memory_id}", response_model=list[TimelineNode])
async def get_timeline_nodes_by_memory(
    timeline_id: UUID,
    memory_id: UUID,
    service: TimelineService = Depends(get_timeline_service)
) -> list[TimelineNode]:
    """
    获取 Memory 关联的所有节点
    
    Args:
        timeline_id: Timeline ID
        memory_id: Memory ID
        
    Returns:
        TimelineNode 列表
        
    Raises:
        HTTPException: Timeline 不存在时返回 404
    """
    timeline = await service.get_timeline(timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    
    nodes = await service.get_nodes_by_memory(memory_id)
    # 过滤只返回当前 Timeline 的节点
    return [n for n in nodes if n.timeline_id == timeline_id]


# ==================== Conversation ====================


@router.post("/conversations", response_model=Conversation, tags=["conversations"])
async def create_conversation(
    conversation_create: ConversationCreate,
    service: TimelineService = Depends(get_timeline_service)
) -> Conversation:
    """
    创建新的 Conversation
    
    Args:
        conversation_create: 创建 Conversation 的请求数据
        
    Returns:
        创建的 Conversation 对象
    """
    return await service.create_conversation(conversation_create)


@router.get("/conversations/{conversation_id}", response_model=Conversation, tags=["conversations"])
async def get_conversation(
    conversation_id: UUID,
    service: TimelineService = Depends(get_timeline_service)
) -> Conversation:
    """
    获取单个 Conversation
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        Conversation 对象
        
    Raises:
        HTTPException: Conversation 不存在时返回 404
    """
    conversation = await service.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post(
    "/conversations/{conversation_id}/link/{timeline_id}",
    response_model=Conversation,
    tags=["conversations"]
)
async def link_conversation_timeline(
    conversation_id: UUID,
    timeline_id: UUID,
    service: TimelineService = Depends(get_timeline_service)
) -> Conversation:
    """
    关联 Conversation 和 Timeline
    
    Args:
        conversation_id: Conversation ID
        timeline_id: Timeline ID
        
    Returns:
        更新后的 Conversation 对象
        
    Raises:
        HTTPException: Conversation 不存在时返回 404
    """
    conversation = await service.link_conversation_timeline(conversation_id, timeline_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation