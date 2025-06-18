"""
Authentication endpoints for gateway authentication service.

Contains all authentication-related API endpoints.
"""
import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict

from core.config import settings
from models.auth import LoginRequest, AuthStatus, Token, TokenData
from api.deps import (
    verify_api_key, 
    verify_token, 
    require_api_key_or_jwt
)
from services.auth_service import auth_service

# 設置 logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_with_api_key(login_request: LoginRequest):
    """使用 API Key 登入並取得 JWT token"""
    
    # 使用認證服務驗證 API Key（不進行服務綁定驗證，因為這是登入端點）
    try:
        result = auth_service.verify_api_key(login_request.api_key)
        logger.info(f"登入驗證通過: {result['name']} (service: {result['service']})")
    except HTTPException as e:
        logger.warning(f"登入驗證失敗: {e.detail}")
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
    """驗證認證狀態 (API Key 或 JWT)，支援服務綁定驗證"""
    
    if auth_info["auth_type"] == "api_key":
        service = auth_info.get("service", "unknown")
        message = f"Valid API Key for service '{service}'" if service != "unknown" else "Valid API Key"
        return AuthStatus(
            authenticated=True,
            auth_type="api_key",
            message=message,
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
async def verify_api_key_only(
    request: Request,
    is_valid: bool = Depends(verify_api_key)
):
    """僅驗證 API Key - 帶詳細日誌和服務綁定驗證"""
    
    # 獲取請求信息
    api_key = request.headers.get("X-API-Key", "")
    service_name = request.headers.get("X-Service-Name", "")
    original_uri = request.headers.get("X-Original-URI", "")
    client_ip = request.client.host
    user_agent = request.headers.get("User-Agent", "")
    
    # 記錄請求詳情
    logger.info(f"API Key 驗證請求: "
                f"IP={client_ip}, "
                f"URI={original_uri}, "
                f"Service={service_name}, "
                f"API_Key={'存在' if api_key else '缺失'}, "
                f"Key_prefix={api_key[:10]}... 如果存在")
    
    # 如果有 User-Agent，記錄客戶端類型
    if "obsidian" in user_agent.lower():
        logger.info(f"Obsidian 客戶端請求: {user_agent}")
    
    # 記錄服務綁定驗證結果
    if service_name:
        logger.info(f"服務綁定驗證通過: API Key 可存取服務 '{service_name}'")
    else:
        logger.info("未指定服務名稱，跳過服務綁定驗證")
    
    return AuthStatus(
        authenticated=True,
        auth_type="api_key", 
        message=f"Valid API Key for service '{service_name}'" if service_name else "Valid API Key"
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