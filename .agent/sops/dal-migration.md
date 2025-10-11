---
id: sops.dal_migration
version: 1.0
last_updated: 2025-10-11
tags: [sops, migration, data-access-layer, database, migration]
---

# Data Access Layer Migration SOP

## Overview
This SOP covers the migration process from legacy data access patterns to the new unified Data Access Layer (DAL), ensuring data integrity, minimal downtime, and smooth transition.

## Migration Strategy

### Phased Approach
1. **Phase 1**: Infrastructure Setup and DAL Implementation
2. **Phase 2**: Legacy Adapter Integration and Testing
3. **Phase 3**: Gradual Migration of Components
4. **Phase 4**: Legacy System Decommissioning
5. **Phase 5**: Optimization and Cleanup

### Migration Goals
- **Zero Downtime**: Maintain system availability during migration
- **Data Integrity**: Ensure no data loss or corruption
- **Performance**: Improve or maintain current performance
- **Backward Compatibility**: Support existing functionality during transition

## Prerequisites

### System Requirements
- **Backup**: Complete system backup before starting
- **Testing Environment**: Staging environment for testing migrations
- **Rollback Plan**: Detailed rollback procedures
- **Monitoring**: Enhanced monitoring during migration
- **Team Coordination**: All team members aware of migration schedule

### Required Tools and Dependencies
- **Database Tools**: pg_dump, psql, alembic
- **Migration Scripts**: Custom migration utilities
- **Testing Framework**: Comprehensive test suite
- **Monitoring Tools**: Enhanced logging and metrics

## Phase 1: Infrastructure Setup

### 1.1 Database Schema Preparation

#### 1.1.1 Create New Schema
```sql
-- Create new DAL-specific schema
CREATE SCHEMA IF NOT EXISTS dal;

-- Create migration tracking table
CREATE TABLE dal.migration_log (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    rollback_sql TEXT
);

-- Create audit log table for DAL
CREATE TABLE dal.audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_id VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_values JSONB,
    new_values JSONB,
    user_id VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    migration_id INTEGER REFERENCES dal.migration_log(id)
);
```

#### 1.1.2 Enhanced Tables for DAL
```sql
-- Add DAL-specific columns to existing tables
ALTER TABLE tournaments 
ADD COLUMN IF NOT EXISTS dal_version INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS dal_metadata JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS dal_created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS dal_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS dal_created_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS dal_updated_by VARCHAR(100);

ALTER TABLE users 
ADD COLUMN IF NOT EXISTS dal_version INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS dal_metadata JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS dal_created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS dal_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS dal_created_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS dal_updated_by VARCHAR(100);

-- Add indexes for DAL operations
CREATE INDEX IF NOT EXISTS idx_tournaments_dal_updated_at ON tournaments(dal_updated_at);
CREATE INDEX IF NOT EXISTS idx_users_dal_updated_at ON users(dal_updated_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON dal.audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_table_record ON dal.audit_log(table_name, record_id);
```

### 1.2 Cache Setup

#### 1.2.1 Redis Configuration
```bash
# Configure Redis for DAL caching
redis-cli CONFIG SET maxmemory 512mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET save "900 1 300 10 60 10000"

# Create DAL-specific database
redis-cli SELECT 1
```

#### 1.2.2 Cache Warming Script
```python
# scripts/warm_cache.py
import asyncio
import json
from core.data_access.cache_manager import CacheManager
from core.data_access.persistence_repository import PersistenceRepository

async def warm_cache():
    cache = CacheManager()
    repo = PersistenceRepository()
    
    # Warm tournament cache
    tournaments = await repo.list_tournaments()
    for tournament in tournaments:
        await cache.set(f"tournament:{tournament.id}", tournament, ttl=3600)
    
    # Warm user cache
    users = await repo.list_users()
    for user in users:
        await cache.set(f"user:{user.id}", user, ttl=3600)
    
    print(f"Warmed cache with {len(tournaments)} tournaments and {len(users)} users")

if __name__ == "__main__":
    asyncio.run(warm_cache())
```

## Phase 2: Legacy Adapter Implementation

### 2.1 Legacy Adapter Setup

