#!/usr/bin/env python3
"""
內部管理客戶端 - 用於管理 API Keys 和查看內部狀態
僅能在內部網路中使用
"""
import httpx
import argparse
import json
import sys
from typing import Optional


class InternalClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=30.0)
    
    def get_status(self):
        """獲取內部服務狀態"""
        try:
            response = self.client.get(f"{self.base_url}/internal/status")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            return {"error": f"Request failed: {e}"}
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    
    def generate_api_key(self, name: Optional[str] = None, prefix: str = "", 
                        length: int = 32, key_type: str = "default"):
        """生成新的 API Key"""
        try:
            data = {
                "name": name,
                "prefix": prefix,
                "length": length,
                "key_type": key_type
            }
            response = self.client.post(f"{self.base_url}/internal/generate-api-key", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            return {"error": f"Request failed: {e}"}
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    
    def list_api_keys(self):
        """列出當前的 API Keys (遮掩版本)"""
        try:
            response = self.client.get(f"{self.base_url}/internal/list-api-keys")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            return {"error": f"Request failed: {e}"}
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    
    def get_config(self):
        """獲取內部配置資訊"""
        try:
            response = self.client.get(f"{self.base_url}/internal/config")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            return {"error": f"Request failed: {e}"}
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}


def main():
    parser = argparse.ArgumentParser(description='內部管理客戶端')
    parser.add_argument('--url', default='http://localhost:8000', help='FastAPI 服務 URL')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 狀態命令
    subparsers.add_parser('status', help='查看服務狀態')
    
    # 生成 API key 命令
    gen_parser = subparsers.add_parser('generate', help='生成新的 API Key')
    gen_parser.add_argument('-n', '--name', help='API Key 名稱')
    gen_parser.add_argument('-p', '--prefix', default='', help='API Key 前綴')
    gen_parser.add_argument('-l', '--length', type=int, default=32, help='API Key 長度')
    gen_parser.add_argument('-t', '--type', choices=['default', 'hex', 'urlsafe'], 
                           default='default', help='API Key 類型')
    
    # 列出 API keys 命令
    subparsers.add_parser('list', help='列出當前的 API Keys')
    
    # 配置命令
    subparsers.add_parser('config', help='查看配置資訊')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    client = InternalClient(args.url)
    
    if args.command == 'status':
        result = client.get_status()
        print("📊 服務狀態:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == 'generate':
        result = client.generate_api_key(
            name=args.name,
            prefix=args.prefix,
            length=args.length,
            key_type=args.type
        )
        if 'error' in result:
            print(f"❌ 錯誤: {result['error']}")
            sys.exit(1)
        else:
            print("🔑 API Key 生成成功!")
            print(f"Key: {result['api_key']}")
            print(f"名稱: {result.get('name', 'N/A')}")
            print(f"創建時間: {result['created_at']}")
            print(f"訊息: {result['message']}")
            print("\n💡 記得將此 Key 添加到您的 .env 文件中!")
    
    elif args.command == 'list':
        result = client.list_api_keys()
        if 'error' in result:
            print(f"❌ 錯誤: {result['error']}")
            sys.exit(1)
        else:
            print("📋 當前 API Keys:")
            print(f"總數: {result['total_keys']}")
            for i, key in enumerate(result['masked_keys'], 1):
                print(f"{i:2d}. {key}")
            print(f"\n💡 {result['note']}")
    
    elif args.command == 'config':
        result = client.get_config()
        if 'error' in result:
            print(f"❌ 錯誤: {result['error']}")
            sys.exit(1)
        else:
            print("⚙️  內部配置:")
            print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main() 