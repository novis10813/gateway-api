"""
Core configuration settings for gateway authentication service.

Contains all application settings using Pydantic BaseSettings.
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT 配置
    jwt_secret_key: str = "your-super-secret-jwt-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # API Key 配置 (向後兼容)
    api_keys: str = "your-secret,another-key"
    
    # API Key 數據庫配置
    api_key_db_file: str = "api_keys.json"
    use_legacy_api_keys: bool = False  # 是否同時支援舊的配置方式
    
    # PostgreSQL 資料庫配置
    database_url: str = "postgresql+asyncpg://gateway:gateway@localhost:5432/gateway_db"
    testing: bool = False
    
    # Rate Limit 配置
    rate_limit_requests_per_minute: int = 60
    rate_limit_window_seconds: int = 60
    
    # 快取配置
    cache_max_size: int = 1000
    cache_ttl_seconds: int = 300  # 5 分鐘
    
    # 服務配置
    debug: bool = False
    host: str = "0.0.0.0" 
    port: int = 8000
    
    # CORS 配置
    allowed_origins: str = "https://novis.tplinkdns.com"
    
    @property
    def api_keys_list(self) -> List[str]:
        """將 API keys 字符串轉換為列表（向後兼容）"""
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """將允許來源字符串轉換為列表"""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"


settings = Settings() 