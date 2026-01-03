"""
Internal management endpoints for gateway authentication service.

Contains all internal management API endpoints for API key management.
Uses PostgreSQL backend via api_key_service_v2 for data storage.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request

from core.config import settings
from models.api_key import (
    ApiKeyRequest, 
    ApiKeyResponse, 
    ApiKeyListResponse,
    DeactivateKeyRequest
)
from api.deps import require_internal_access
from services.api_key_service_v2 import api_key_service_v2

router = APIRouter()


@router.get("/status", response_model=dict)
async def internal_status(request: Request, _: None = Depends(require_internal_access)):
    """內部服務狀態"""
    status_info = await api_key_service_v2.get_system_status()
    status_info["client_ip"] = request.client.host
    return status_info


@router.post("/generate-api-key", response_model=ApiKeyResponse)
async def generate_new_api_key(
    request: Request,
    key_request: ApiKeyRequest,
    _: None = Depends(require_internal_access)
):
    """生成新的 API Key 並存儲到 PostgreSQL 數據庫 - 僅內部使用"""
    return await api_key_service_v2.create_api_key(key_request)


@router.get("/list-api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(request: Request, _: None = Depends(require_internal_access)):
    """列出所有 API Keys (隱藏完整內容) - 僅內部使用"""
    return await api_key_service_v2.list_api_keys()


@router.post("/deactivate-api-key", response_model=dict)
async def deactivate_api_key(
    request: Request,
    deactivate_request: DeactivateKeyRequest,
    _: None = Depends(require_internal_access)
):
    """停用 API Key - 僅內部使用
    
    Note: Now requires key_id (UUID) instead of raw api_key.
    For backward compatibility, we'll need to look up the key first.
    """
    # TODO: For backward compatibility, may need to support looking up by prefix
    return await api_key_service_v2.deactivate_api_key(deactivate_request.api_key)


@router.get("/config", response_model=dict)
async def get_internal_config(request: Request, _: None = Depends(require_internal_access)):
    """獲取內部配置資訊 - 僅內部使用"""
    return await api_key_service_v2.get_system_config()