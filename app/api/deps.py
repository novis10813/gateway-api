"""
API dependencies for gateway authentication service.

Contains dependency injection functions for authentication and authorization.
Uses V2 async PostgreSQL-based auth service.
"""
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Optional
import ipaddress
import logging

from services.auth_service_v2 import auth_service_v2
from models.auth import TokenData

logger = logging.getLogger(__name__)

# FastAPI Security schemes
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


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


async def verify_api_key(
    request: Request,
    x_api_key: str = Header(None, alias="X-API-Key"), 
    x_service_name: Optional[str] = Header(None, alias="X-Service-Name"),
    required_permission: str = None
) -> bool:
    """驗證 API Key 依賴注入函數，支援服務綁定驗證 (V2 async PostgreSQL)"""
    logger.info(f"deps.verify_api_key 調用")
    logger.info(f"x_api_key 存在: {'是' if x_api_key else '否'}")
    logger.info(f"x_service_name: {x_service_name}")
    if x_api_key:
        logger.info(f"x_api_key 前 10 個字符: {x_api_key[:10]}")
    else:
        logger.info("x_api_key 不存在")

    try:
        client_ip = request.client.host if request.client else None
        result = await auth_service_v2.verify_api_key(
            x_api_key, required_permission, x_service_name, client_ip
        )
        logger.info(f"verify_api_key 返回結果: {result}")
        return True
    except Exception as e:
        logger.error(f"auth_service_v2.verify_api_key 調用失敗: {e}")
        raise


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """驗證 JWT token 依賴注入函數"""
    return auth_service_v2.verify_jwt_token(credentials.credentials)


async def require_api_key_or_jwt(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_service_name: Optional[str] = Header(None, alias="X-Service-Name"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    required_permission: str = None
) -> Dict:
    """要求 API Key 或 JWT token 其中之一的依賴注入函數，支援服務綁定驗證 (V2 async)"""
    jwt_token = credentials.credentials if credentials else None
    client_ip = request.client.host if request.client else None
    return await auth_service_v2.authenticate_request(
        x_api_key, jwt_token, required_permission, x_service_name, client_ip
    )


# 重新導出認證依賴，便於其他模組使用
__all__ = [
    "verify_api_key",
    "verify_token", 
    "require_api_key_or_jwt",
    "require_internal_access",
    "is_internal_request",
    "TokenData",
    "security",
    "optional_security"
]