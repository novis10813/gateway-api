import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT 配置
    jwt_secret_key: str = "your-super-secret-jwt-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # API Key 配置
    api_keys: str = "your-secret"
    
    # 服務配置
    debug: bool = False
    host: str = "0.0.0.0" 
    port: int = 8000
    
    # CORS 配置
    allowed_origins: str = "https://novis.tplinkdns.com"
    
    @property
    def api_keys_list(self) -> List[str]:
        """將 API keys 字符串轉換為列表"""
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """將允許來源字符串轉換為列表"""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"


settings = Settings() 