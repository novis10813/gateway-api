"""
Authentication endpoints for gateway authentication service.

Contains all authentication-related API endpoints.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict

from core.config import settings
from models.auth import LoginRequest, AuthStatus, Token, TokenData
from api.deps import (
    verify_api_key, 
    verify_token, 
    require_api_key_or_jwt
)
from services.auth_service import auth_service

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_with_api_key(login_request: LoginRequest):
    """使用 API Key 登入並取得 JWT token"""
    
    # 驗證 API Key
    if login_request.api_key not in settings.api_keys_list:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    
    # 創建 JWT token
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={
            "sub": login_request.username,
            "scopes": login_request.scopes or []
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/verify", response_model=AuthStatus)
async def verify_authentication(auth_info: dict = Depends(require_api_key_or_jwt)):
    """驗證認證狀態 (API Key 或 JWT)"""
    
    if auth_info["auth_type"] == "api_key":
        return AuthStatus(
            authenticated=True,
            auth_type="api_key",
            message="Valid API Key",
        )
    else:  # JWT
        return AuthStatus(
            authenticated=True,
            auth_type="jwt",
            message="Valid JWT token",
            user=auth_info["user"],
            scopes=auth_info["scopes"]
        )


@router.get("/verify-api-key", response_model=AuthStatus)
async def verify_api_key_only(is_valid: bool = Depends(verify_api_key)):
    """僅驗證 API Key"""
    return AuthStatus(
        authenticated=True,
        auth_type="api_key", 
        message="Valid API Key"
    )


@router.get("/verify-jwt", response_model=AuthStatus)
async def verify_jwt_only(token_data: TokenData = Depends(verify_token)):
    """僅驗證 JWT token"""
    return AuthStatus(
        authenticated=True,
        auth_type="jwt",
        message="Valid JWT token",
        user=token_data.username,
        scopes=token_data.scopes
    ) 