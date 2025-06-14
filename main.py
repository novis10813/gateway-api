from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import ipaddress

from config import settings
from auth import (
    verify_api_key, 
    create_access_token, 
    verify_token, 
    require_api_key_or_jwt,
    Token, 
    TokenData
)
from api_key_manager import api_key_db

app = FastAPI(
    title="Gateway Authentication Service",
    description="API Key 和 JWT 驗證服務",
    version="1.0.0"
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    api_key: str
    username: Optional[str] = "api_user"
    scopes: Optional[List[str]] = []


class AuthStatus(BaseModel):
    authenticated: bool
    auth_type: str
    message: str
    user: Optional[str] = None
    scopes: Optional[List[str]] = []


class ApiKeyRequest(BaseModel):
    name: str
    service: str
    permissions: Optional[List[str]] = ["read"]
    custom_key: Optional[str] = None


class ApiKeyResponse(BaseModel):
    api_key: str
    name: str
    service: str
    permissions: List[str]
    created_at: str
    message: str


class ApiKeyListResponse(BaseModel):
    total_keys: int
    keys: dict
    database_keys: dict
    legacy_keys: dict


class DeactivateKeyRequest(BaseModel):
    api_key: str


def is_internal_request(request: Request) -> bool:
    """檢查是否為內部請求"""
    client_ip = request.client.host
    
    # Docker 內部網路 IP 範圍
    internal_networks = [
        ipaddress.ip_network("172.16.0.0/12"),  # Docker default bridge
        ipaddress.ip_network("10.0.0.0/8"),    # Private network
        ipaddress.ip_network("192.168.0.0/16"), # Private network
        ipaddress.ip_network("127.0.0.0/8"),   # Localhost
    ]
    
    try:
        client_addr = ipaddress.ip_address(client_ip)
        return any(client_addr in network for network in internal_networks)
    except ValueError:
        return False


def require_internal_access(request: Request):
    """要求內部網路訪問"""
    if not is_internal_request(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Internal network access required"
        )


# ====== 對外服務端點 (External Endpoints) ======

@app.get("/", response_model=dict)
async def root():
    """服務狀態檢查 - 對外"""
    return {
        "service": "Gateway Authentication Service",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/dashboard", response_model=dict)
async def dashboard():
    """儀表板端點 - 對外 (保持向後兼容)"""
    return {"message": "FastAPI Authentication Service is running"}


@app.post("/auth/login", response_model=Token)
async def login_with_api_key(login_request: LoginRequest):
    """使用 API Key 登入並取得 JWT token - 對外"""
    
    # 驗證 API Key
    if login_request.api_key not in settings.api_keys_list:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    
    # 創建 JWT token
    access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    access_token = create_access_token(
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


@app.get("/auth/verify", response_model=AuthStatus)
async def verify_authentication(auth_info: dict = Depends(require_api_key_or_jwt)):
    """驗證認證狀態 (API Key 或 JWT) - 對外"""
    
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


@app.get("/auth/verify-api-key", response_model=AuthStatus)
async def verify_api_key_only(is_valid: bool = Depends(verify_api_key)):
    """僅驗證 API Key - 對外"""
    return AuthStatus(
        authenticated=True,
        auth_type="api_key", 
        message="Valid API Key"
    )


@app.get("/auth/verify-jwt", response_model=AuthStatus)
async def verify_jwt_only(token_data: TokenData = Depends(verify_token)):
    """僅驗證 JWT token - 對外"""
    return AuthStatus(
        authenticated=True,
        auth_type="jwt",
        message="Valid JWT token",
        user=token_data.username,
        scopes=token_data.scopes
    )


# 向後兼容的端點
@app.get("/your-api", response_model=dict)
async def legacy_api(is_valid: bool = Depends(verify_api_key)):
    """向後兼容的 API 端點 - 對外"""
    return {"message": "Welcome to your home API!"}


# ====== 內部管理端點 (Internal Management Endpoints) ======

@app.get("/internal/status", response_model=dict)
async def internal_status(request: Request, _: None = Depends(require_internal_access)):
    """內部服務狀態"""
    database_keys = api_key_db.list_api_keys()
    return {
        "service": "Gateway Authentication Service - Internal",
        "status": "running",
        "client_ip": request.client.host,
        "legacy_keys_count": len(settings.api_keys_list),
        "database_keys_count": len(database_keys),
        "total_active_keys": len(api_key_db.get_all_valid_keys()),
        "jwt_algorithm": settings.jwt_algorithm,
        "api_key_db_file": settings.api_key_db_file
    }


@app.post("/internal/generate-api-key", response_model=ApiKeyResponse)
async def generate_new_api_key(
    request: Request,
    key_request: ApiKeyRequest,
    _: None = Depends(require_internal_access)
):
    """生成新的 API Key 並存儲到數據庫 - 僅內部使用"""
    try:
        result = api_key_db.add_api_key(
            name=key_request.name,
            service=key_request.service,
            permissions=key_request.permissions,
            custom_key=key_request.custom_key
        )
        
        return ApiKeyResponse(
            api_key=result["api_key"],
            name=result["info"]["name"],
            service=result["info"]["service"],
            permissions=result["info"]["permissions"],
            created_at=result["info"]["created_at"],
            message="API Key generated and stored successfully. Please save it securely."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/internal/list-api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(request: Request, _: None = Depends(require_internal_access)):
    """列出所有 API Keys (隱藏完整內容) - 僅內部使用"""
    # 從數據庫獲取
    database_keys = api_key_db.list_api_keys()
    
    # 處理舊的配置 keys
    legacy_keys = {}
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
    
    # 合併所有 keys
    all_keys = {**database_keys, **legacy_keys}
    
    return ApiKeyListResponse(
        total_keys=len(all_keys),
        keys=all_keys,
        database_keys=database_keys,
        legacy_keys=legacy_keys
    )


@app.post("/internal/deactivate-api-key", response_model=dict)
async def deactivate_api_key(
    request: Request,
    deactivate_request: DeactivateKeyRequest,
    _: None = Depends(require_internal_access)
):
    """停用 API Key - 僅內部使用"""
    success = api_key_db.deactivate_api_key(deactivate_request.api_key)
    if success:
        return {
            "message": "API Key deactivated successfully",
            "api_key": deactivate_request.api_key[:8] + "...",
            "status": "deactivated"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found in database"
        )


@app.get("/internal/config", response_model=dict)
async def get_internal_config(request: Request, _: None = Depends(require_internal_access)):
    """獲取內部配置資訊 - 僅內部使用"""
    return {
        "jwt_algorithm": settings.jwt_algorithm,
        "jwt_expire_minutes": settings.jwt_access_token_expire_minutes,
        "legacy_keys_count": len(settings.api_keys_list),
        "database_keys_count": len(api_key_db.list_api_keys()),
        "use_legacy_keys": settings.use_legacy_api_keys,
        "api_key_db_file": settings.api_key_db_file,
        "allowed_origins": settings.allowed_origins_list,
        "debug_mode": settings.debug
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, debug=settings.debug)
