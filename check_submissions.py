"""
Quick script to check what's in the database.
Run this to see why dashboard is empty.
"""

import sqlite3
import os

db_path = os.path.join('dashboard', 'dashboard.db')

if not os.path.exists(db_path):
    print(f"Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 60)
print("PLACEMENT SUBMISSIONS IN DATABASE")
print("=" * 60)

try:
    # Get recent submissions
    cursor.execute("""
        SELECT 
            id,
            status,
            overall_confidence,
            tournament_id,
            round_name,
            created_at,
            validated_at
        FROM placement_submissions
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    submissions = cursor.fetchall()
    
    if not submissions:
        print("\n❌ No submissions found in database!")
        print("   Upload some TFT screenshots to populate the database.")
    else:
        print(f"\nFound {len(submissions)} recent submissions:\n")
        
        for sub in submissions:
            (sid, status, confidence, tid, rid, created, validated) = sub
            
            # Format status with emoji
            status_emoji = {
                'pending': '⏳',
                'pending_review': '👁️',
                'validated': '✅',
                'rejected': '❌'
            }.get(status, '❓')
            
            print(f"{status_emoji} ID: {sid}")
            print(f"   Status: {status}")
            print(f"   Confidence: {confidence / 100 if confidence else 0:.1%}")
            print(f"   Tournament: {tid}")
            print(f"   Round: {rid}")
            print(f"   Created: {created}")
            print(f"   Validated: {validated if validated else 'Never'}")
            print()
    
    # Count by status
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM placement_submissions
        GROUP BY status
    """)
    
    by_status = cursor.fetchall()
    
    print("=" * 60)
    print("SUBMISSIONS BY STATUS")
    print("=" * 60)
    
    for status, count in by_status:
        status_emoji = {
            'pending': '⏳',
            'pending_review': '👁️',
            'validated': '✅',
            'rejected': '❌'
        }.get(status, '❓')
        
        print(f"{status_emoji} {status}: {count}")
    
    print()
    print("💡 Tip: Dashboard only shows 'pending' and 'pending_review' submissions.")
    print("   Status 'rejected' won't show on review page.")

except Exception as e:
    print(f"❌ Error querying database: {e}")
finally:
    conn.close()
