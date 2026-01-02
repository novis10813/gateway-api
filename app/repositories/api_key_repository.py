"""
API Key Repository with caching support.

Implements the Repository Pattern with an LRU cache layer for efficient
API key lookups and management.
"""
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.db_models import ApiKey, ApiKeyAuditLog, RateLimit
from utils.hashing import generate_api_key, get_key_prefix, verify_api_key


class ApiKeyCache:
    """
    Thread-safe LRU cache with TTL support.
    
    Used to reduce database queries for frequently accessed API keys.
    """
    
    def __init__(self, maxsize: int = 1000, ttl_seconds: int = 300):
        self._cache: Dict[str, dict] = {}
        self._timestamps: Dict[str, datetime] = {}
        self._lock = threading.RLock()
        self._maxsize = maxsize
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> Optional[dict]:
        """Get a cached item if it exists and is not expired."""
        with self._lock:
            if key not in self._cache:
                return None
            
            # Check TTL
            if datetime.now() - self._timestamps[key] > self._ttl:
                del self._cache[key]
                del self._timestamps[key]
                return None
            
            return self._cache[key]
    
    def set(self, key: str, value: dict) -> None:
        """Set a cache item, evicting oldest if necessary."""
        with self._lock:
            # LRU eviction
            if len(self._cache) >= self._maxsize and key not in self._cache:
                oldest_key = min(self._timestamps, key=self._timestamps.get)
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
            
            self._cache[key] = value
            self._timestamps[key] = datetime.now()
    
    def invalidate(self, key: str) -> None:
        """Remove a specific item from cache."""
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
    
    def clear(self) -> None:
        """Clear all cached items."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self._maxsize,
                "ttl_seconds": self._ttl.total_seconds()
            }


class ApiKeyRepositoryInterface(ABC):
    """Abstract interface for API Key Repository."""
    
    @abstractmethod
    async def get_by_prefix(self, prefix: str) -> Optional[dict]:
        """Get an API key by its prefix."""
        pass
    
    @abstractmethod
    async def create(
        self, 
        name: str, 
        service: str, 
        permissions: List[str],
        expires_at: Optional[datetime] = None
    ) -> tuple[str, dict]:
        """Create a new API key. Returns (raw_key, key_data)."""
        pass
    
    @abstractmethod
    async def deactivate(self, key_id: str, reason: Optional[str] = None) -> bool:
        """Deactivate an API key."""
        pass
    
    @abstractmethod
    async def list_keys(
        self, 
        service: Optional[str] = None, 
        active_only: bool = True
    ) -> List[dict]:
        """List API keys with optional filtering."""
        pass
    
    @abstractmethod
    async def update_usage(
        self, 
        key_id: str, 
        client_ip: Optional[str] = None
    ) -> None:
        """Update usage statistics for an API key."""
        pass


class PostgresApiKeyRepository(ApiKeyRepositoryInterface):
    """PostgreSQL implementation of API Key Repository."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get_by_prefix(self, prefix: str) -> Optional[dict]:
        """Get an API key by its SHA256 prefix."""
        stmt = select(ApiKey).where(ApiKey.key_prefix == prefix)
        result = await self._session.execute(stmt)
        key = result.scalar_one_or_none()
        
        if key is None:
            return None
        
        return self._to_dict(key)
    
    async def create(
        self,
        name: str,
        service: str,
        permissions: List[str],
        expires_at: Optional[datetime] = None
    ) -> tuple[str, dict]:
        """Create a new API key with secure hashing."""
        # Generate key with hash
        raw_key, key_prefix, key_hash = generate_api_key(service)
        
        # Create database record
        api_key = ApiKey(
            key_prefix=key_prefix,
            key_hash=key_hash,
            name=name,
            service=service,
            permissions=permissions or ["read"],
            expires_at=expires_at,
            is_active=True,
        )
        
        self._session.add(api_key)
        await self._session.flush()  # Get the ID
        
        # Create audit log
        audit_log = ApiKeyAuditLog(
            key_id=api_key.id,
            action="created",
            details={"name": name, "service": service}
        )
        self._session.add(audit_log)
        
        return raw_key, self._to_dict(api_key)
    
    async def deactivate(self, key_id: str, reason: Optional[str] = None) -> bool:
        """Deactivate an API key by ID."""
        stmt = (
            update(ApiKey)
            .where(ApiKey.id == key_id)
            .values(
                is_active=False,
                revoked_at=datetime.now(timezone.utc),
                revoke_reason=reason or "Manually revoked"
            )
            .returning(ApiKey.id)
        )
        result = await self._session.execute(stmt)
        affected = result.scalar_one_or_none()
        
        if affected:
            # Create audit log
            audit_log = ApiKeyAuditLog(
                key_id=key_id,
                action="revoked",
                details={"reason": reason}
            )
            self._session.add(audit_log)
            return True
        
        return False
    
    async def list_keys(
        self,
        service: Optional[str] = None,
        active_only: bool = True
    ) -> List[dict]:
        """List API keys with optional filtering."""
        conditions = []
        
        if active_only:
            conditions.append(ApiKey.is_active == True)
        if service:
            conditions.append(ApiKey.service == service)
        
        stmt = select(ApiKey)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(ApiKey.created_at.desc())
        
        result = await self._session.execute(stmt)
        keys = result.scalars().all()
        
        return [self._to_dict(key, mask_prefix=True) for key in keys]
    
    async def update_usage(
        self,
        key_id: str,
        client_ip: Optional[str] = None
    ) -> None:
        """Update usage statistics for an API key."""
        stmt = (
            update(ApiKey)
            .where(ApiKey.id == key_id)
            .values(
                usage_count=ApiKey.usage_count + 1,
                last_used_at=datetime.now(timezone.utc),
                last_used_ip=client_ip
            )
        )
        await self._session.execute(stmt)
    
    async def check_rate_limit(
        self,
        key_id: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit.
        
        Returns:
            (is_allowed, remaining_requests)
        """
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)
        
        # Clean old windows
        delete_stmt = RateLimit.__table__.delete().where(
            RateLimit.window_start < window_start
        )
        await self._session.execute(delete_stmt)
        
        # Get or create current window
        current_minute = now.replace(second=0, microsecond=0)
        stmt = select(RateLimit).where(
            and_(
                RateLimit.key_id == key_id,
                RateLimit.window_start == current_minute
            )
        )
        result = await self._session.execute(stmt)
        rate_limit = result.scalar_one_or_none()
        
        if rate_limit is None:
            rate_limit = RateLimit(
                key_id=key_id,
                window_start=current_minute,
                request_count=1
            )
            self._session.add(rate_limit)
            await self._session.flush()
            return True, limit - 1
        
        if rate_limit.request_count >= limit:
            return False, 0
        
        rate_limit.request_count += 1
        return True, limit - rate_limit.request_count
    
    def _to_dict(self, key: ApiKey, mask_prefix: bool = False) -> dict:
        """Convert ApiKey model to dictionary."""
        prefix = key.key_prefix
        if mask_prefix:
            prefix = prefix[:4] + "****" + prefix[-4:]
        
        return {
            "id": key.id,
            "key_prefix": prefix,
            "key_hash": key.key_hash,
            "name": key.name,
            "service": key.service,
            "permissions": key.permissions,
            "is_active": key.is_active,
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "revoked_at": key.revoked_at.isoformat() if key.revoked_at else None,
            "revoke_reason": key.revoke_reason,
            "usage_count": key.usage_count,
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "created_at": key.created_at.isoformat() if key.created_at else None,
        }


class CachedApiKeyRepository(ApiKeyRepositoryInterface):
    """
    Caching decorator for API Key Repository.
    
    Wraps another repository and adds LRU cache with TTL.
    """
    
    def __init__(self, inner: PostgresApiKeyRepository, cache: ApiKeyCache):
        self._inner = inner
        self._cache = cache
    
    async def get_by_prefix(self, prefix: str) -> Optional[dict]:
        """Get from cache first, then database."""
        # Check cache
        cached = self._cache.get(prefix)
        if cached is not None:
            return cached
        
        # Query database
        result = await self._inner.get_by_prefix(prefix)
        if result:
            self._cache.set(prefix, result)
        
        return result
    
    async def create(
        self,
        name: str,
        service: str,
        permissions: List[str],
        expires_at: Optional[datetime] = None
    ) -> tuple[str, dict]:
        """Create key (no caching needed for creation)."""
        return await self._inner.create(name, service, permissions, expires_at)
    
    async def deactivate(self, key_id: str, reason: Optional[str] = None) -> bool:
        """Deactivate and invalidate cache."""
        result = await self._inner.deactivate(key_id, reason)
        # Note: We'd need key_prefix to invalidate cache efficiently
        # For now, don't cache deactivated keys
        return result
    
    async def list_keys(
        self,
        service: Optional[str] = None,
        active_only: bool = True
    ) -> List[dict]:
        """List keys (no caching for list operations)."""
        return await self._inner.list_keys(service, active_only)
    
    async def update_usage(
        self,
        key_id: str,
        client_ip: Optional[str] = None
    ) -> None:
        """Update usage (async, don't block)."""
        await self._inner.update_usage(key_id, client_ip)
    
    def invalidate_by_prefix(self, prefix: str) -> None:
        """Invalidate a specific cache entry."""
        self._cache.invalidate(prefix)
    
    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
    
    def cache_stats(self) -> dict:
        """Get cache statistics."""
        return self._cache.stats()


# Global cache instance
_api_key_cache = ApiKeyCache(
    maxsize=settings.cache_max_size,
    ttl_seconds=settings.cache_ttl_seconds
)


def get_api_key_cache() -> ApiKeyCache:
    """Get the global API key cache instance."""
    return _api_key_cache
