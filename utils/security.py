"""
Security utilities for gateway authentication service.

Contains functions for generating API keys and other security-related operations.
"""
import secrets
import string
from typing import List


def generate_api_key(length: int = 32, prefix: str = "") -> str:
    """生成安全的 API key"""
    # 使用字母和數字
    alphabet = string.ascii_letters + string.digits
    
    # 生成隨機字符串
    random_part = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    if prefix:
        return f"{prefix}_{random_part}"
    return random_part


def generate_hex_key(length: int = 32) -> str:
    """生成十六進制格式的 API key"""
    return secrets.token_hex(length // 2)


def generate_url_safe_key(length: int = 32) -> str:
    """生成 URL 安全的 API key"""
    return secrets.token_urlsafe(length)[:length]


def generate_multiple_keys(count: int, length: int = 32, prefix: str = "", 
                          key_type: str = "default") -> List[str]:
    """生成多個 API keys"""
    keys = []
    for _ in range(count):
        if key_type == 'hex':
            key = generate_hex_key(length)
        elif key_type == 'urlsafe':
            key = generate_url_safe_key(length)
        else:
            key = generate_api_key(length, prefix)
        keys.append(key)
    return keys 