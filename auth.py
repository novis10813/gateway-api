from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import HTTPException, Header, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from config import settings


security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []


class Token(BaseModel):
    access_token: str
    token_type: str


def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")) -> bool:
    """驗證 API Key"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if x_api_key not in settings.api_keys_list:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """創建 JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(datetime.UTC) + expires_delta
    else:
        expire = datetime.now(datetime.UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """驗證 JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=scopes)
    except JWTError:
        raise credentials_exception
    
    return token_data


def require_api_key_or_jwt(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
) -> dict:
    """要求 API Key 或 JWT token 其中之一"""
    
    # 優先檢查 API Key
    if x_api_key and x_api_key in settings.api_keys_list:
        return {"auth_type": "api_key", "key": x_api_key}
    
    # 如果沒有 API Key，檢查 JWT
    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
            scopes = payload.get("scopes", [])
            return {"auth_type": "jwt", "user": username, "scopes": scopes}
        except JWTError:
            pass  # JWT 無效，繼續檢查其他認證方式
    
    # 都沒有則返回錯誤
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid API Key or JWT token required",
        headers={"WWW-Authenticate": "Bearer"},
    ) 