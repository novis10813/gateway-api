#!/usr/bin/env python3
"""
API Key 生成工具
"""
import secrets
import string
import argparse
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


def main():
    parser = argparse.ArgumentParser(description='生成 API Keys')
    parser.add_argument('-n', '--number', type=int, default=1, help='生成的 key 數量')
    parser.add_argument('-l', '--length', type=int, default=32, help='Key 長度')
    parser.add_argument('-p', '--prefix', type=str, default='', help='Key 前綴')
    parser.add_argument('-t', '--type', choices=['default', 'hex', 'urlsafe'], 
                       default='default', help='Key 類型')
    
    args = parser.parse_args()
    
    print(f"🔑 生成 {args.number} 個 API Key(s):")
    print("=" * 50)
    
    keys = []
    for i in range(args.number):
        if args.type == 'hex':
            key = generate_hex_key(args.length)
        elif args.type == 'urlsafe':
            key = generate_url_safe_key(args.length)
        else:
            key = generate_api_key(args.length, args.prefix)
        
        keys.append(key)
        print(f"{i+1:2d}. {key}")
    
    print("=" * 50)
    print("💡 使用建議:")
    print("1. 將這些 keys 添加到 .env 文件中:")
    print(f"   API_KEYS={','.join(keys)}")
    print("\n2. 或者直接設置環境變量:")
    print(f"   export API_KEYS='{','.join(keys)}'")
    print("\n3. 測試 API key:")
    print(f"   curl -H 'X-API-Key: {keys[0]}' https://novis.tplinkdns.com/auth/verify")


if __name__ == "__main__":
    main() 