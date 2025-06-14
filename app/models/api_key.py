"""
API Key models for gateway authentication service.

Contains Pydantic models for API key management requests and responses.
"""
from pydantic import BaseModel
from typing import Optional, List


class ApiKeyRequest(BaseModel):
    """API Key 創建請求模型"""
    name: str
    service: str
    permissions: Optional[List[str]] = ["read"]
    custom_key: Optional[str] = None


class ApiKeyResponse(BaseModel):
    """API Key 創建回應模型"""
    api_key: str
    name: str
    service: str
    permissions: List[str]
    created_at: str
    message: str


class ApiKeyListResponse(BaseModel):
    """API Key 列表回應模型"""
    total_keys: int
    keys: dict
    database_keys: dict
    legacy_keys: dict


class DeactivateKeyRequest(BaseModel):
    """API Key 停用請求模型"""
    api_key: str 