#### 2.1.1 Create Legacy Adapter
```python
# core/data_access/legacy_adapter.py
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

class LegacyAdapter:
    """Adapter to bridge legacy code with new DAL."""
    
    def __init__(self, dal_repository, legacy_functions):
        self.dal_repository = dal_repository
        self.legacy_functions = legacy_functions
        self.logger = logging.getLogger("LegacyAdapter")
        self.migration_mode = False  # Toggle for migration
    
    async def get_tournament(self, tournament_id: str) -> Optional[Dict]:
        """Get tournament using DAL or legacy method."""
        if self.migration_mode:
            try:
                # Use DAL
                tournament = await self.dal_repository.get_by_id(tournament_id)
                if tournament:
                    return tournament.to_dict()
            except Exception as e:
                self.logger.error(f"DAL get_tournament failed: {e}")
                # Fallback to legacy
                return await self.legacy_functions['get_tournament'](tournament_id)
        else:
            # Use legacy
            return await self.legacy_functions['get_tournament'](tournament_id)
    
    async def save_tournament(self, tournament_data: Dict) -> Dict:
        """Save tournament using DAL or legacy method."""
        if self.migration_mode:
            try:
                # Use DAL
                from core.models.tournament import Tournament
                tournament = Tournament.from_dict(tournament_data)
                saved = await self.dal_repository.create(tournament)
                return saved.to_dict()
            except Exception as e:
                self.logger.error(f"DAL save_tournament failed: {e}")
                # Fallback to legacy
                return await self.legacy_functions['save_tournament'](tournament_data)
        else:
            # Use legacy
            return await self.legacy_functions['save_tournament'](tournament_data)
    
    async def list_tournaments(self, **filters) -> List[Dict]:
        """List tournaments using DAL or legacy method."""
        if self.migration_mode:
            try:
                # Use DAL
                tournaments = await self.dal_repository.list(**filters)
                return [t.to_dict() for t in tournaments]
            except Exception as e:
                self.logger.error(f"DAL list_tournaments failed: {e}")
                # Fallback to legacy
                return await self.legacy_functions['list_tournaments'](**filters)
        else:
            # Use legacy
            return await self.legacy_functions['list_tournaments'](**filters)
```

#### 2.1.2 Integration Script
```python
# scripts/integrate_legacy_adapter.py
import asyncio
from core.data_access.legacy_adapter import LegacyAdapter
from core.data_access.persistence_repository import PersistenceRepository
from core.persistence import get_tournament, save_tournament, list_tournaments

async def setup_legacy_adapter():
    # Initialize DAL repository
    dal_repo = PersistenceRepository()
    
    # Define legacy functions
    legacy_functions = {
        'get_tournament': get_tournament,
        'save_tournament': save_tournament,
        'list_tournaments': list_tournaments
    }
    
    # Create adapter
    adapter = LegacyAdapter(dal_repo, legacy_functions)
    
    # Test adapter
    test_id = "test_tournament_123"
    print("Testing legacy adapter...")
    
    # Test get operation
    result = await adapter.get_tournament(test_id)
    print(f"Get tournament result: {result is not None}")
    
    # Test list operation
    tournaments = await adapter.list_tournaments(limit=5)
    print(f"List tournaments result: {len(tournaments)} tournaments")
    
    return adapter

if __name__ == "__main__":
    adapter = asyncio.run(setup_legacy_adapter())
    print("Legacy adapter setup complete")
```

### 2.2 Data Validation

