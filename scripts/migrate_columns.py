#!/usr/bin/env python3
"""
Migration script to move from config.yaml column assignments to the new persistence system.

Run this script once to migrate your configuration:
    python scripts/migrate_columns.py
"""

import asyncio
import logging
import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.migration import run_migration, get_migration_status


async def main():
    """
    Run the complete migration process.
    """
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("🚀 Starting Google Sheets column migration...")
    print("=" * 60)

    try:
        # Run migration
        results = await run_migration()

        print("\n✅ Migration completed!")
        print("=" * 60)

        # Show results
        print(f"📋 Results:")
        print(f"   - Migrated configurations: {len(results['migrated_guilds'])}")
        print(f"   - Failed configurations: {len(results['failed_guilds'])}")
        print(f"   - Validation errors: {len(results['validation_errors'])}")
        print(f"   - Config.yaml cleaned: {results['config_cleaned']}")

        if results['migrated_guilds']:
            print(f"\n📝 Successfully migrated:")
            for guild in results['migrated_guilds']:
                print(f"   - {guild}")

        if results['failed_guilds']:
            print(f"\n❌ Failed to migrate:")
            for error in results['failed_guilds']:
                print(f"   - {error}")

        if results['validation_errors']:
            print(f"\n⚠️ Validation errors:")
            for error in results['validation_errors']:
                print(f"   - {error}")

        # Show migration log
        status = get_migration_status()
        if status['log']:
            print(f"\n📄 Migration Log:")
            for entry in status['log'][-10:]:  # Show last 10 entries
                print(f"   - {entry}")

        print("\n" + "=" * 60)
        print("🎉 Migration process completed!")

        if results['config_cleaned']:
            print("✅ Config.yaml has been cleaned up (backup created)")
        else:
            print("⚠️ Config.yaml cleanup may have failed - check manually")

        print("\n💡 Next steps:")
        print("   1. Test the bot's sheet functionality")
        print("   2. Use /gal config edit to configure column mappings")
        print("   3. Verify registration and check-in work correctly")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        logging.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())