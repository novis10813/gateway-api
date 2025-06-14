"""
Main router for API v1.

Aggregates all v1 endpoints into a single router.
"""
from fastapi import APIRouter

from api.v1.endpoints import auth, internal, health

# 創建 v1 主路由器
api_router = APIRouter()

# 包含認證端點
api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["authentication"]
)

# 包含內部管理端點
api_router.include_router(
    internal.router, 
    prefix="/internal", 
    tags=["internal"]
)

# 包含健康檢查和向後兼容端點
api_router.include_router(
    health.router, 
    tags=["health"]
) 