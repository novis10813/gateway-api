"""
Health check and legacy endpoints for gateway authentication service.

Contains health check and backward compatibility endpoints.
"""
from fastapi import APIRouter, Depends

from api.deps import verify_api_key

router = APIRouter()


@router.get("/", response_model=dict)
async def root():
    """服務狀態檢查 - 對外"""
    return {
        "service": "Gateway Authentication Service",
        "status": "running",
        "version": "1.0.0"
    }


@router.get("/dashboard", response_model=dict)
async def dashboard():
    """儀表板端點 - 對外 (保持向後兼容)"""
    return {"message": "FastAPI Authentication Service is running"}


@router.get("/your-api", response_model=dict)
async def legacy_api(is_valid: bool = Depends(verify_api_key)):
    """向後兼容的 API 端點 - 對外"""
    return {"message": "Welcome to your home API!"} 