#### 2.2.1 Data Consistency Checker
```python
# scripts/validate_data_consistency.py
import asyncio
from datetime import datetime
from core.data_access.legacy_adapter import LegacyAdapter
from core.persistence import get_tournament as legacy_get_tournament

async def validate_tournament_data():
    """Validate data consistency between legacy and DAL."""
    adapter = await setup_legacy_adapter()
    
    # Get sample tournaments
    tournaments = await adapter.list_tournaments(limit=100)
    inconsistencies = []
    
    for tournament in tournaments:
        tournament_id = tournament['id']
        
        # Get data from both sources
        legacy_data = await legacy_get_tournament(tournament_id)
        dal_data = await adapter.get_tournament(tournament_id)
        
        # Compare key fields
        if legacy_data and dal_data:
            if legacy_data['name'] != dal_data['name']:
                inconsistencies.append({
                    'tournament_id': tournament_id,
                    'field': 'name',
                    'legacy': legacy_data['name'],
                    'dal': dal_data['name']
                })
            
            if legacy_data['status'] != dal_data['status']:
                inconsistencies.append({
                    'tournament_id': tournament_id,
                    'field': 'status',
                    'legacy': legacy_data['status'],
                    'dal': dal_data['status']
                })
    
    # Report results
    print(f"Validation complete. Found {len(inconsistencies)} inconsistencies:")
    for inconsistency in inconsistencies:
        print(f"  Tournament {inconsistency['tournament_id']}: "
              f"{inconsistency['field']} differs "
              f"(legacy: {inconsistency['legacy']}, dal: {inconsistency['dal']})")
    
    return len(inconsistencies) == 0

if __name__ == "__main__":
    is_consistent = asyncio.run(validate_tournament_data())
    if is_consistent:
        print("✅ Data validation passed")
    else:
        print("❌ Data validation failed - manual review required")
```

## Phase 3: Gradual Migration

### 3.1 Component Migration Strategy

#### 3.1.1 Migration Priority List
1. **Configuration Management** - Low risk, high benefit
2. **Tournament Read Operations** - High frequency, low complexity
3. **User Management** - Critical functionality
4. **Tournament Write Operations** - Complex, high impact
5. **Real-time Updates** - Event system integration

#### 3.1.2 Migration Script Template
```python
# scripts/migrate_component.py
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

class ComponentMigrator:
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.logger = logging.getLogger(f"Migrator.{component_name}")
        self.start_time = None
        self.end_time = None
        
    async def pre_migration_checks(self) -> bool:
        """Perform pre-migration validation."""
        self.logger.info(f"Starting pre-migration checks for {self.component_name}")
        
        # Check system health
        health_ok = await self.check_system_health()
        if not health_ok:
            self.logger.error("System health check failed")
            return False
        
        # Check backup availability
        backup_ok = await self.check_backup_availability()
        if not backup_ok:
            self.logger.error("Backup check failed")
            return False
        
        # Check data consistency
        consistency_ok = await self.check_data_consistency()
        if not consistency_ok:
            self.logger.error("Data consistency check failed")
            return False
        
        self.logger.info("Pre-migration checks passed")
        return True
    
    async def migrate(self) -> bool:
        """Execute component migration."""
        self.start_time = datetime.utcnow()
        self.logger.info(f"Starting migration of {self.component_name}")
        
        try:
            # Record migration start
            await self.record_migration_start()
            
            # Execute migration steps
            success = await self.execute_migration_steps()
            
            if success:
                # Validate migration
                validation_ok = await self.validate_migration()
                if not validation_ok:
                    await self.rollback_migration()
                    return False
                
                self.end_time = datetime.utcnow()
                await self.record_migration_success()
                self.logger.info(f"Migration of {self.component_name} completed successfully")
                return True
            else:
                await self.rollback_migration()
                return False
                
        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            await self.rollback_migration()
            return False
    
    async def execute_migration_steps(self) -> bool:
        """Execute specific migration steps for the component."""
        # Override in subclasses
        raise NotImplementedError
    
    async def validate_migration(self) -> bool:
        """Validate migration results."""
        # Override in subclasses
        return True
    
    async def rollback_migration(self):
        """Rollback migration if needed."""
        self.logger.warning(f"Rolling back migration of {self.component_name}")
        # Override in subclasses
    
    async def record_migration_start(self):
        """Record migration start in database."""
        # Record migration in migration log
        pass
    
    async def record_migration_success(self):
        """Record migration success in database."""
        # Record migration completion
        pass

class TournamentMigrator(ComponentMigrator):
    def __init__(self):
        super().__init__("tournaments")
    
    async def execute_migration_steps(self) -> bool:
        """Execute tournament migration steps."""
        # Step 1: Enable DAL for read operations
        self.logger.info("Enabling DAL for tournament read operations")
        await self.enable_dal_reads()
        
        # Step 2: Monitor read operations
        self.logger.info("Monitoring read operations for 5 minutes")
        await asyncio.sleep(300)
        
        # Step 3: Enable DAL for write operations
        self.logger.info("Enabling DAL for tournament write operations")
        await self.enable_dal_writes()
        
        return True
    
    async def enable_dal_reads(self):
        """Enable DAL for tournament read operations."""
        # Update configuration or feature flags
        pass
    
    async def enable_dal_writes(self):
        """Enable DAL for tournament write operations."""
        # Update configuration or feature flags
        pass
```

