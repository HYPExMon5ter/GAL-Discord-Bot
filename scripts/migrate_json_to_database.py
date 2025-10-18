#!/usr/bin/env python3
"""
JSON to Database Migration Script

Migrates all JSON file storage to the unified database storage system.
Creates backups before migration and validates data integrity after migration.
"""

import json
import logging
import os
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.storage_service import get_storage_service, StorageError


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('migration.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


class JSONToDatabaseMigrator:
    """Handles migration of JSON files to unified database storage."""
    
    def __init__(self):
        self.storage_service = get_storage_service()
        self.project_root = project_root
        self.backup_dir = project_root / "storage" / "migration_backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # JSON files to migrate
        self.json_files = {
            "persisted_views": project_root / "persisted_views.json",
            "waitlist_data": project_root / "waitlist_data.json"
        }
        
        self.migration_log = {
            "start_time": datetime.now(UTC).isoformat(),
            "migrations": {},
            "errors": [],
            "success": False
        }
    
    def create_backup(self, file_path: Path) -> Optional[str]:
        """Create a backup of the JSON file."""
        if not file_path.exists():
            logging.info(f"No file to backup: {file_path}")
            return None
        
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_filename
        
        try:
            with open(file_path, 'r', encoding='utf-8') as src, \
                 open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
            
            logging.info(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logging.error(f"Failed to create backup for {file_path}: {e}")
            return None
    
    def load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse a JSON file."""
        if not file_path.exists():
            logging.info(f"File does not exist: {file_path}")
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logging.info(f"Loaded {len(data)} items from {file_path}")
            return data
            
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in {file_path}: {e}")
            return {}
        except Exception as e:
            logging.error(f"Failed to load {file_path}: {e}")
            return {}
    
    def migrate_persisted_views(self) -> bool:
        """Migrate persisted_views.json to database."""
        logging.info("Starting migration of persisted_views.json")
        
        file_path = self.json_files["persisted_views"]
        backup_path = self.create_backup(file_path)
        
        # Load existing data
        json_data = self.load_json_file(file_path)
        if not json_data:
            logging.info("No data to migrate for persisted_views")
            return True
        
        try:
            # Check if there's already data in the database
            existing_data = self.storage_service.get_persisted_views()
            
            if existing_data:
                logging.warning(f"Database already contains {len(existing_data)} persisted_views items")
                
                # Compare data and merge if necessary
                merged_data = {**existing_data, **json_data}
                
                if len(merged_data) > len(existing_data):
                    logging.info(f"Merging {len(merged_data) - len(existing_data)} new items")
                    self.storage_service.save_persisted_views(merged_data)
                else:
                    logging.info("Database data is current, no migration needed")
            else:
                # No existing data, import everything
                self.storage_service.save_persisted_views(json_data)
                logging.info(f"Imported {len(json_data)} persisted_views items")
            
            # Verify migration
            migrated_data = self.storage_service.get_persisted_views()
            if self.compare_data(json_data, migrated_data):
                logging.info("✅ persisted_views migration successful")
                self.migration_log["migrations"]["persisted_views"] = {
                    "success": True,
                    "items_migrated": len(json_data),
                    "backup_path": backup_path,
                    "verification": "passed"
                }
                return True
            else:
                logging.error("❌ persisted_views migration verification failed")
                self.migration_log["errors"].append("persisted_views verification failed")
                return False
                
        except Exception as e:
            logging.error(f"❌ persisted_views migration failed: {e}")
            self.migration_log["errors"].append(f"persisted_views migration error: {e}")
            return False
    
    def migrate_waitlist_data(self) -> bool:
        """Migrate waitlist_data.json to database."""
        logging.info("Starting migration of waitlist_data.json")
        
        file_path = self.json_files["waitlist_data"]
        backup_path = self.create_backup(file_path)
        
        # Load existing data
        json_data = self.load_json_file(file_path)
        if not json_data:
            logging.info("No data to migrate for waitlist_data")
            return True
        
        try:
            # Check if there's already data in the database
            existing_data = self.storage_service.get_waitlist_data()
            
            if existing_data:
                logging.warning(f"Database already contains data for {len(existing_data)} guilds")
                
                # Compare data and merge if necessary
                merged_data = {**existing_data, **json_data}
                
                if len(merged_data) > len(existing_data):
                    logging.info(f"Merging data for {len(merged_data) - len(existing_data)} new guilds")
                    self.storage_service.save_waitlist_data(merged_data)
                else:
                    logging.info("Database data is current, no migration needed")
            else:
                # No existing data, import everything
                self.storage_service.save_waitlist_data(json_data)
                logging.info(f"Imported waitlist data for {len(json_data)} guilds")
            
            # Verify migration
            migrated_data = self.storage_service.get_waitlist_data()
            if self.compare_data(json_data, migrated_data):
                logging.info("✅ waitlist_data migration successful")
                self.migration_log["migrations"]["waitlist_data"] = {
                    "success": True,
                    "guilds_migrated": len(json_data),
                    "backup_path": backup_path,
                    "verification": "passed"
                }
                return True
            else:
                logging.error("❌ waitlist_data migration verification failed")
                self.migration_log["errors"].append("waitlist_data verification failed")
                return False
                
        except Exception as e:
            logging.error(f"❌ waitlist_data migration failed: {e}")
            self.migration_log["errors"].append(f"waitlist_data migration error: {e}")
            return False
    
    def compare_data(self, original: Dict[str, Any], migrated: Dict[str, Any]) -> bool:
        """Compare original and migrated data for integrity verification."""
        if len(original) != len(migrated):
            logging.warning(f"Data length mismatch: original={len(original)}, migrated={len(migrated)}")
            return False
        
        # Check all keys exist and values match
        for key in original:
            if key not in migrated:
                logging.warning(f"Missing key in migrated data: {key}")
                return False
            
            # For complex structures, we need to do deep comparison
            if isinstance(original[key], dict) and isinstance(migrated[key], dict):
                if not self.deep_compare(original[key], migrated[key]):
                    logging.warning(f"Data mismatch for key: {key}")
                    return False
            elif original[key] != migrated[key]:
                logging.warning(f"Value mismatch for key {key}: original={original[key]}, migrated={migrated[key]}")
                return False
        
        return True
    
    def deep_compare(self, obj1: Any, obj2: Any) -> bool:
        """Deep comparison of two objects."""
        if type(obj1) != type(obj2):
            return False
        
        if isinstance(obj1, dict):
            if len(obj1) != len(obj2):
                return False
            for key in obj1:
                if key not in obj2 or not self.deep_compare(obj1[key], obj2[key]):
                    return False
            return True
        elif isinstance(obj1, list):
            if len(obj1) != len(obj2):
                return False
            for i in range(len(obj1)):
                if not self.deep_compare(obj1[i], obj2[i]):
                    return False
            return True
        else:
            return obj1 == obj2
    
    def cleanup_old_files(self) -> bool:
        """Remove old JSON files after successful migration."""
        logging.info("Cleaning up old JSON files")
        
        cleaned_files = []
        for name, file_path in self.json_files.items():
            if file_path.exists():
                try:
                    # Move to backup directory with a clear name
                    cleanup_name = f"{file_path.stem}_migrated_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
                    cleanup_path = self.backup_dir / cleanup_name
                    
                    file_path.rename(cleanup_path)
                    cleaned_files.append(str(cleanup_path))
                    logging.info(f"Moved {file_path} to {cleanup_path}")
                    
                except Exception as e:
                    logging.error(f"Failed to cleanup {file_path}: {e}")
                    self.migration_log["errors"].append(f"Cleanup failed for {file_path}: {e}")
                    return False
        
        if cleaned_files:
            logging.info(f"✅ Cleaned up {len(cleaned_files)} old JSON files")
            self.migration_log["cleanup"] = {
                "success": True,
                "files_moved": cleaned_files
            }
        
        return True
    
    def run_migration(self) -> bool:
        """Run the complete migration process."""
        logging.info("🚀 Starting JSON to database migration")
        
        try:
            # Get storage status before migration
            status = self.storage_service.get_storage_status()
            logging.info(f"Storage status: {status}")
            
            # Migrate each data type
            migrations_success = True
            
            migrations_success &= self.migrate_persisted_views()
            migrations_success &= self.migrate_waitlist_data()
            
            if migrations_success:
                # Cleanup old files
                cleanup_success = self.cleanup_old_files()
                
                if cleanup_success:
                    logging.info("🎉 Migration completed successfully!")
                    self.migration_log["success"] = True
                else:
                    logging.warning("⚠️ Migration completed but cleanup failed")
                    self.migration_log["success"] = True
                    self.migration_log["warnings"] = ["Cleanup failed"]
            else:
                logging.error("❌ Migration failed")
                self.migration_log["success"] = False
            
            # Save migration log
            self.save_migration_log()
            
            return self.migration_log["success"]
            
        except Exception as e:
            logging.error(f"❌ Migration failed with exception: {e}")
            self.migration_log["errors"].append(f"Migration exception: {e}")
            self.migration_log["success"] = False
            self.save_migration_log()
            return False
    
    def save_migration_log(self):
        """Save the migration log to a file."""
        self.migration_log["end_time"] = datetime.now(UTC).isoformat()
        
        log_filename = f"migration_log_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
        log_path = self.backup_dir / log_filename
        
        try:
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(self.migration_log, f, indent=2, ensure_ascii=False)
            logging.info(f"Migration log saved to: {log_path}")
        except Exception as e:
            logging.error(f"Failed to save migration log: {e}")


def main():
    """Main migration function."""
    setup_logging()
    
    logging.info("=" * 60)
    logging.info("JSON to Database Migration Script")
    logging.info("=" * 60)
    
    # Verify we're in the right directory
    if not (project_root / "bot.py").exists():
        logging.error("❌ This script must be run from the project root directory")
        sys.exit(1)
    
    # Create migrator and run migration
    migrator = JSONToDatabaseMigrator()
    success = migrator.run_migration()
    
    if success:
        logging.info("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        logging.error("❌ Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
