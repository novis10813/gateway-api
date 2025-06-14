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
    name: Optional[str] = None
    prefix: Optional[str] = ""
    length: Optional[int] = 32
    key_type: Optional[str] = "default"  # default, hex, urlsafe


class ApiKeyResponse(BaseModel):
    api_key: str
    name: Optional[str] = None
    created_at: str
    message: str


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
    return {
        "service": "Gateway Authentication Service - Internal",
        "status": "running",
        "client_ip": request.client.host,
        "api_keys_count": len(settings.api_keys_list),
        "jwt_algorithm": settings.jwt_algorithm
    }


@app.post("/internal/generate-api-key", response_model=ApiKeyResponse)
async def generate_new_api_key(
    request: Request,
    key_request: ApiKeyRequest,
    _: None = Depends(require_internal_access)
):
    """生成新的 API Key - 僅內部使用"""
    import secrets
    import string
    from datetime import datetime
    
    # 生成 API key
    if key_request.key_type == "hex":
        new_key = secrets.token_hex(key_request.length // 2)
    elif key_request.key_type == "urlsafe":
        new_key = secrets.token_urlsafe(key_request.length)[:key_request.length]
    else:  # default
        alphabet = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(key_request.length))
        if key_request.prefix:
            new_key = f"{key_request.prefix}_{random_part}"
        else:
            new_key = random_part
    
    return ApiKeyResponse(
        api_key=new_key,
        name=key_request.name,
        created_at=datetime.now().isoformat(),
        message="API Key generated successfully. Please save it securely and add to your configuration."
    )


@app.get("/internal/list-api-keys", response_model=dict)
async def list_api_keys(request: Request, _: None = Depends(require_internal_access)):
    """列出當前配置的 API Keys (隱藏完整內容) - 僅內部使用"""
    masked_keys = []
    for key in settings.api_keys_list:
        if len(key) > 8:
            masked = key[:4] + "*" * (len(key) - 8) + key[-4:]
        else:
            masked = "*" * len(key)
        masked_keys.append(masked)
    
    return {
        "total_keys": len(settings.api_keys_list),
        "masked_keys": masked_keys,
        "note": "Complete keys are not displayed for security reasons"
    }


@app.get("/internal/config", response_model=dict)
async def get_internal_config(request: Request, _: None = Depends(require_internal_access)):
    """獲取內部配置資訊 - 僅內部使用"""
    return {
        "jwt_algorithm": settings.jwt_algorithm,
        "jwt_expire_minutes": settings.jwt_access_token_expire_minutes,
        "api_keys_count": len(settings.api_keys_list),
        "allowed_origins": settings.allowed_origins_list,
        "debug_mode": settings.debug
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, debug=settings.debug)
