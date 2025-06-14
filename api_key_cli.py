#!/usr/bin/env python3
"""
API Key 管理命令行工具
"""
import argparse
import json
import sys
from pathlib import Path
from api_key_manager import ApiKeyDB


def main():
    parser = argparse.ArgumentParser(description='API Key 管理工具')
    parser.add_argument('--db-file', default='api_keys.json', help='數據庫文件路徑')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 列出命令
    list_parser = subparsers.add_parser('list', help='列出 API Keys')
    list_parser.add_argument('--service', help='過濾特定服務')
    list_parser.add_argument('--show-all', action='store_true', help='顯示包括停用的 keys')
    
    # 添加命令
    add_parser = subparsers.add_parser('add', help='添加新的 API Key')
    add_parser.add_argument('--name', required=True, help='API Key 名稱')
    add_parser.add_argument('--service', required=True, help='服務名稱')
    add_parser.add_argument('--permissions', nargs='+', default=['read'], help='權限列表')
    add_parser.add_argument('--custom-key', help='自定義 Key（可選）')
    
    # 停用命令
    deactivate_parser = subparsers.add_parser('deactivate', help='停用 API Key')
    deactivate_parser.add_argument('--key', required=True, help='要停用的 API Key')
    
    # 驗證命令
    verify_parser = subparsers.add_parser('verify', help='驗證 API Key')
    verify_parser.add_argument('--key', required=True, help='要驗證的 API Key')
    verify_parser.add_argument('--permission', help='需要的權限')
    
    # 統計命令
    stats_parser = subparsers.add_parser('stats', help='顯示統計信息')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 初始化數據庫
    db = ApiKeyDB(args.db_file)
    
    try:
        if args.command == 'list':
            list_keys(db, args.service, not args.show_all)
        elif args.command == 'add':
            add_key(db, args.name, args.service, args.permissions, args.custom_key)
        elif args.command == 'deactivate':
            deactivate_key(db, args.key)
        elif args.command == 'verify':
            verify_key(db, args.key, args.permission)
        elif args.command == 'stats':
            show_stats(db)
    except Exception as e:
        print(f"❌ 錯誤: {e}", file=sys.stderr)
        sys.exit(1)


def list_keys(db: ApiKeyDB, service: str = None, active_only: bool = True):
    """列出 API Keys"""
    keys = db.list_api_keys(service, active_only)
    
    if not keys:
        print("📭 沒有找到匹配的 API Keys")
        return
    
    print(f"🔑 API Keys 列表 {'(僅活躍)' if active_only else '(包括停用)'}")
    print("-" * 80)
    
    for masked_key, info in keys.items():
        status = "✅ 活躍" if info.get('is_active', True) else "❌ 停用"
        print(f"Key: {masked_key}")
        print(f"  名稱: {info['name']}")
        print(f"  服務: {info['service']}")
        print(f"  權限: {', '.join(info['permissions'])}")
        print(f"  創建時間: {info['created_at']}")
        print(f"  最後使用: {info['last_used'] or '從未使用'}")
        print(f"  使用次數: {info['usage_count']}")
        print(f"  狀態: {status}")
        print("-" * 40)


def add_key(db: ApiKeyDB, name: str, service: str, permissions: list, custom_key: str = None):
    """添加新的 API Key"""
    result = db.add_api_key(name, service, permissions, custom_key)
    
    print("✅ API Key 創建成功!")
    print(f"🔑 API Key: {result['api_key']}")
    print(f"📝 名稱: {result['info']['name']}")
    print(f"🔧 服務: {result['info']['service']}")
    print(f"🔐 權限: {', '.join(result['info']['permissions'])}")
    print(f"📅 創建時間: {result['info']['created_at']}")
    print("\n⚠️  請妥善保存此 API Key，它不會再次顯示完整內容！")


def deactivate_key(db: ApiKeyDB, api_key: str):
    """停用 API Key"""
    success = db.deactivate_api_key(api_key)
    
    if success:
        print(f"✅ API Key {api_key[:8]}... 已成功停用")
    else:
        print(f"❌ 未找到 API Key: {api_key[:8]}...")
        sys.exit(1)


def verify_key(db: ApiKeyDB, api_key: str, required_permission: str = None):
    """驗證 API Key"""
    result = db.validate_api_key(api_key, required_permission)
    
    if result['valid']:
        print("✅ API Key 驗證成功!")
        print(f"📝 名稱: {result['name']}")
        print(f"🔧 服務: {result['service']}")
        print(f"🔐 權限: {', '.join(result['permissions'])}")
        if required_permission:
            print(f"✅ 權限 '{required_permission}' 驗證通過")
    else:
        print(f"❌ API Key 驗證失敗: {result['reason']}")
        sys.exit(1)


def show_stats(db: ApiKeyDB):
    """顯示統計信息"""
    all_keys = db.list_api_keys(active_only=False)
    active_keys = db.list_api_keys(active_only=True)
    
    # 按服務分組
    services = {}
    for key, info in all_keys.items():
        service = info['service']
        if service not in services:
            services[service] = {'total': 0, 'active': 0, 'usage': 0}
        services[service]['total'] += 1
        services[service]['usage'] += info.get('usage_count', 0)
        if info.get('is_active', True):
            services[service]['active'] += 1
    
    print("📊 API Key 統計信息")
    print("=" * 50)
    print(f"總 Keys: {len(all_keys)}")
    print(f"活躍 Keys: {len(active_keys)}")
    print(f"停用 Keys: {len(all_keys) - len(active_keys)}")
    print()
    
    print("📈 按服務分類:")
    for service, stats in services.items():
        print(f"  {service}:")
        print(f"    總數: {stats['total']}")
        print(f"    活躍: {stats['active']}")
        print(f"    總使用次數: {stats['usage']}")
    print()
    
    # 最活躍的 keys
    print("🔥 使用最頻繁的 Keys:")
    usage_sorted = sorted(all_keys.items(), 
                         key=lambda x: x[1].get('usage_count', 0), 
                         reverse=True)[:5]
    
    for masked_key, info in usage_sorted:
        if info.get('usage_count', 0) > 0:
            print(f"  {masked_key}: {info['usage_count']} 次 ({info['service']})")


if __name__ == "__main__":
    main() 