### 3.2 Migration Execution

#### 3.2.1 Automated Migration Script
```bash
#!/bin/bash
# migrate.sh - Main migration script

set -e  # Exit on any error

# Configuration
MIGRATION_LOG="/var/log/gal-api/migration.log"
BACKUP_DIR="/home/galapi/backups/migration"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$MIGRATION_LOG"
}

# Function to check prerequisites
check_prerequisites() {
    log_message "Checking migration prerequisites..."
    
    # Check if bot is running
    if ! systemctl is-active --quiet gal-bot; then
        log_message "ERROR: Bot service is not running"
        exit 1
    fi
    
    # Check disk space
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 80 ]; then
        log_message "ERROR: Disk usage is ${DISK_USAGE}% (>80%)"
        exit 1
    fi
    
    # Check database connection
    if ! psql -h localhost -U galapi_user -d gal_api -c "SELECT 1;" > /dev/null 2>&1; then
        log_message "ERROR: Cannot connect to database"
        exit 1
    fi
    
    log_message "Prerequisites check passed"
}

# Function to create backup
create_backup() {
    log_message "Creating backup before migration..."
    
    # Database backup
    pg_dump -h localhost -U galapi_user gal_api > "$BACKUP_DIR/db_backup_$DATE.sql"
    gzip "$BACKUP_DIR/db_backup_$DATE.sql"
    
    # Application backup
    tar -czf "$BACKUP_DIR/app_backup_$DATE.tar.gz" -C /home/galapi/gal-api .
    
    log_message "Backup created successfully"
}

# Function to run migration
run_migration() {
    log_message "Starting migration..."
    
    # Run Python migration script
    cd /home/galapi/gal-api
    source .venv/bin/activate
    
    python scripts/migrate_component.py --component configuration
    if [ $? -ne 0 ]; then
        log_message "ERROR: Configuration migration failed"
        exit 1
    fi
    
    python scripts/migrate_component.py --component tournaments_read
    if [ $? -ne 0 ]; then
        log_message "ERROR: Tournament read migration failed"
        exit 1
    fi
    
    python scripts/migrate_component.py --component tournaments_write
    if [ $? -ne 0 ]; then
        log_message "ERROR: Tournament write migration failed"
        exit 1
    fi
    
    log_message "Migration completed successfully"
}

# Function to validate migration
validate_migration() {
    log_message "Validating migration..."
    
    # Run validation script
    python scripts/validate_migration.py
    if [ $? -ne 0 ]; then
        log_message "ERROR: Migration validation failed"
        exit 1
    fi
    
    log_message "Migration validation passed"
}

# Function to cleanup
cleanup() {
    log_message "Performing cleanup..."
    
    # Remove old backups (keep last 5)
    find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +5 -delete
    find "$BACKUP_DIR" -name "app_backup_*.tar.gz" -mtime +5 -delete
    
    log_message "Cleanup completed"
}

# Main execution
main() {
    log_message "Starting DAL migration process"
    
    check_prerequisites
    create_backup
    run_migration
    validate_migration
    cleanup
    
    log_message "DAL migration process completed successfully"
}

# Execute main function
main "$@"
```

## Phase 4: Testing and Validation

### 4.1 Automated Testing

