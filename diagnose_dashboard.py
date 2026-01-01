"""
Diagnose why dashboard shows nothing.
This script checks database and simulates dashboard queries.
"""

import sqlite3
import os
from datetime import datetime, timedelta

db_path = os.path.join('dashboard', 'dashboard.db')

if not os.path.exists(db_path):
    print(f"❌ Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=" * 70)
print("DASHBOARD DIAGNOSTICS")
print("=" * 70)

try:
    # ====================================
    # Check all recent submissions
    # ====================================
    print("\n[1] ALL RECENT SUBMISSIONS")
    print("-" * 70)
    
    cursor.execute("""
        SELECT 
            id,
            status,
            overall_confidence,
            created_at,
            validated_at,
            tournament_id,
            round_name
        FROM placement_submissions
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    all_subs = cursor.fetchall()
    
    if not all_subs:
        print("   ❌ No submissions found in database!")
    else:
        for sub in all_subs:
            (sid, status, conf, created, validated, tid, rid) = sub
            print(f"\n   📝 ID: {sid}")
            print(f"   📊 Status: {status}")
            print(f"   💯 Confidence: {conf / 100 if conf else 0:.1%}")
            print(f"   📅 Created: {created}")
            print(f"   ✅ Validated: {validated if validated else 'Never'}")
            print(f"   🏆 Tournament: {tid}")
            print(f"   🎯 Round: {rid}")
    
    # ====================================
    # Check what dashboard would see
    # ====================================
    print("\n[2] DASHBOARD ROUTER QUERY (What dashboard sees)")
    print("-" * 70)
    
    # Simulate dashboard router query:
    # WHERE status IN ('pending', 'pending_review')
    cursor.execute("""
        SELECT 
            id,
            status,
            overall_confidence,
            created_at
        FROM placement_submissions
        WHERE status IN ('pending', 'pending_review')
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    dashboard_subs = cursor.fetchall()
    
    print(f"   📊 Query: WHERE status IN ('pending', 'pending_review')")
    print(f"   🔍 Results found: {len(dashboard_subs)} submission(s)")
    
    if not dashboard_subs:
        print("\n   ❌ Dashboard query returns NOTHING!")
        print("   ⚠️  This is why dashboard is empty!")
        print("\n   💡 Possible reasons:")
        print("      1. Submissions have different status (not 'pending' or 'pending_review')")
        print("      2. Database has no submissions")
        print("      3. Submissions were rejected")
    else:
        for sub in dashboard_subs:
            (sid, status, conf, created) = sub
            print(f"\n   ✅ ID: {sid}")
            print(f"   📊 Status: {status}")
            print(f"   💯 Confidence: {conf / 100 if conf else 0:.1%}")
            print(f"   📅 Created: {created}")
    
    # ====================================
    # Count by status
    # ====================================
    print("\n[3] SUBMISSIONS BY STATUS")
    print("-" * 70)
    
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM placement_submissions
        GROUP BY status
        ORDER BY count DESC
    """)
    
    by_status = cursor.fetchall()
    
    if not by_status:
        print("   ❌ No submissions in database")
    else:
        for status, count in by_status:
            emoji = {
                'pending': '⏳',
                'pending_review': '👁️',
                'validated': '✅',
                'rejected': '❌',
                'processing': '🔄'
            }.get(status, '❓')
            
            is_visible = status in ('pending', 'pending_review')
            visible_mark = ' 👁️ (visible on dashboard)' if is_visible else ' 👻 (hidden on dashboard)'
            
            print(f"   {emoji} {status:20} {count:3} submissions{visible_mark}")
    
    # ====================================
    # Check for recent submissions (last 24 hours)
    # ====================================
    print("\n[4] SUBMISSIONS IN LAST 24 HOURS")
    print("-" * 70)
    
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM placement_submissions
        WHERE created_at > ?
    """, (cutoff,))
    
    recent_count = cursor.fetchone()[0]
    print(f"   📊 Created in last 24 hours: {recent_count} submission(s)")
    
    # ====================================
    # Check batch status
    # ====================================
    print("\n[5] RECENT BATCHES")
    print("-" * 70)
    
    cursor.execute("""
        SELECT 
            id,
            status,
            batch_size,
            completed_count,
            validated_count,
            error_count,
            average_confidence,
            started_at,
            completed_at
        FROM processing_batches
        ORDER BY started_at DESC
        LIMIT 5
    """)
    
    batches = cursor.fetchall()
    
    if not batches:
        print("   ❌ No batches found")
    else:
        for batch in batches:
            (bid, status, bsize, completed, validated, errors, conf, started, completed) = batch
            print(f"\n   📦 Batch ID: {bid}")
            print(f"   📊 Status: {status}")
            print(f"   📏 Size: {bsize}")
            print(f"   ✅ Completed: {completed}")
            print(f"   👁️ Validated: {validated}")
            print(f"   ❌ Errors: {errors}")
            print(f"   💯 Avg Confidence: {conf / 100 if conf else 0:.1%}")
            print(f"   🕐 Started: {started}")
            print(f"   ✨ Completed: {completed if completed else 'Never'}")
    
    # ====================================
    # Recommendations
    # ====================================
    print("\n[6] RECOMMENDATIONS")
    print("-" * 70)
    
    has_pending = any(status == 'pending' or status == 'pending_review' for status, _ in by_status)
    has_validated = any(status == 'validated' for status, _ in by_status)
    
    if not has_pending and not has_validated:
        print("   ⚠️  No submissions found in database")
        print("   💡 Upload some TFT screenshots to populate database")
    elif not has_pending and has_validated:
        print("   ℹ️  All submissions are validated")
        print("   💡 Check dashboard at /admin/placements/submissions?status=validated")
    elif has_pending:
        pending_count = sum(count for status, count in by_status if status in ('pending', 'pending_review'))
        print(f"   ✅ Found {pending_count} pending/review submissions")
        print("   💡 Dashboard should show these at /admin/placements/review")
        
        if len(dashboard_subs) == 0:
            print("\n   ⚠️  PROBLEM: Dashboard query returns nothing!")
            print("   💡 This means status filter isn't matching database values")
            print("   🔧 Check if router query matches actual status values")
    
    print("\n[7] NEXT STEPS")
    print("-" * 70)
    
    if len(dashboard_subs) > 0:
        print("   ✅ Dashboard query returns results")
        print("   💡 If dashboard still shows nothing, check:")
        print("      1. Frontend API call (browser dev tools)")
        print("      2. React component rendering")
        print("      3. Cache issues (hard refresh)")
    else:
        print("   ⚠️  Dashboard query returns nothing")
        print("   💡 Check router filter matches database status values")
        print("   🔧 Dashboard filters: status IN ('pending', 'pending_review')")
        print("   📊 Database statuses:", ", ".join([s for s, _ in by_status]))

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()

print("\n" + "=" * 70)
print("DIAGNOSTICS COMPLETE")
print("=" * 70)
