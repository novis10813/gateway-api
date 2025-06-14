"""
Authentication models for gateway authentication service.

Contains Pydantic models for authentication-related requests and responses.
"""
from pydantic import BaseModel
from typing import Optional, List


class LoginRequest(BaseModel):
    """登入請求模型"""
    api_key: str
    username: Optional[str] = "api_user"
    scopes: Optional[List[str]] = []


class AuthStatus(BaseModel):
    """認證狀態回應模型"""
    authenticated: bool
    auth_type: str
    message: str
    user: Optional[str] = None
    scopes: Optional[List[str]] = []


class Token(BaseModel):
    """JWT Token 回應模型"""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """JWT Token 資料模型"""
    username: Optional[str] = None
    scopes: List[str] = [] 