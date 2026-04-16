"""
Cluster Memory API 主入口

FastAPI 应用配置和启动。
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..services.cluster_manager import ClusterManager, ClusterManagerConfig
from ..services.memory_pool import MemoryPool, MemoryPoolConfig
from ..services.timeline_service import TimelineService, TimelineServiceConfig
from .routes import cluster, memory, search, timeline

# 全局服务实例
_memory_pool: MemoryPool | None = None
_cluster_manager: ClusterManager | None = None
_timeline_service: TimelineService | None = None


def get_memory_pool() -> MemoryPool:
    """获取 MemoryPool 依赖"""
    if _memory_pool is None:
        raise RuntimeError("MemoryPool not initialized")
    return _memory_pool


def get_cluster_manager() -> ClusterManager:
    """获取 ClusterManager 依赖"""
    if _cluster_manager is None:
        raise RuntimeError("ClusterManager not initialized")
    return _cluster_manager


def get_timeline_service() -> TimelineService:
    """获取 TimelineService 依赖"""
    if _timeline_service is None:
        raise RuntimeError("TimelineService not initialized")
    return _timeline_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    在启动时初始化服务，在关闭时清理资源。
    """
    # 启动时初始化
    config_path = Path("./data/cluster_memory")
    
    _memory_pool = MemoryPool(MemoryPoolConfig(db_path=str(config_path)))
    _cluster_manager = ClusterManager(ClusterManagerConfig(db_path=str(config_path)))
    _timeline_service = TimelineService(TimelineServiceConfig(db_path=str(config_path)))
    
    await _memory_pool.initialize()
    await _cluster_manager.initialize()
    await _timeline_service.initialize()
    
    yield
    
    # 关闭时清理
    await _memory_pool.close()
    await _cluster_manager.close()
    await _timeline_service.close()


# 创建 FastAPI 应用
app = FastAPI(
    title="Cluster Memory API",
    description="Cluster Memory 系统的 REST API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(memory.router)
app.include_router(cluster.router)
app.include_router(timeline.router)
app.include_router(search.router)


@app.get("/")
async def root() -> dict:
    """
    根路径
    
    返回 API 信息。
    """
    return {
        "name": "Cluster Memory API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check() -> dict:
    """
    健康检查
    
    返回服务状态。
    """
    return {
        "status": "healthy",
        "services": {
            "memory_pool": _memory_pool is not None,
            "cluster_manager": _cluster_manager is not None,
            "timeline_service": _timeline_service is not None
        }
    }


# 如果作为主模块运行
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )