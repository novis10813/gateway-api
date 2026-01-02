#!/usr/bin/env python3
"""
Migration script to migrate API keys from JSON file to PostgreSQL.

This script reads the existing api_keys.json file and creates corresponding
records in the PostgreSQL database with proper hashing.

Usage:
    python -m cli.migrate_to_postgres

Note: This script should be run once after deploying the new PostgreSQL setup.
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import settings
from db.database import db_manager
from repositories.api_key_repository import PostgresApiKeyRepository
from utils.hashing import generate_api_key


async def migrate_json_to_postgres(json_file: str = "api_keys.json"):
    """
    Migrate API keys from JSON file to PostgreSQL.
    
    Note: Since we can't reverse the hash, we'll create NEW keys for each
    existing entry. The old keys will no longer work after migration.
    
    For a production migration, you would need to:
    1. Inform users that keys will be rotated
    2. Generate new keys and distribute them
    3. Keep the legacy JSON fallback enabled during transition
    """
    json_path = Path(__file__).parent.parent / json_file
    
    if not json_path.exists():
        print(f"❌ JSON file not found: {json_path}")
        return
    
    # Load existing data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    api_keys = data.get("api_keys", {})
    
    if not api_keys:
        print("⚠️  No API keys found in JSON file")
        return
    
    print(f"📦 Found {len(api_keys)} API keys to migrate")
    print("=" * 60)
    
    # Initialize database
    await db_manager.init_db()
    
    migrated = 0
    skipped = 0
    new_keys = []
    
    async with db_manager.session() as session:
        repo = PostgresApiKeyRepository(session)
        
        for old_key, info in api_keys.items():
            name = info.get("name", "Unknown")
            service = info.get("service", "legacy")
            permissions = info.get("permissions", ["read"])
            is_active = info.get("is_active", True)
            
            # Skip inactive keys
            if not is_active:
                print(f"⏭️  Skipping inactive key: {name} ({service})")
                skipped += 1
                continue
            
            try:
                # Create new key with proper hashing
                raw_key, key_data = await repo.create(
                    name=name,
                    service=service,
                    permissions=permissions
                )
                
                new_keys.append({
                    "old_key_prefix": old_key[:8] + "..." if len(old_key) > 8 else old_key,
                    "new_key": raw_key,
                    "name": name,
                    "service": service
                })
                
                print(f"✅ Migrated: {name} ({service})")
                print(f"   New key: {raw_key}")
                migrated += 1
                
            except Exception as e:
                print(f"❌ Failed to migrate {name}: {e}")
    
    await db_manager.close()
    
    print("=" * 60)
    print(f"\n📊 Migration Summary:")
    print(f"   - Migrated: {migrated}")
    print(f"   - Skipped (inactive): {skipped}")
    print(f"   - Total: {len(api_keys)}")
    
    if new_keys:
        print("\n⚠️  IMPORTANT: New API keys have been generated!")
        print("   The old keys will NO LONGER WORK after you disable legacy mode.")
        print("   Please save these new keys and distribute them to your services:\n")
        
        # Save new keys to file
        output_file = Path(__file__).parent.parent / "migrated_keys.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "migrated_at": datetime.now().isoformat(),
                "keys": new_keys
            }, f, indent=2, ensure_ascii=False)
        
        print(f"   📁 New keys saved to: {output_file}")
        print("\n   After updating all services with new keys, set:")
        print("   USE_LEGACY_API_KEYS=false")


async def main():
    """Main entry point."""
    print("🔄 API Key Migration: JSON → PostgreSQL")
    print("=" * 60)
    
    # Check database connection
    try:
        await db_manager.init_db()
        print("✅ Database connection successful")
        await db_manager.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   Please ensure PostgreSQL is running and DATABASE_URL is set correctly")
        return
    
    # Run migration
    await migrate_json_to_postgres()


if __name__ == "__main__":
    asyncio.run(main())