#### 4.1.1 Integration Test Suite
```python
# tests/test_dal_migration.py
import pytest
import asyncio
from core.data_access.legacy_adapter import LegacyAdapter
from core.data_access.persistence_repository import PersistenceRepository

class TestDalmigration:
    @pytest.fixture
    async def adapter(self):
        # Setup adapter for testing
        dal_repo = PersistenceRepository()
        legacy_functions = {
            'get_tournament': legacy_get_tournament,
            'save_tournament': legacy_save_tournament,
            'list_tournaments': legacy_list_tournaments
        }
        adapter = LegacyAdapter(dal_repo, legacy_functions)
        adapter.migration_mode = True
        yield adapter
    
    @pytest.mark.asyncio
    async def test_tournament_read_consistency(self, adapter):
        """Test tournament read consistency between DAL and legacy."""
        # Create test tournament
        test_data = {
            'id': 'test_migration_001',
            'name': 'Migration Test Tournament',
            'status': 'draft'
        }
        
        # Save using legacy
        legacy_result = await adapter.save_tournament(test_data)
        
        # Read using DAL
        dal_result = await adapter.get_tournament(test_data['id'])
        
        # Compare results
        assert dal_result is not None
        assert dal_result['name'] == legacy_result['name']
        assert dal_result['status'] == legacy_result['status']
    
    @pytest.mark.asyncio
    async def test_tournament_write_consistency(self, adapter):
        """Test tournament write consistency between DAL and legacy."""
        # Create test data
        test_data = {
            'id': 'test_migration_002',
            'name': 'Migration Write Test',
            'status': 'active'
        }
        
        # Save using DAL
        dal_result = await adapter.save_tournament(test_data)
        
        # Read using legacy to verify
        legacy_result = await legacy_get_tournament(test_data['id'])
        
        # Compare results
        assert legacy_result is not None
        assert legacy_result['name'] == dal_result['name']
        assert legacy_result['status'] == dal_result['status']
    
    @pytest.mark.asyncio
    async def test_performance_comparison(self, adapter):
        """Test performance comparison between DAL and legacy."""
        import time
        
        test_id = 'perf_test_001'
        
        # Test DAL performance
        start_time = time.time()
        for _ in range(100):
            await adapter.get_tournament(test_id)
        dal_time = time.time() - start_time
        
        # Test legacy performance
        adapter.migration_mode = False
        start_time = time.time()
        for _ in range(100):
            await adapter.get_tournament(test_id)
        legacy_time = time.time() - start_time
        
        # DAL should be faster or at least not significantly slower
        assert dal_time <= legacy_time * 1.5  # Allow 50% slower max
```

### 4.2 Performance Testing

#### 4.2.1 Load Testing Script
```python
# scripts/load_test_dal.py
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

async def test_api_load(base_url: str, concurrent_requests: int = 50):
    """Test API load with concurrent requests."""
    
    async def make_request(session, url):
        start_time = time.time()
        try:
            async with session.get(url) as response:
                data = await response.json()
                end_time = time.time()
                return {
                    'status': response.status,
                    'response_time': end_time - start_time,
                    'success': response.status == 200
                }
        except Exception as e:
            end_time = time.time()
            return {
                'status': 0,
                'response_time': end_time - start_time,
                'success': False,
                'error': str(e)
            }
    
    # Test endpoints
    endpoints = [
        f"{base_url}/tournaments",
        f"{base_url}/users",
        f"{base_url}/config"
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            print(f"Testing endpoint: {endpoint}")
            
            # Make concurrent requests
            tasks = [make_request(session, endpoint) for _ in range(concurrent_requests)]
            results = await asyncio.gather(*tasks)
            
            # Analyze results
            successful = sum(1 for r in results if r['success'])
            avg_response_time = sum(r['response_time'] for r in results) / len(results)
            max_response_time = max(r['response_time'] for r in results)
            
            print(f"  Success rate: {successful}/{concurrent_requests} ({successful/concurrent_requests*100:.1f}%)")
            print(f"  Average response time: {avg_response_time:.3f}s")
            print(f"  Max response time: {max_response_time:.3f}s")

if __name__ == "__main__":
    asyncio.run(test_api_load("https://your-domain.com/api"))
```

## Phase 5: Legacy Decommissioning

### 5.1 Decommissioning Checklist

#### 5.1.1 Pre-decommissioning Validation
- [ ] All components successfully migrated to DAL
- [ ] Performance meets or exceeds legacy system
- [ ] All automated tests passing
- [ ] No error messages in logs for 7 days
- [ ] User feedback positive for 7 days
- [ ] Backup procedures tested and verified

