"""
Clear recent screenshot submissions from database.
Use this to test fresh processing without duplicate errors.
"""

import sqlite3
import os
from datetime import datetime, timedelta

db_path = os.path.join('dashboard', 'dashboard.db')

if not os.path.exists(db_path):
    print(f"Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Delete submissions from last 1 hour
    cursor.execute("""
        DELETE FROM placement_submissions
        WHERE created_at > datetime('now', '-1 hour')
    """)
    
    deleted = cursor.rowcount
    conn.commit()
    
    print(f"✅ Deleted {deleted} recent submission(s) from database")
    print("   Database is ready for fresh testing!")
    
except Exception as e:
    print(f"❌ Error clearing database: {e}")
    conn.rollback()
finally:
    conn.close()
