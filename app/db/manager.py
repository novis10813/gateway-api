#!/usr/bin/env python3
"""
Database manager for gateway authentication service.

API Key 管理模組，使用 JSON 文件作為簡單的數據庫
"""
import json
import secrets
import string
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import threading


class ApiKeyDB:
    def __init__(self, db_file: str = "api_keys.json"):
        self.db_file = Path(db_file)
        self._lock = threading.Lock()
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """確保數據庫文件存在"""
        if not self.db_file.exists():
            default_data = {
                "api_keys": {},
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }
            self._save_data(default_data)
    
    def _load_data(self) -> Dict:
        """載入數據"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"api_keys": {}, "metadata": {}}
    
    def _save_data(self, data: Dict):
        """保存數據"""
        with self._lock:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _save_data_unlocked(self, data: Dict):
        """保存數據（不加鎖）"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_api_key(self, name: str, service: str, permissions: List[str] = None, 
                   custom_key: str = None) -> Dict:
        """添加新的 API Key"""
        data = self._load_data()
        
        # 生成 API Key
        if custom_key:
            api_key = custom_key
        else:
            # 生成格式：service_randomstring
            random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) 
                                for _ in range(24))
            api_key = f"{service}_{random_part}"
        
        # 檢查重複
        if api_key in data["api_keys"]:
            raise ValueError(f"API Key already exists: {api_key}")
        
        # 創建記錄
        key_info = {
            "name": name,
            "service": service,
            "permissions": permissions or ["read"],
            "created_at": datetime.now().isoformat(),
            "last_used": None,
            "is_active": True,
            "usage_count": 0
        }
        
        data["api_keys"][api_key] = key_info
        self._save_data(data)
        
        return {
            "api_key": api_key,
            "info": key_info
        }
    
    def get_api_key(self, api_key: str) -> Optional[Dict]:
        """獲取 API Key 信息"""
        data = self._load_data()
        return data["api_keys"].get(api_key)
    
    def list_api_keys(self, service: str = None, active_only: bool = True) -> Dict:
        """列出 API Keys"""
        data = self._load_data()
        result = {}
        
        for key, info in data["api_keys"].items():
            # 過濾條件
            if active_only and not info.get("is_active", True):
                continue
            if service and info.get("service") != service:
                continue
            
            # 隱藏部分 key 內容
            masked_key = key[:8] + "*" * (len(key) - 12) + key[-4:] if len(key) > 12 else "*" * len(key)
            result[masked_key] = {
                "name": info["name"],
                "service": info["service"],
                "permissions": info["permissions"],
                "created_at": info["created_at"],
                "last_used": info["last_used"],
                "usage_count": info["usage_count"]
            }
        
        return result
    
    def deactivate_api_key(self, api_key: str) -> bool:
        """停用 API Key"""
        data = self._load_data()
        if api_key in data["api_keys"]:
            data["api_keys"][api_key]["is_active"] = False
            data["api_keys"][api_key]["deactivated_at"] = datetime.now().isoformat()
            self._save_data(data)
            return True
        return False
    
    def validate_api_key(self, api_key: str, required_permission: str = None) -> Dict:
        """驗證 API Key 並更新使用記錄"""
        with self._lock:  # 🔧 整個操作加鎖
            data = self._load_data()
            key_info = data["api_keys"].get(api_key)
            
            if not key_info:
                return {"valid": False, "reason": "Key not found"}
            
            if not key_info.get("is_active", True):
                return {"valid": False, "reason": "Key deactivated"}
            
            # 檢查權限
            if required_permission:
                permissions = key_info.get("permissions", [])
                if required_permission not in permissions and "admin" not in permissions:
                    return {"valid": False, "reason": "Insufficient permissions"}
            
            # 更新使用記錄
            key_info["last_used"] = datetime.now().isoformat()
            key_info["usage_count"] = key_info.get("usage_count", 0) + 1
            data["api_keys"][api_key] = key_info
            self._save_data_unlocked(data)  # 🔧 使用不加鎖的版本
            
            return {
                "valid": True,
                "service": key_info["service"],
                "permissions": key_info["permissions"],
                "name": key_info["name"]
            }
    
    def get_all_valid_keys(self) -> List[str]:
        """獲取所有有效的 API Keys（用於向後兼容）"""
        data = self._load_data()
        return [key for key, info in data["api_keys"].items() 
                if info.get("is_active", True)]


# 全局實例 - 使用 config 中的設定
from core.config import settings
import os

# 使用當前檔案的目錄來確定絕對路徑
_current_dir = Path(__file__).parent.parent  # app/ 目錄
_db_path = _current_dir / settings.api_key_db_file
api_key_db = ApiKeyDB(str(_db_path))


def migrate_from_config(config_keys: List[str]):
    """從配置文件遷移現有的 API Keys"""
    for i, key in enumerate(config_keys):
        try:
            api_key_db.add_api_key(
                name=f"Legacy Key {i+1}",
                service="legacy",
                permissions=["admin"],
                custom_key=key
            )
            print(f"✅ Migrated legacy key: {key[:8]}...")
        except ValueError:
            print(f"⚠️  Key already exists: {key[:8]}...")


if __name__ == "__main__":
    # 測試代碼
    print("🔑 API Key Manager Test")
    
    # 添加測試 key
    result = api_key_db.add_api_key(
        name="WebDAV Service",
        service="webdav",
        permissions=["read", "write"]
    )
    print(f"Created: {result['api_key']}")
    
    # 驗證 key
    validation = api_key_db.validate_api_key(result['api_key'], "read")
    print(f"Validation: {validation}")
    
    # 列出 keys
    keys = api_key_db.list_api_keys()
    print(f"Keys: {keys}") 