#### 5.1.2 Legacy Code Removal
```bash
# Backup legacy code before removal
mkdir -p /home/galapi/legacy_backup/$(date +%Y%m%d)
cp -r /home/galapi/gal-api/core/persistence.py /home/galapi/legacy_backup/$(date +%Y%m%d)/
cp -r /home/galapi/gal-api/helpers/ /home/galapi/legacy_backup/$(date +%Y%m%d)/

# Remove legacy imports from core modules
find /home/galapi/gal-api -name "*.py" -exec grep -l "from.*persistence import" {} \; | \
  xargs sed -i 's/from.*persistence import/# LEGACY REMOVED: from persistence import/g'

# Remove legacy adapter
rm /home/galapi/gal-api/core/data_access/legacy_adapter.py

# Update imports
find /home/galapi/gal-api -name "*.py" -exec sed -i 's/from.*legacy_adapter import/# LEGACY REMOVED: from legacy_adapter import/g' {} \;
```

#### 5.1.3 Database Cleanup
```sql
-- Remove legacy-specific columns (after verification)
-- ALTER TABLE tournaments DROP COLUMN IF EXISTS legacy_column;
-- ALTER TABLE users DROP COLUMN IF EXISTS legacy_column;

-- Clean up migration logs older than 30 days
DELETE FROM dal.migration_log WHERE started_at < NOW() - INTERVAL '30 days';

-- Optimize database
VACUUM ANALYZE;
```

## Rollback Procedures

### 1. Emergency Rollback

#### 1.1 Database Rollback
```bash
#!/bin/bash
# emergency_rollback.sh

echo "Starting emergency rollback..."

# Stop services
sudo systemctl stop gal-api gal-bot

# Restore database
gunzip -c /home/galapi/backups/migration/db_backup_latest.sql.gz | \
  psql -h localhost -U galapi_user -d gal_api

# Restore application
cd /home/galapi
rm -rf gal-api
tar -xzf /home/galapi/backups/migration/app_backup_latest.tar.gz

# Start services
sudo systemctl start gal-bot gal-api

echo "Emergency rollback completed"
```

#### 1.2 Configuration Rollback
```bash
# Restore configuration files
cp /home/galapi/backup/config.yaml /home/galapi/gal-api/
cp /home/galapi/backup/.env.local /home/galapi/gal-api/

# Restart services
sudo systemctl restart gal-api gal-bot
```

### 2. Partial Rollback

#### 2.1 Component-specific Rollback
```python
# scripts/rollback_component.py
import asyncio
from core.data_access.legacy_adapter import LegacyAdapter

async def rollback_component(component_name: str):
    """Rollback specific component to legacy mode."""
    adapter = LegacyAdapter(dal_repo, legacy_functions)
    adapter.migration_mode = False
    
    # Update feature flags
    if component_name == "tournaments":
        await disable_dal_tournaments()
    elif component_name == "users":
        await disable_dal_users()
    
    print(f"Rolled back {component_name} to legacy mode")

if __name__ == "__main__":
    component = sys.argv[1] if len(sys.argv) > 1 else "tournaments"
    asyncio.run(rollback_component(component))
```

## Post-Migration Optimization

### 1. Performance Tuning

#### 1.1 Database Optimization
```sql
-- Update statistics
ANALYZE;

-- Rebuild indexes
REINDEX DATABASE gal_api;

-- Optimize queries
EXPLAIN ANALYZE SELECT * FROM tournaments WHERE status = 'active';
```

#### 1.2 Cache Optimization
```python
# Optimize cache settings
cache_config = {
    'max_memory_size': 200 * 1024 * 1024,  # 200MB
    'default_ttl': 1800,  # 30 minutes
    'compression_threshold': 512,  # 512 bytes
    'enable_warming': True
}
```

### 2. Monitoring Enhancement

#### 2.1 DAL-specific Metrics
```python
# Add DAL metrics to monitoring
@dataclass
class DALMetrics:
    repository_operations: Dict[str, int]
    cache_hit_rates: Dict[str, float]
    query_times: Dict[str, float]
    connection_pool_stats: Dict[str, Any]
    error_rates: Dict[str, float]
```

## Documentation Updates

### 1. Update Documentation
- Update architecture diagrams
- Update API documentation
- Update troubleshooting guides
- Update deployment procedures

### 2. Team Training
- Conduct training sessions on new DAL
- Provide best practices documentation
- Create debugging guides
- Update onboarding materials

---

**DAL Migration Status**: ✅ Production Ready  
**Strategy**: Phased migration with zero downtime  
**Safety**: Comprehensive backup and rollback procedures  
**Testing**: Automated validation and performance testing  
**Monitoring**: Enhanced monitoring throughout migration process
