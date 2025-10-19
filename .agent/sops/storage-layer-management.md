---
id: sops.storage_layer_management
version: 1.0
last_updated: 2025-01-18
tags: [storage, database, management, backup, recovery, migration, 3-tier]
---

# Storage Layer Management SOP

## Overview

This SOP outlines the procedures for managing the Guardian Angel League bot's 3-tier storage system, which provides automatic fallback mechanisms ensuring data persistence and reliability across different deployment environments.

## Storage Architecture Overview

### Storage Tiers
1. **Primary Storage (PostgreSQL)**: Production-grade database
2. **Fallback Storage (SQLite)**: Development and offline scenarios  
3. **Emergency Storage (JSON Files)**: Legacy emergency fallback

### Storage Service Components
- **Storage Service** (`core/storage_service.py`): Unified storage abstraction
- **Connection Manager** (`core/data_access/connection_manager.py`): Database connections
- **Persistence Repository** (`core/data_access/persistence_repository.py`): Data access layer

## Daily Operations

### Storage Health Monitoring

#### System Health Check
**Frequency**: Every 15 minutes (automated)  
**Manual Check**: Daily at 9:00 AM

**Procedure**:
```python
from core.storage_service import get_storage_service

async def check_storage_health():
    """Comprehensive storage health check"""
    storage = get_storage_service()
    status = storage.get_storage_status()
    
    print(f"PostgreSQL Available: {status['postgres_available']}")
    print(f"SQLite Fallback: {status['sqlite_fallback']}")
    print(f"Persisted Views: {status['persisted_views_count']}")
    print(f"Waitlist Data: {status['waitlist_data_count']}")
    print(f"Last Backup: {status['last_backup']}")
    print(f"Connection Health: {status['connection_health']}")
    
    return status

# Run health check
import asyncio
asyncio.run(check_storage_health())
```

**Expected Output**:
```
PostgreSQL Available: True
SQLite Fallback: False
Persisted Views: 125
Waitlist Data: 8
Last Backup: 2025-01-18T09:00:00Z
Connection Health: healthy
```

#### Database Connection Monitoring
**Frequency**: Continuous (automated alerts)

**Key Metrics**:
- Connection pool utilization (<80% target)
- Query response times (<100ms average)
- Connection failure rate (<1%)
- Fallback activation frequency

**Monitoring Script**:
```python
import time
import asyncio
import logging
from core.data_access.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

async def monitor_connection_health():
    """Monitor database connection health"""
    conn_manager = ConnectionManager()
    
    while True:
        try:
            # Test connection
            start_time = time.time()
            async with conn_manager.get_connection() as conn:
                await conn.fetchval("SELECT 1")
            response_time = (time.time() - start_time) * 1000
            
            if response_time > 500:
                logger.warning(f"Slow database response: {response_time:.2f}ms")
            else:
                logger.info(f"Database healthy: {response_time:.2f}ms")
                
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            
        await asyncio.sleep(60)  # Check every minute
```

### Data Integrity Validation

#### Daily Integrity Check
**Frequency**: Daily at 2:00 AM

**Procedure**:
```python
from core.storage_service import get_storage_service

async def validate_data_integrity():
    """Validate storage data integrity"""
    storage = get_storage_service()
    
    # Run integrity validation
    validation_results = storage.validate_data_integrity()
    
    print(f"Validation Status: {validation_results['status']}")
    print(f"Records Validated: {validation_results['records_validated']}")
    print(f"Errors Found: {validation_results['errors_found']}")
    
    if validation_results['errors_found'] > 0:
        for error in validation_results['errors']:
            print(f"Error: {error}")
    
    return validation_results

# Run validation
import asyncio
asyncio.run(validate_data_integrity())
```

### Cache Management

#### Cache Performance Monitoring
**Frequency**: Every 30 minutes (automated)

