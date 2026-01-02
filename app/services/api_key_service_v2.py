"""
API Key service V2 for gateway authentication service.

Contains all API key management business logic using PostgreSQL backend.
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.database import db_manager
from models.api_key import ApiKeyRequest, ApiKeyResponse, ApiKeyListResponse
from repositories.api_key_repository import (
    PostgresApiKeyRepository,
    CachedApiKeyRepository,
    get_api_key_cache,
)


class ApiKeyServiceV2:
    """API Key 管理服務類 (V2 - PostgreSQL + Hashing)"""
    
    def __init__(self):
        self._cache = get_api_key_cache()
    
    async def create_api_key(
        self,
        request: ApiKeyRequest,
        expires_in_days: Optional[int] = None,
        session: Optional[AsyncSession] = None
    ) -> ApiKeyResponse:
        """
        創建新的 API Key
        
        Args:
            request: API Key 創建請求
            expires_in_days: Key 過期天數（可選）
            session: 資料庫 session（可選）
            
        Returns:
            ApiKeyResponse: 創建結果（包含原始 key，僅顯示一次）
        """
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        async def _create(sess: AsyncSession) -> ApiKeyResponse:
            repo = PostgresApiKeyRepository(sess)
            
            raw_key, key_data = await repo.create(
                name=request.name,
                service=request.service,
                permissions=request.permissions or ["read"],
                expires_at=expires_at
            )
            
            return ApiKeyResponse(
                api_key=raw_key,  # Only shown once!
                name=key_data["name"],
                service=key_data["service"],
                permissions=key_data["permissions"],
                created_at=key_data["created_at"],
                message="API Key generated successfully. Save it securely - it cannot be retrieved again."
            )
        
        if session:
            return await _create(session)
        else:
            async with db_manager.session() as new_session:
                return await _create(new_session)
    
    async def list_api_keys(
        self,
        service: Optional[str] = None,
        active_only: bool = True,
        session: Optional[AsyncSession] = None
    ) -> ApiKeyListResponse:
        """
        列出 API Keys
        
        Args:
            service: 過濾特定服務（可選）
            active_only: 是否只顯示活躍的 keys
            session: 資料庫 session（可選）
            
        Returns:
            ApiKeyListResponse: API Key 列表（key_prefix 已遮蔽）
        """
        async def _list(sess: AsyncSession) -> ApiKeyListResponse:
            repo = PostgresApiKeyRepository(sess)
            keys = await repo.list_keys(service=service, active_only=active_only)
            
            # Convert to dict format for response
            database_keys = {}
            for key in keys:
                masked_prefix = key["key_prefix"]  # Already masked in repo
                database_keys[masked_prefix] = {
                    "id": key["id"],
                    "name": key["name"],
                    "service": key["service"],
                    "permissions": key["permissions"],
                    "created_at": key["created_at"],
                    "last_used_at": key["last_used_at"],
                    "usage_count": key["usage_count"],
                    "expires_at": key["expires_at"],
                    "is_active": key["is_active"],
                }
            
            # Legacy keys (for backward compatibility)
            legacy_keys = {}
            if settings.use_legacy_api_keys and (not service or service == "legacy"):
                for i, key in enumerate(settings.api_keys_list):
                    if len(key) > 8:
                        masked = key[:4] + "*" * (len(key) - 8) + key[-4:]
                    else:
                        masked = "*" * len(key)
                    legacy_keys[masked] = {
                        "name": f"Legacy Key {i+1}",
                        "service": "legacy",
                        "permissions": ["admin"],
                        "created_at": "N/A",
                        "source": "config"
                    }
            
            all_keys = {**database_keys, **legacy_keys}
            
            return ApiKeyListResponse(
                total_keys=len(all_keys),
                keys=all_keys,
                database_keys=database_keys,
                legacy_keys=legacy_keys
            )
        
        if session:
            return await _list(session)
        else:
            async with db_manager.session() as new_session:
                return await _list(new_session)
    
    async def deactivate_api_key(
        self,
        key_id: str,
        reason: Optional[str] = None,
        session: Optional[AsyncSession] = None
    ) -> Dict:
        """
        停用 API Key
        
        Args:
            key_id: API Key ID (UUID)
            reason: 停用原因（可選）
            session: 資料庫 session（可選）
            
        Returns:
            dict: 操作結果
        """
        async def _deactivate(sess: AsyncSession) -> Dict:
            repo = CachedApiKeyRepository(
                PostgresApiKeyRepository(sess),
                self._cache
            )
            
            success = await repo.deactivate(key_id, reason)
            
            if success:
                return {
                    "message": "API Key deactivated successfully",
                    "key_id": key_id,
                    "status": "deactivated",
                    "reason": reason
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="API Key not found"
                )
        
        if session:
            return await _deactivate(session)
        else:
            async with db_manager.session() as new_session:
                return await _deactivate(new_session)
    
    async def get_system_status(self) -> Dict:
        """
        獲取系統狀態
        
        Returns:
            dict: 系統狀態信息
        """
        async with db_manager.session() as session:
            repo = PostgresApiKeyRepository(session)
            keys = await repo.list_keys(active_only=False)
            active_keys = [k for k in keys if k["is_active"]]
            
            return {
                "service": "Gateway Authentication Service V2",
                "status": "running",
                "database": "PostgreSQL",
                "legacy_keys_count": len(settings.api_keys_list) if settings.use_legacy_api_keys else 0,
                "database_keys_count": len(keys),
                "total_active_keys": len(active_keys),
                "cache_stats": self._cache.stats(),
                "rate_limit": {
                    "requests_per_minute": settings.rate_limit_requests_per_minute,
                    "window_seconds": settings.rate_limit_window_seconds
                }
            }
    
    async def get_system_config(self) -> Dict:
        """
        獲取系統配置
        
        Returns:
            dict: 系統配置信息
        """
        return {
            "jwt_algorithm": settings.jwt_algorithm,
            "jwt_expire_minutes": settings.jwt_access_token_expire_minutes,
            "use_legacy_keys": settings.use_legacy_api_keys,
            "database_url": settings.database_url.split("@")[-1],  # Hide credentials
            "cache_max_size": settings.cache_max_size,
            "cache_ttl_seconds": settings.cache_ttl_seconds,
            "rate_limit_requests_per_minute": settings.rate_limit_requests_per_minute,
            "allowed_origins": settings.allowed_origins_list,
            "debug_mode": settings.debug
        }


# 全局 API Key 服務實例
api_key_service_v2 = ApiKeyServiceV2()
