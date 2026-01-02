"""
SQLAlchemy ORM models for API Key management.

Defines the database schema for api_keys, rate_limits, and audit_logs tables.
"""
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean, DateTime, Integer, String, Text, BigInteger,
    ForeignKey, Index, func
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, INET, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class ApiKey(Base):
    """API Key model for storing hashed keys and metadata."""
    
    __tablename__ = "api_keys"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        primary_key=True, 
        default=lambda: str(uuid4())
    )
    
    # Key data (never store raw key!)
    key_prefix: Mapped[str] = mapped_column(
        String(16), 
        unique=True, 
        nullable=False,
        index=True,
        comment="SHA256 prefix for fast lookup"
    )
    key_hash: Mapped[str] = mapped_column(
        String(128), 
        nullable=False,
        comment="Argon2id hash for verification"
    )
    
    # Metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    service: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    permissions: Mapped[List[str]] = mapped_column(
        ARRAY(String), 
        default=list,
        nullable=False
    )
    
    # Lifecycle
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        index=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    revoke_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Statistics
    usage_count: Mapped[int] = mapped_column(BigInteger, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    last_used_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    audit_logs: Mapped[List["ApiKeyAuditLog"]] = relationship(
        "ApiKeyAuditLog", 
        back_populates="api_key",
        cascade="all, delete-orphan"
    )
    rate_limits: Mapped[List["RateLimit"]] = relationship(
        "RateLimit",
        back_populates="api_key",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name={self.name}, service={self.service})>"


class RateLimit(Base):
    """Rate limit tracking for API keys (PostgreSQL-based, no Redis)."""
    
    __tablename__ = "rate_limits"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), 
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False
    )
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False
    )
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationship
    api_key: Mapped["ApiKey"] = relationship("ApiKey", back_populates="rate_limits")
    
    __table_args__ = (
        Index("idx_rate_limit_key_window", "key_id", "window_start", unique=True),
    )


class ApiKeyAuditLog(Base):
    """Audit log for API key operations."""
    
    __tablename__ = "api_key_audit_logs"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), 
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(32), 
        nullable=False,
        comment="created, validated, revoked, expired, rate_limited"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        index=True
    )
    
    # Relationship
    api_key: Mapped[Optional["ApiKey"]] = relationship(
        "ApiKey", 
        back_populates="audit_logs"
    )
    
    __table_args__ = (
        Index("idx_audit_action", "action"),
        Index("idx_audit_key_id", "key_id"),
    )
