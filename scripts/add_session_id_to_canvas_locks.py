#!/usr/bin/env python3
"""
Migration script to add session_id column to canvas_locks table.

This script adds the session_id column to the CanvasLock model and
creates a backup of any existing locks before modifying the database.
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

def main():
    """Run the migration to add session_id column to canvas_locks table."""
    
    # Get the database path from dependencies.py or use default
    parent_dir = Path(__file__).parent.parent
    db_path = os.getenv("DATABASE_URL", "sqlite:///./dashboard/dashboard.db")
    
    # Handle different database URL formats
    if db_path.startswith("sqlite:///"):
        db_path = db_path[10:]  # Remove sqlite:///
    
    db_file = Path(parent_dir) / db_path
    if not db_file.exists():
        print(f"Database file not found at: {db_file}")
        return 1
    
    print(f"Migrating database: {db_file}")
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Check if session_id column already exists
        cursor.execute("PRAGMA table_info(canvas_locks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "session_id" in columns:
            print("session_id column already exists in canvas_locks table")
            return 0
        
        print("Adding session_id column to canvas_locks table...")
        
        # Create backup of existing locks
        cursor.execute("SELECT * FROM canvas_locks")
        existing_locks = cursor.fetchall()
        
        if existing_locks:
            print(f"Found {len(existing_locks)} existing locks")
            cursor.execute("""
                CREATE TABLE canvas_locks_backup AS 
                SELECT * FROM canvas_locks
            """)
            print("Created backup table: canvas_locks_backup")
        
        # Add session_id column
        cursor.execute("""
            ALTER TABLE canvas_locks 
            ADD COLUMN session_id TEXT
        """)
        
        # Generate temporary session IDs for existing locks
        if existing_locks:
            cursor.execute("""
                UPDATE canvas_locks 
                SET session_id = 'migrated_' || id || '_' || strftime('%s', 'now')
                WHERE session_id IS NULL
            """)
            print(f"Generated temporary session IDs for {len(existing_locks)} existing locks")
        
        # Create index on session_id for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_canvas_locks_session_id 
            ON canvas_locks(session_id)
        """)
        print("Created index on session_id column")
        
        # Commit changes
        conn.commit()
        print("Migration completed successfully!")
        
        return 0
        
    except Exception as e:
        print(f"Error during migration: {e}")
        return 1
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