**Procedure**:
```python
from core.data_access.cache_manager import CacheManager

async def monitor_cache_performance():
    """Monitor cache performance metrics"""
    cache = CacheManager()
    
    # Get cache statistics
    stats = await cache.get_stats()
    
    print(f"Cache Hit Rate: {stats['hit_rate']:.2%}")
    print(f"Cache Size: {stats['cache_size']}")
    print(f"Memory Usage: {stats['memory_usage_mb']:.2f}MB")
    print(f"Expired Entries: {stats['expired_entries']}")
    
    # Alert if performance degraded
    if stats['hit_rate'] < 0.8:
        print("⚠️ Cache hit rate below 80%")
    
    if stats['memory_usage_mb'] > 500:
        print("⚠️ Cache memory usage above 500MB")

# Run cache monitoring
import asyncio
asyncio.run(monitor_cache_performance())
```

## Weekly Operations

### Backup Management

#### Automated Backup Creation
**Frequency**: Weekly on Sunday at 3:00 AM

**Procedure**:
```python
from core.storage_service import get_storage_service
import datetime

async def create_weekly_backup():
    """Create weekly storage backup"""
    storage = get_storage_service()
    
    # Create backup
    backup_path = storage.backup_data()
    
    if backup_path:
        print(f"✅ Weekly backup created: {backup_path}")
        
        # Verify backup integrity
        if await verify_backup_integrity(backup_path):
            print("✅ Backup integrity verified")
        else:
            print("❌ Backup integrity check failed")
    else:
        print("❌ Backup creation failed")

async def verify_backup_integrity(backup_path: str) -> bool:
    """Verify backup file integrity"""
    try:
        import json
        
        # Load and validate backup
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        
        # Check required fields
        required_fields = ['timestamp', 'version', 'persisted_views', 'waitlist_data']
        if all(field in backup_data for field in required_fields):
            return True
        
    except Exception as e:
        print(f"Backup verification error: {e}")
    
    return False

# Run backup
import asyncio
asyncio.run(create_weekly_backup())
```

#### Backup Rotation and Cleanup
**Frequency**: Weekly

**Procedure**:
```bash
#!/bin/bash
# scripts/cleanup_old_backups.sh

BACKUP_DIR="/backup/gal/storage"
RETENTION_DAYS=30

# Remove old backups
find $BACKUP_DIR -name "storage_backup_*.json" -mtime +$RETENTION_DAYS -delete

# Compress backups older than 7 days
find $BACKUP_DIR -name "storage_backup_*.json" -mtime +7 -exec gzip {} \;

echo "Backup cleanup completed. Retained backups:"
ls -la $BACKUP_DIR
```

### Performance Optimization

#### Database Performance Review
**Frequency**: Every Monday at 10:00 AM

**Procedure**:
```sql
-- Connect to PostgreSQL database
-- Check slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
WHERE mean_time > 1000  -- queries taking more than 1 second
ORDER BY mean_time DESC
LIMIT 10;

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

#### Cache Optimization
**Frequency**: Weekly

**Procedure**:
```python
from core.data_access.cache_manager import CacheManager

async def optimize_cache_performance():
    """Optimize cache performance based on usage patterns"""
    cache = CacheManager()
    
    # Get cache analytics
    analytics = await cache.get_analytics()
    
    # Identify unused cache keys
    unused_keys = [
        key for key, stats in analytics.items()
        if stats['hit_count'] == 0 and stats['age_hours'] > 24
    ]
    
    # Clear unused cache entries
    for key in unused_keys:
        await cache.delete(key)
        print(f"Cleared unused cache key: {key}")
    
    # Adjust TTL for frequently accessed items
    hot_keys = [
        key for key, stats in analytics.items()
        if stats['hit_count'] > 100
    ]
    
    for key in hot_keys:
        await cache.set_ttl(key, 3600)  # Extend to 1 hour
        print(f"Extended TTL for hot key: {key}")

# Run optimization
import asyncio
asyncio.run(optimize_cache_performance())
```

## Monthly Operations

### Storage Capacity Planning

#### Storage Usage Analysis
**Frequency**: First of each month

**Procedure**:
```python
import os
import sqlite3
from pathlib import Path

