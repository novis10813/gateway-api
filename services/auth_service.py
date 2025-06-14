"""
Authentication service for gateway authentication service.

Contains all authentication-related business logic.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from fastapi import HTTPException, status
from jose import JWTError, jwt

from core.config import settings
from db.manager import api_key_db, migrate_from_config
from models.auth import TokenData


class AuthService:
    """認證服務類"""
    
    def __init__(self):
        """初始化認證服務"""
        # 啟動時遷移舊的 API Keys（僅在首次運行時）
        try:
            if settings.use_legacy_api_keys:
                migrate_from_config(settings.api_keys_list)
        except Exception as e:
            print(f"⚠️  Failed to migrate legacy keys: {e}")
    
    def verify_api_key(self, api_key: str, required_permission: str = None) -> Dict:
        """
        驗證 API Key，支援新舊兩種方式
        
        Args:
            api_key: API 金鑰
            required_permission: 需要的權限（可選）
        
        Returns:
            dict: API Key 信息和權限
        """
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API Key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 首先檢查新的數據庫
        result = api_key_db.validate_api_key(api_key, required_permission)
        if result["valid"]:
            return result
        
        # 如果啟用了向後兼容，檢查舊的配置
        if settings.use_legacy_api_keys and api_key in settings.api_keys_list:
            return {
                "valid": True,
                "service": "legacy",
                "permissions": ["admin"],  # 舊的 keys 默認擁有所有權限
                "name": "Legacy API Key"
            }
        
        # 都不匹配則拋出錯誤
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """創建 JWT token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(datetime.UTC) + expires_delta
        else:
            expire = datetime.now(datetime.UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        
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
    
    def authenticate_request(
        self, 
        api_key: Optional[str] = None, 
        jwt_token: Optional[str] = None,
        required_permission: str = None
    ) -> Dict:
        """
        驗證請求，支援 API Key 或 JWT token
        
        Args:
            api_key: API 金鑰（可選）
            jwt_token: JWT token（可選）
            required_permission: 需要的權限（可選）
        
        Returns:
            dict: 認證信息
        """
        # 優先檢查 API Key
        if api_key:
            # 使用新的數據庫驗證
            result = api_key_db.validate_api_key(api_key, required_permission)
            if result["valid"]:
                return {
                    "auth_type": "api_key", 
                    "key": api_key,
                    "service": result["service"],
                    "permissions": result["permissions"],
                    "name": result["name"]
                }
            
            # 向後兼容舊的配置
            if settings.use_legacy_api_keys and api_key in settings.api_keys_list:
                return {
                    "auth_type": "api_key", 
                    "key": api_key,
                    "service": "legacy",
                    "permissions": ["admin"],
                    "name": "Legacy API Key"
                }
        
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
                pass  # JWT 無效，繼續檢查其他認證方式
        
        # 都沒有則返回錯誤
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid API Key or JWT token required",
            headers={"WWW-Authenticate": "Bearer"},
        )


# 全局認證服務實例
auth_service = AuthService() 