"""
API Key service for gateway authentication service.

Contains all API key management business logic.
"""
from typing import Dict, List, Optional
from fastapi import HTTPException, status

from core.config import settings
from db.manager import api_key_db
from models.api_key import ApiKeyRequest, ApiKeyResponse, ApiKeyListResponse


class ApiKeyService:
    """API Key 管理服務類"""
    
    def create_api_key(self, request: ApiKeyRequest) -> ApiKeyResponse:
        """
        創建新的 API Key
        
        Args:
            request: API Key 創建請求
            
        Returns:
            ApiKeyResponse: 創建結果
        """
        try:
            result = api_key_db.add_api_key(
                name=request.name,
                service=request.service,
                permissions=request.permissions,
                custom_key=request.custom_key
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
    
    def list_api_keys(self, service: Optional[str] = None, active_only: bool = True) -> ApiKeyListResponse:
        """
        列出 API Keys
        
        Args:
            service: 過濾特定服務（可選）
            active_only: 是否只顯示活躍的 keys
            
        Returns:
            ApiKeyListResponse: API Key 列表
        """
        # 從數據庫獲取
        database_keys = api_key_db.list_api_keys(service=service, active_only=active_only)
        
        # 處理舊的配置 keys
        legacy_keys = {}
        if not service or service == "legacy":  # 只有在沒有過濾或過濾 legacy 時才顯示
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
    
    def deactivate_api_key(self, api_key: str) -> Dict:
        """
        停用 API Key
        
        Args:
            api_key: 要停用的 API Key
            
        Returns:
            dict: 操作結果
        """
        success = api_key_db.deactivate_api_key(api_key)
        if success:
            return {
                "message": "API Key deactivated successfully",
                "api_key": api_key[:8] + "...",
                "status": "deactivated"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key not found in database"
            )
    
    def get_system_status(self) -> Dict:
        """
        獲取系統狀態
        
        Returns:
            dict: 系統狀態信息
        """
        database_keys = api_key_db.list_api_keys()
        return {
            "service": "Gateway Authentication Service - Internal",
            "status": "running",
            "legacy_keys_count": len(settings.api_keys_list),
            "database_keys_count": len(database_keys),
            "total_active_keys": len(api_key_db.get_all_valid_keys()),
            "jwt_algorithm": settings.jwt_algorithm,
            "api_key_db_file": settings.api_key_db_file
        }
    
    def get_system_config(self) -> Dict:
        """
        獲取系統配置
        
        Returns:
            dict: 系統配置信息
        """
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


# 全局 API Key 服務實例
api_key_service = ApiKeyService() 