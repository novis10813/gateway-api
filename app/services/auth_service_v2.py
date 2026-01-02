"""
Refactored Authentication service with secure hashing and caching.

Supports both the new PostgreSQL-based system and legacy JSON file for
backward compatibility during migration.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.database import db_manager
from db.manager import api_key_db  # Legacy support
from models.auth import TokenData
from repositories.api_key_repository import (
    PostgresApiKeyRepository,
    CachedApiKeyRepository,
    get_api_key_cache,
)
from utils.hashing import get_key_prefix, verify_api_key


class AuthServiceV2:
    """
    認證服務類 (V2 - PostgreSQL + Hashing)
    
    Features:
    - Argon2id hashed API keys
    - LRU cache for fast lookups
    - Rate limiting
    - TTL and revocation support
    - Audit logging
    """
    
    def __init__(self):
        self._cache = get_api_key_cache()
    
    async def verify_api_key(
        self,
        api_key: str,
        required_permission: Optional[str] = None,
        service_name: Optional[str] = None,
        client_ip: Optional[str] = None,
        session: Optional[AsyncSession] = None
    ) -> Dict:
        """
        驗證 API Key，支援新舊兩種方式和服務綁定驗證
        
        Args:
            api_key: API 金鑰
            required_permission: 需要的權限（可選）
            service_name: 請求的服務名稱（可選，用於服務綁定驗證）
            client_ip: 客戶端 IP（可選，用於稽核）
            session: 資料庫 session（可選，若不提供則自動建立）
        
        Returns:
            dict: API Key 信息和權限
        """
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API Key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get key prefix for lookup
        prefix = get_key_prefix(api_key)
        
        # Use provided session or create new one
        if session:
            return await self._verify_with_session(
                session, api_key, prefix, required_permission, 
                service_name, client_ip
            )
        else:
            async with db_manager.session() as new_session:
                return await self._verify_with_session(
                    new_session, api_key, prefix, required_permission,
                    service_name, client_ip
                )
    
    async def _verify_with_session(
        self,
        session: AsyncSession,
        api_key: str,
        prefix: str,
        required_permission: Optional[str],
        service_name: Optional[str],
        client_ip: Optional[str]
    ) -> Dict:
        """Internal verification with session."""
        # Create repository with cache
        repo = CachedApiKeyRepository(
            PostgresApiKeyRepository(session),
            self._cache
        )
        
        # Get key data
        key_data = await repo.get_by_prefix(prefix)
        
        if not key_data:
            # Try legacy JSON file as fallback
            if settings.use_legacy_api_keys:
                return await self._verify_legacy(api_key, required_permission)
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if active
        if not key_data["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check TTL
        if key_data.get("expires_at"):
            expires_at = datetime.fromisoformat(key_data["expires_at"])
            if datetime.now(timezone.utc) > expires_at:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API Key has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Verify hash
        if not verify_api_key(api_key, key_data["key_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check rate limit
        inner_repo = PostgresApiKeyRepository(session)
        is_allowed, remaining = await inner_repo.check_rate_limit(
            key_data["id"],
            settings.rate_limit_requests_per_minute,
            settings.rate_limit_window_seconds
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(settings.rate_limit_window_seconds)
                },
            )
        
        # Check service binding
        key_service = key_data["service"]
        if service_name and key_service != "legacy":
            if key_service != service_name:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API Key for service '{key_service}' cannot access service '{service_name}'",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Check permissions
        permissions = key_data.get("permissions", [])
        if required_permission:
            if required_permission not in permissions and "admin" not in permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {required_permission}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Update usage stats (fire and forget)
        asyncio.create_task(
            self._update_usage_async(key_data["id"], client_ip)
        )
        
        return {
            "valid": True,
            "service": key_service,
            "permissions": permissions,
            "name": key_data["name"],
            "rate_limit_remaining": remaining
        }
    
    async def _verify_legacy(
        self,
        api_key: str,
        required_permission: Optional[str]
    ) -> Dict:
        """Fallback to legacy JSON verification."""
        result = api_key_db.validate_api_key(api_key, required_permission)
        
        if result["valid"]:
            return result
        
        # Also check config-based keys
        if api_key in settings.api_keys_list:
            return {
                "valid": True,
                "service": "legacy",
                "permissions": ["admin"],
                "name": "Legacy API Key"
            }
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    async def _update_usage_async(self, key_id: str, client_ip: Optional[str]) -> None:
        """Update usage statistics asynchronously."""
        try:
            async with db_manager.session() as session:
                repo = PostgresApiKeyRepository(session)
                await repo.update_usage(key_id, client_ip)
        except Exception:
            # Don't fail the request if usage update fails
            pass
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """創建 JWT token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return encoded_jwt
    
    def verify_jwt_token(self, token: str) -> TokenData:
        """驗證 JWT token"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            scopes = payload.get("scopes", [])
            return TokenData(username=username, scopes=scopes)
        except JWTError:
            raise credentials_exception
    
    async def authenticate_request(
        self, 
        api_key: Optional[str] = None, 
        jwt_token: Optional[str] = None,
        required_permission: Optional[str] = None,
        service_name: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> Dict:
        """
        驗證請求，支援 API Key 或 JWT token，以及服務綁定驗證
        """
        # 優先檢查 API Key
        if api_key:
            try:
                result = await self.verify_api_key(
                    api_key, required_permission, service_name, client_ip
                )
                return {
                    "auth_type": "api_key", 
                    "key": api_key[:8] + "...",  # Don't expose full key
                    "service": result["service"],
                    "permissions": result["permissions"],
                    "name": result["name"],
                    "rate_limit_remaining": result.get("rate_limit_remaining")
                }
            except HTTPException:
                pass  # Try JWT if API Key fails
        
        # 如果沒有 API Key 或 API Key 無效，檢查 JWT
        if jwt_token:
            try:
                payload = jwt.decode(jwt_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
                username: str = payload.get("sub")
                if username is None:
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
                scopes = payload.get("scopes", [])
                
                # 檢查權限
                if required_permission and required_permission not in scopes and "admin" not in scopes:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions. Required: {required_permission}"
                    )
                
                return {"auth_type": "jwt", "user": username, "scopes": scopes}
            except JWTError:
                pass
        
        # 都沒有則返回錯誤
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid API Key or JWT token required",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Global instance
auth_service_v2 = AuthServiceV2()