async def analyze_storage_usage():
    """Analyze storage usage and capacity trends"""
    
    # SQLite usage
    sqlite_size = os.path.getsize('storage/fallback.db') if os.path.exists('storage/fallback.db') else 0
    
    # PostgreSQL usage (if available)
    postgres_size = await get_postgresql_size() if is_postgresql_available() else 0
    
    # JSON emergency storage
    json_size = 0
    json_dir = Path('storage/emergency')
    if json_dir.exists():
        for file in json_dir.glob('*.json'):
            json_size += file.stat().st_size
    
    total_size = sqlite_size + postgres_size + json_size
    
    print(f"Storage Usage Analysis:")
    print(f"SQLite: {format_bytes(sqlite_size)}")
    print(f"PostgreSQL: {format_bytes(postgres_size)}")
    print(f"JSON Emergency: {format_bytes(json_size)}")
    print(f"Total: {format_bytes(total_size)}")
    
    # Growth trend analysis
    await analyze_growth_trends(total_size)

def format_bytes(bytes_value: int) -> str:
    """Format bytes in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.2f} TB"

async def analyze_growth_trends(current_size: int):
    """Analyze storage growth trends"""
    # Implementation would compare with historical data
    # and project future storage needs
    pass

# Run analysis
import asyncio
asyncio.run(analyze_storage_usage())
```

#### Database Maintenance
**Frequency**: Monthly

**Procedure**:
```sql
-- PostgreSQL maintenance
VACUUM ANALYZE;  -- Update table statistics and reclaim space

-- Reindex fragmented indexes
REINDEX DATABASE CONCURRENTLY your_database_name;

-- Update table statistics
ANALYZE;

-- Check for unused indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Data Migration and Archival

#### Historical Data Archival
**Frequency**: Monthly

**Procedure**:
```python
from core.storage_service import get_storage_service
from datetime import datetime, timedelta

async def archive_historical_data():
    """Archive data older than 90 days"""
    storage = get_storage_service()
    
    # Calculate archive cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    
    # Archive old guild data
    archived_count = await storage.archive_guild_data_before(cutoff_date)
    
    print(f"Archived {archived_count} guild data entries")
    
    # Create archive index
    await storage.create_archive_index(cutoff_date)

# Run archival
import asyncio
asyncio.run(archive_historical_data())
```

## Maintenance Procedures

### Storage Tier Management

#### Primary Storage (PostgreSQL) Management

##### Connection Pool Configuration
```python
# core/data_access/connection_manager.py configuration
POSTGRESQL_CONFIG = {
    "min_connections": 2,
    "max_connections": 10,
    "connection_timeout": 30,
    "idle_timeout": 300,
    "max_lifetime": 3600,
    "retry_attempts": 3,
    "retry_delay": 1.0
}
```

##### Failover Testing
**Frequency**: Monthly

**Procedure**:
```python
async def test_postgresql_failover():
    """Test PostgreSQL failover to SQLite"""
    storage = get_storage_service()
    
    # Simulate PostgreSQL failure
    print("Simulating PostgreSQL failure...")
    await storage.simulate_postgresql_failure()
    
    # Verify fallback to SQLite
    status = storage.get_storage_status()
    assert status['sqlite_fallback'] == True
    print("✅ Successfully failed over to SQLite")
    
    # Test operations during fallback
    await test_storage_operations()
    
    # Restore PostgreSQL
    print("Restoring PostgreSQL connection...")
    await storage.restore_postgresql_connection()
    
    # Verify restoration
    status = storage.get_storage_status()
    assert status['postgres_available'] == True
    print("✅ PostgreSQL connection restored")

async def test_storage_operations():
    """Test storage operations during fallback"""
    storage = get_storage_service()
    
    # Test data operations
    test_data = {"test_key": "test_value"}
    await storage.save_persisted_views(test_data)
    
    retrieved_data = await storage.get_persisted_views()
    assert retrieved_data == test_data
    print("✅ Storage operations working correctly")

# Run failover test
import asyncio
asyncio.run(test_postgresql_failover())
```

#### Fallback Storage (SQLite) Management

##### Database Optimization
**Frequency**: Monthly

**Procedure**:
```bash
# SQLite database optimization
sqlite3 storage/fallback.db "VACUUM;"
sqlite3 storage/fallback.db "ANALYZE;"

# Check database integrity
sqlite3 storage/fallback.db "PRAGMA integrity_check;"

# Check foreign key constraints
sqlite3 storage/fallback.db "PRAGMA foreign_key_check;"
```

##### Size Management
```python
import sqlite3
import os

def manage_sqlite_size():
    """Monitor and manage SQLite database size"""
    db_path = 'storage/fallback.db'
    
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        
        print(f"SQLite database size: {size_mb:.2f} MB")
        
        if size_mb > 100:  # Alert if > 100MB
            print("⚠️ SQLite database getting large, consider cleanup")
            
            # Run cleanup
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Clear old log entries
            cursor.execute("DELETE FROM logs WHERE created_at < datetime('now', '-30 days')")
            conn.commit()
            
            # Vacuum to reclaim space
            cursor.execute("VACUUM")
            conn.close()
            
            new_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            print(f"Size after cleanup: {new_size_mb:.2f} MB")

# Run size management
manage_sqlite_size()
```

#### Emergency Storage (JSON) Management

##### JSON File Cleanup
**Frequency**: Weekly

**Procedure**:
```python
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

def cleanup_emergency_json_files():
    """Clean up old emergency JSON files"""
    emergency_dir = Path('storage/emergency')
    
    if not emergency_dir.exists():
        return
    
    cutoff_date = datetime.now() - timedelta(days=7)
    cleaned_count = 0
    
    for json_file in emergency_dir.glob('*.json'):
        file_time = datetime.fromtimestamp(json_file.stat().st_mtime)
        
        if file_time < cutoff_date:
            try:
                json_file.unlink()
                cleaned_count += 1
                print(f"Removed old emergency file: {json_file}")
            except Exception as e:
                print(f"Error removing {json_file}: {e}")
    
    print(f"Cleaned up {cleaned_count} emergency JSON files")

# Run cleanup
cleanup_emergency_json_files()
```

## Backup and Recovery Procedures

### Comprehensive Backup Strategy

#### Full System Backup
**Frequency**: Daily (automated)  
**Scope**: All storage layers, configuration files

**Backup Script**:
```bash
#!/bin/bash
# scripts/full_storage_backup.sh

BACKUP_DIR="/backup/gal/$(date +%Y%m%d)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

echo "Starting full storage backup..."

# 1. PostgreSQL backup (if available)
if command -v pg_dump &> /dev/null; then
    if [ ! -z "$DATABASE_URL" ]; then
        echo "Backing up PostgreSQL..."
        pg_dump $DATABASE_URL > $BACKUP_DIR/postgresql_$TIMESTAMP.sql
        gzip $BACKUP_DIR/postgresql_$TIMESTAMP.sql
    fi
fi

# 2. SQLite backup
if [ -f "storage/fallback.db" ]; then
    echo "Backing up SQLite..."
    cp storage/fallback.db $BACKUP_DIR/sqlite_$TIMESTAMP.db
    gzip $BACKUP_DIR/sqlite_$TIMESTAMP.db
fi

# 3. Emergency JSON backup
if [ -d "storage/emergency" ]; then
    echo "Backing up emergency JSON files..."
    tar -czf $BACKUP_DIR/emergency_$TIMESTAMP.tar.gz storage/emergency/
fi

# 4. Configuration backup
echo "Backing up configuration..."
tar -czf $BACKUP_DIR/config_$TIMESTAMP.tar.gz \
    config.yaml \
    .env \
    core/data_access/

# 5. Create backup manifest
cat > $BACKUP_DIR/backup_manifest_$TIMESTAMP.txt << EOF
Backup created: $(date)
Backup type: Full system backup
Components:
- PostgreSQL: $( [ -f "$BACKUP_DIR/postgresql_$TIMESTAMP.sql.gz" ] && echo "Yes" || echo "No" )
- SQLite: $( [ -f "$BACKUP_DIR/sqlite_$TIMESTAMP.db.gz" ] && echo "Yes" || echo "No" )
- Emergency JSON: $( [ -f "$BACKUP_DIR/emergency_$TIMESTAMP.tar.gz" ] && echo "Yes" || echo "No" )
- Configuration: Yes
EOF

echo "✅ Full backup completed: $BACKUP_DIR"
ls -la $BACKUP_DIR
```

#### Incremental Backup
**Frequency**: Every 4 hours

**Procedure**:
```python
from core.storage_service import get_storage_service
import json
from datetime import datetime

async def create_incremental_backup():
    """Create incremental backup of changed data"""
    storage = get_storage_service()
    
    # Get changes since last backup
    changes = await storage.get_changes_since_last_backup()
    
    if changes:
        # Create incremental backup
        backup_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "incremental",
            "changes": changes
        }
        
        # Save backup
        backup_path = f"backups/incremental_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        print(f"✅ Incremental backup created: {backup_path}")
        print(f"Changes backed up: {len(changes)}")
    else:
        print("No changes to backup")

# Run incremental backup
import asyncio
asyncio.run(create_incremental_backup())
```

### Recovery Procedures

#### Complete System Recovery
**Use Case**: System failure, data corruption  
**Recovery Time Objective**: 2 hours

**Recovery Script**:
```bash
#!/bin/bash
# scripts/recover_storage_system.sh

BACKUP_DIR=$1
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

echo "Starting storage system recovery from: $BACKUP_DIR"

# Stop all services
echo "Stopping services..."
pkill -f uvicorn
pkill -f "npm run dev"

# 1. Recover SQLite (most critical fallback)
if [ -f "$BACKUP_DIR/sqlite_*.db.gz" ]; then
    echo "Recovering SQLite database..."
    gunzip -c $BACKUP_DIR/sqlite_*.db.gz > storage/fallback.db
    echo "✅ SQLite recovered"
fi

# 2. Recover PostgreSQL (if available)
if [ -f "$BACKUP_DIR/postgresql_*.sql.gz" ]; then
    echo "Recovering PostgreSQL database..."
    gunzip -c $BACKUP_DIR/postgresql_*.sql.gz | psql $DATABASE_URL
    echo "✅ PostgreSQL recovered"
fi

# 3. Recover emergency JSON files
if [ -f "$BACKUP_DIR/emergency_*.tar.gz" ]; then
    echo "Recovering emergency JSON files..."
    tar -xzf $BACKUP_DIR/emergency_*.tar.gz
    echo "✅ Emergency JSON files recovered"
fi

# 4. Recover configuration
if [ -f "$BACKUP_DIR/config_*.tar.gz" ]; then
    echo "Backing up current configuration..."
    cp config.yaml config.yaml.backup.$TIMESTAMP
    
    echo "Recovering configuration..."
    tar -xzf $BACKUP_DIR/config_*.tar.gz
    echo "✅ Configuration recovered"
fi

# 5. Verify recovery
echo "Verifying recovery..."
python -c "
import asyncio
from core.storage_service import get_storage_service

async def verify():
    storage = get_storage_service()
    status = storage.get_storage_status()
    print(f'Storage status: {status}')
    
    # Test basic operations
    test_data = {'recovery_test': True}
    await storage.save_persisted_views(test_data)
    retrieved = await storage.get_persisted_views()
    
    if retrieved == test_data:
        print('✅ Storage operations verified')
    else:
        print('❌ Storage operations failed')

asyncio.run(verify())
"

# 6. Restart services
echo "Restarting services..."
python start_dashboard.py

echo "✅ Storage system recovery completed"
```

#### Partial Recovery

##### Single Guild Recovery
```python
from core.storage_service import get_storage_service

async def recover_guild_data(guild_id: str, backup_path: str):
    """Recover data for a specific guild"""
    storage = get_storage_service()
    
    # Load backup
    with open(backup_path, 'r') as f:
        backup_data = json.load(f)
    
    # Extract guild data
    guild_data = backup_data.get('persisted_views', {}).get(guild_id)
    waitlist_data = backup_data.get('waitlist_data', {}).get(guild_id)
    
    if guild_data:
        await storage.save_persisted_views({guild_id: guild_data})
        print(f"✅ Recovered persisted views for guild {guild_id}")
    
    if waitlist_data:
        await storage.save_waitlist_data({guild_id: waitlist_data})
        print(f"✅ Recovered waitlist data for guild {guild_id}")

# Usage
# asyncio.run(recover_guild_data("123456789", "backup_20250118.json"))
```

## Troubleshooting Guide

### Common Storage Issues

#### PostgreSQL Connection Issues

**Issue**: Connection refused or timeout
```
Error: could not connect to server: Connection refused
```

**Troubleshooting Steps**:
```bash
# 1. Check PostgreSQL service status
sudo systemctl status postgresql

# 2. Check network connectivity
telnet postgres_host 5432

# 3. Verify connection string
echo $DATABASE_URL

# 4. Test connection manually
psql $DATABASE_URL -c "SELECT 1;"

# 5. Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

**Solutions**:
```bash
# Restart PostgreSQL
sudo systemctl restart postgresql

# Update connection configuration
# Edit config.yaml or environment variables
export DATABASE_URL="<your_postgresql_connection_string>"
```

#### SQLite Database Corruption

**Issue**: Database disk image is malformed
```
Error: database disk image is malformed
```

**Troubleshooting Steps**:
```bash
# 1. Check database integrity
sqlite3 storage/fallback.db "PRAGMA integrity_check;"

# 2. Try to recover data
sqlite3 storage/fallback.db ".recover" | sqlite3 recovery.db

# 3. Export data if possible
sqlite3 storage/fallback.db ".dump" > backup.sql

# 4. Check file permissions
ls -la storage/fallback.db
```

**Solutions**:
```bash
# Create fresh database from backup
cp storage/fallback.db storage/fallback.db.corrupt
sqlite3 storage/fallback.db "VACUUM;"

# If corruption persists, restore from backup
cp backups/latest_sqlite_backup.db storage/fallback.db
```

#### Cache Performance Issues

**Issue**: High memory usage, slow cache operations

**Diagnosis**:
```python
from core.data_access.cache_manager import CacheManager

async def diagnose_cache_issues():
    """Diagnose cache performance issues"""
    cache = CacheManager()
    
    # Get detailed statistics
    stats = await cache.get_detailed_stats()
    
    print(f"Cache entries: {stats['total_entries']}")
    print(f"Memory usage: {stats['memory_usage_mb']:.2f} MB")
    print(f"Hit rate: {stats['hit_rate']:.2%}")
    print(f"Expired entries: {stats['expired_entries']}")
    print(f"Large entries: {len(stats['large_entries'])}")
    
    # Identify problematic entries
    for entry in stats['large_entries']:
        print(f"Large entry: {entry['key']} ({entry['size_kb']:.1f} KB)")

# Run diagnosis
import asyncio
asyncio.run(diagnose_cache_issues())
```

**Solutions**:
```python
# Clear problematic cache entries
async def cleanup_cache():
    cache = CacheManager()
    
    # Clear expired entries
    await cache.cleanup_expired()
    
    # Clear large entries
    stats = await cache.get_detailed_stats()
    for entry in stats['large_entries']:
        if entry['size_kb'] > 100:  # > 100KB
            await cache.delete(entry['key'])
            print(f"Cleared large cache entry: {entry['key']}")
    
    # Force garbage collection
    import gc
    gc.collect()

# Run cleanup
import asyncio
asyncio.run(cleanup_cache())
```

### Emergency Procedures

#### Complete Storage Failure

**Symptoms**:
- All storage layers unavailable
- Data not persisting
- Services failing to start

**Immediate Response**:
```bash
# 1. Activate emergency mode
export STORAGE_EMERGENCY_MODE=true

# 2. Create memory-only storage
python -c "
from core.storage_service import get_storage_service
import asyncio

async def emergency_init():
    storage = get_storage_service()
    await storage.initialize_emergency_mode()
    print('Emergency storage initialized')

asyncio.run(emergency_init())
"

# 3. Start services in emergency mode
python start_dashboard.py

# 4. Notify administrators
echo "🚨 STORAGE SYSTEM FAILURE - EMERGENCY MODE ACTIVATED" | \
    mail -s "GAL Storage Alert" admin@example.com
```

**Recovery Steps**:
1. **Assess Damage**: Identify failed storage layers
2. **Restore Primary**: Attempt to recover PostgreSQL
3. **Fallback Recovery**: Restore SQLite if PostgreSQL fails
4. **Data Recovery**: Recover from backups if needed
5. **Service Verification**: Test all storage operations
6. **Monitor Stability**: Watch for recurrence

#### Data Corruption Detection

**Detection Script**:
```python
from core.storage_service import get_storage_service
import hashlib

async def detect_data_corruption():
    """Detect potential data corruption"""
    storage = get_storage_service()
    
    # Get all persisted data
    all_data = await storage.get_all_persisted_data()
    
    corruption_detected = False
    
    for guild_id, data in all_data.items():
        # Calculate checksums
        data_str = json.dumps(data, sort_keys=True)
        checksum = hashlib.md5(data_str.encode()).hexdigest()
        
        # Check for corruption indicators
        if not data or len(data_str) == 0:
            print(f"⚠️ Empty data detected for guild {guild_id}")
            corruption_detected = True
        
        if len(data_str) > 1000000:  # > 1MB
            print(f"⚠️ Unusually large data for guild {guild_id}: {len(data_str)} bytes")
            corruption_detected = True
        
        # Store checksum for comparison
        await storage.save_data_checksum(guild_id, checksum)
    
    if corruption_detected:
        print("❌ Data corruption detected - immediate action required")
        await send_corruption_alert()
    else:
        print("✅ No data corruption detected")

async def send_corruption_alert():
    """Send alert about data corruption"""
    # Implementation would send notification to administrators
    print("🚨 DATA CORRUPTION ALERT SENT TO ADMINISTRATORS")

# Run corruption detection
import asyncio
asyncio.run(detect_data_corruption())
```

## Performance Optimization

### Storage Performance Tuning

#### PostgreSQL Optimization
```sql
-- Connection pool optimization
ALTER SYSTEM SET max_connections = 100;
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET work_mem = '4MB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';

-- Apply changes
SELECT pg_reload_conf();

-- Create indexes for performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_persisted_views_guild_id 
ON persisted_views(guild_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_waitlist_data_guild_id 
ON waitlist_data(guild_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cache_expires_at 
ON cache(expires_at);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM persisted_views WHERE guild_id = '123456789';
```

#### SQLite Optimization
```bash
# SQLite optimization commands
sqlite3 storage/fallback.db << EOF
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;  -- 256MB
VACUUM;
ANALYZE;
EOF
```

#### Cache Performance Tuning
```python
# core/data_access/cache_manager.py optimization
CACHE_CONFIG = {
    "max_memory_mb": 512,
    "max_entries": 10000,
    "default_ttl": 3600,  # 1 hour
    "cleanup_interval": 300,  # 5 minutes
    "compression_threshold": 1024,  # Compress entries > 1KB
    "serialization": "json"  # Use JSON for faster serialization
}
```

### Monitoring and Alerting

#### Performance Metrics Collection
```python
import time
import asyncio
from typing import Dict, List

class StoragePerformanceMonitor:
    """Monitor storage performance metrics"""
    
    def __init__(self):
        self.metrics = []
    
    async def collect_metrics(self):
        """Collect storage performance metrics"""
        storage = get_storage_service()
        
        # Measure operation performance
        start_time = time.time()
        await storage.save_persisted_views({"test": "data"})
        save_time = time.time() - start_time
        
        start_time = time.time()
        await storage.get_persisted_views()
        load_time = time.time() - start_time
        
        # Collect system metrics
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "save_time_ms": save_time * 1000,
            "load_time_ms": load_time * 1000,
            "storage_type": storage.get_active_storage_type(),
            "cache_hit_rate": await storage.get_cache_hit_rate(),
            "connection_pool_size": await storage.get_connection_pool_size()
        }
        
        self.metrics.append(metrics)
        
        # Alert on performance degradation
        if save_time > 1.0:  # > 1 second
            await self.send_performance_alert("slow_save", metrics)
        
        if load_time > 0.5:  # > 500ms
            await self.send_performance_alert("slow_load", metrics)
    
    async def send_performance_alert(self, alert_type: str, metrics: Dict):
        """Send performance alert"""
        message = f"""
        🚨 Storage Performance Alert
        
        Alert Type: {alert_type}
        Timestamp: {metrics['timestamp']}
        Storage Type: {metrics['storage_type']}
        
        Save Time: {metrics['save_time_ms']:.2f}ms
        Load Time: {metrics['load_time_ms']:.2f}ms
        Cache Hit Rate: {metrics['cache_hit_rate']:.2%}
        
        Immediate investigation required.
        """
        
        # Send to monitoring system
        print(message)

# Usage
monitor = StoragePerformanceMonitor()
asyncio.run(monitor.collect_metrics())
```

---

**SOP Version**: 1.0  
**Last Updated**: 2025-01-18  
**Related Documentation**: [Storage Architecture](../system/storage-architecture.md), [Data Access Layer](../system/data-access-layer.md), [Database Migration SOP](../sops/database-migration-sop.md)
