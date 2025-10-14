---
id: sops.database-migration-sop
version: 1.0
last_updated: 2025-10-14
tags: [database, migration, schema, data-management, backup-recovery]
---

# Database Migration SOP

## Overview

This Standard Operating Procedure (SOP) outlines the formal process for database schema migrations, data migrations, and database updates in the Guardian Angel League Live Graphics Dashboard project. The process ensures data integrity, minimal downtime, and proper rollback capabilities.

## Scope

This SOP applies to:
- Database schema changes
- Data migration operations
- Database version upgrades
- Database configuration changes
- Backup and recovery operations
- Database performance optimization

## Migration Categories

### Schema Migrations
```sql
-- Schema migration types
-- 1. Table creation
CREATE TABLE new_table (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Table modification
ALTER TABLE existing_table 
ADD COLUMN new_column TEXT DEFAULT 'default_value';

-- 3. Index creation
CREATE INDEX idx_table_column ON table_name(column_name);

-- 4. Constraint addition
ALTER TABLE table_name 
ADD CONSTRAINT unique_constraint UNIQUE (column_name);
```

### Data Migrations
```python
# Data migration patterns
class DataMigration:
    def __init__(self, db_session):
        self.db = db_session
    
    def migrate_data(self):
        """Execute data migration"""
        # 1. Validate preconditions
        self.validate_preconditions()
        
        # 2. Create backup
        self.create_backup()
        
        # 3. Transform data
        self.transform_data()
        
        # 4. Validate results
        self.validate_results()
        
        # 5. Cleanup
        self.cleanup()
```

## Migration Process Workflow

### 1. Migration Planning

#### Requirements Analysis
```markdown
## Migration Requirements Document

### Migration Objectives
- Clear description of migration purpose
- Expected outcomes and benefits
- Success criteria definition

### Impact Assessment
- Affected tables and data
- Application impact analysis
- Downtime requirements
- Risk assessment

### Technical Requirements
- Database compatibility
- Performance requirements
- Storage requirements
- Rollback capabilities
```

#### Migration Design
```python
# Migration design template
class MigrationDesign:
    def __init__(self):
        self.migration_id = "migration_2025_10_14_001"
        self.description = "Add event_name to graphics table"
        self.prerequisites = []
        self.dependencies = []
        self.rollback_plan = ""
    
    def forward_migration(self):
        """Forward migration SQL"""
        return """
        ALTER TABLE graphics 
        ADD COLUMN event_name TEXT DEFAULT '';
        
        CREATE INDEX idx_graphics_event_name 
        ON graphics(event_name);
        """
    
    def rollback_migration(self):
        """Rollback migration SQL"""
        return """
        DROP INDEX IF EXISTS idx_graphics_event_name;
        ALTER TABLE graphics 
        DROP COLUMN IF EXISTS event_name;
        """
```

### 2. Migration Development

#### Migration File Structure
```python
# migrations/001_add_event_name_to_graphics.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers
revision = '001_add_event_name_to_graphics'
down_revision = '000_initial_schema'
branch_labels = None
depends_on = None

def upgrade():
    """Upgrade database schema"""
    # Add event_name column
    with op.batch_alter_table('graphics') as batch_op:
        batch_op.add_column(sa.Column('event_name', sa.Text(), nullable=True))
        batch_op.create_index('idx_graphics_event_name', ['event_name'], unique=False)

def downgrade():
    """Downgrade database schema"""
    with op.batch_alter_table('graphics') as batch_op:
        batch_op.drop_index('idx_graphics_event_name')
        batch_op.drop_column('event_name')
```

#### Migration Testing
```python
# Test migration procedures
class TestMigration:
    def test_migration_up(self):
        """Test forward migration"""
        # 1. Setup test database
        # 2. Run migration
        # 3. Validate schema changes
        # 4. Test application compatibility
    
    def test_migration_down(self):
        """Test rollback migration"""
        # 1. Setup migrated database
        # 2. Run rollback
        # 3. Validate rollback success
        # 4. Test application compatibility
    
    def test_data_integrity(self):
        """Test data integrity during migration"""
        # 1. Populate test data
        # 2. Run migration
        # 3. Validate data integrity
        # 4. Check data consistency
```

### 3. Migration Validation

#### Pre-Migration Validation
```python
# Pre-migration validation checklist
class PreMigrationValidation:
    def validate_database_state(self):
        """Validate current database state"""
        checks = [
            self.check_database_connectivity(),
            self.check_current_schema(),
            self.check_data_consistency(),
            self.check_disk_space(),
            self.check_backup_availability()
        ]
        return all(checks)
    
    def validate_prerequisites(self):
        """Validate migration prerequisites"""
        return {
            "application_compatibility": self.check_app_compatibility(),
            "backup_available": self.verify_backup_available(),
            "rollback_plan": self.verify_rollback_plan(),
            "maintenance_window": self.check_maintenance_window()
        }
```

#### Post-Migration Validation
```python
# Post-migration validation
class PostMigrationValidation:
    def validate_schema(self):
        """Validate migrated schema"""
        # Check new tables exist
        # Check modified tables correct
        # Check indexes created
        # Check constraints applied
        pass
    
    def validate_data(self):
        """Validate data integrity"""
        # Check data consistency
        # Check data completeness
        # Check data relationships
        # Check data accuracy
        pass
    
    def validate_application(self):
        """Validate application compatibility"""
        # Test application startup
        # Test critical workflows
        # Test API endpoints
        # Test user interfaces
        pass
```

## Deployment Procedures

### Staging Environment Testing

#### Staging Migration Process
```bash
# Staging environment migration process
1. Prepare staging database
   - Copy production database to staging
   - Verify staging environment ready
   - Schedule migration testing window

2. Execute migration on staging
   - Run migration scripts
   - Monitor execution
   - Validate results

3. Application testing on staging
   - Deploy updated application
   - Run integration tests
   - Perform user acceptance testing

4. Performance testing
   - Run performance benchmarks
   - Compare with baseline
   - Validate no performance regression
```

#### Staging Validation Checklist
```markdown
## Staging Migration Validation Checklist

### Migration Execution
- [ ] Migration scripts executed successfully
- [ ] No migration errors encountered
- [ ] Migration completed within expected time
- [ ] Rollback tested and working

### Schema Validation
- [ ] New schema matches design specifications
- [ ] All indexes created correctly
- [ ] All constraints applied correctly
- [ ] No schema inconsistencies

### Data Validation
- [ ] All data migrated correctly
- [ ] No data corruption or loss
- [ ] Data relationships maintained
- [ ] Data consistency verified

### Application Validation
- [ ] Application starts successfully
- [ ] All features working correctly
- [ ] API endpoints responding correctly
- [ ] User interfaces functioning properly
```

### Production Deployment

#### Production Migration Strategy
```python
# Production migration strategies
class MigrationStrategy:
    def rolling_migration(self):
        """Rolling migration strategy"""
        # 1. Prepare production environment
        # 2. Put application in maintenance mode
        # 3. Create production backup
        # 4. Execute migration
        # 5. Validate migration
        # 6. Bring application back online
        
    def blue_green_migration(self):
        """Blue-green migration strategy"""
        # 1. Prepare green environment
        # 2. Migrate green environment
        # 3. Test green environment
        # 4. Switch traffic to green
        # 5. Validate production operation
        # 6. Decommission blue environment
```

#### Production Migration Process
```bash
# Production migration execution
1. Pre-migration preparation
   - Verify backup available
   - Notify stakeholders
   - Prepare rollback plan
   - Assemble migration team

2. Migration execution
   - Put application in maintenance mode
   - Create final backup
   - Execute migration scripts
   - Monitor migration progress

3. Post-migration validation
   - Validate migration success
   - Test application functionality
   - Monitor system performance
   - Verify user experience

4. Go-live preparation
   - Bring application back online
   - Monitor system behavior
   - Validate user workflows
   - Confirm service restoration
```

## Backup and Recovery

### Backup Strategy

#### Pre-Migration Backup
```bash
# Comprehensive backup procedure
#!/bin/bash

# Database backup
sqlite3 dashboard.db ".backup dashboard_backup_$(date +%Y%m%d_%H%M%S).db"

# Application files backup
tar -czf application_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
    api/ dashboard/ config.yaml

# Configuration backup
cp config.yaml config_backup_$(date +%Y%m%d_%H%M%S).yaml

# Verify backup integrity
sqlite3 dashboard_backup_*.db "PRAGMA integrity_check;"
```

#### Backup Validation
```python
# Backup validation procedures
class BackupValidation:
    def validate_database_backup(self, backup_file):
        """Validate database backup integrity"""
        checks = [
            self.check_file_exists(backup_file),
            self.check_file_size(backup_file),
            self.check_database_integrity(backup_file),
            self.check_data_completeness(backup_file)
        ]
        return all(checks)
    
    def validate_restore_capability(self, backup_file):
        """Validate backup can be restored"""
        # Test restore on staging environment
        # Verify data integrity after restore
        # Validate application compatibility
        pass
```

### Recovery Procedures

#### Rollback Procedures
```python
# Database rollback procedures
class DatabaseRollback:
    def __init__(self, backup_file):
        self.backup_file = backup_file
    
    def execute_rollback(self):
        """Execute database rollback"""
        try:
            # 1. Stop application services
            self.stop_application()
            
            # 2. Restore database from backup
            self.restore_database()
            
            # 3. Restore application files if needed
            self.restore_application_files()
            
            # 4. Validate rollback success
            self.validate_rollback()
            
            # 5. Restart application services
            self.start_application()
            
        except Exception as e:
            # Handle rollback failure
            self.handle_rollback_failure(e)
    
    def validate_rollback(self):
        """Validate rollback success"""
        # Check database connectivity
        # Verify data integrity
        # Test application functionality
        pass
```

## Migration Monitoring

### Real-time Monitoring

#### Migration Metrics
```python
# Migration monitoring metrics
class MigrationMetrics:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.records_processed = 0
        self.errors = []
    
    def track_progress(self):
        """Track migration progress"""
        return {
            "elapsed_time": self.get_elapsed_time(),
            "records_processed": self.records_processed,
            "progress_percentage": self.calculate_progress(),
            "error_count": len(self.errors)
        }
    
    def track_performance(self):
        """Track migration performance"""
        return {
            "cpu_usage": self.get_cpu_usage(),
            "memory_usage": self.get_memory_usage(),
            "disk_io": self.get_disk_io(),
            "database_connections": self.get_db_connections()
        }
```

#### Alerting Configuration
```yaml
# Migration alerting configuration
migration_alerts:
  critical:
    - "Migration failure"
    - "Database connection loss"
    - "Data corruption detected"
    - "Migration timeout"
    
  warning:
    - "Performance degradation"
    - "Long running migration"
    - "High resource usage"
    - "Migration warnings"
    
  info:
    "Migration started"
    "Migration milestones"
    "Migration completed"
    "Performance metrics"
```

## Special Migration Scenarios

### Large Dataset Migrations

#### Batch Processing Strategy
```python
# Large dataset migration strategy
class LargeDatasetMigration:
    def __init__(self, batch_size=1000):
        self.batch_size = batch_size
    
    def migrate_in_batches(self):
        """Migrate data in batches to prevent timeouts"""
        offset = 0
        
        while True:
            # Process batch
            batch = self.get_batch(offset, self.batch_size)
            if not batch:
                break
                
            self.process_batch(batch)
            self.update_progress(offset)
            
            offset += self.batch_size
            
            # Pause to prevent resource exhaustion
            time.sleep(0.1)
```

### Zero-Downtime Migrations

#### Online Schema Changes
```python
# Zero-downtime migration strategy
class ZeroDowntimeMigration:
    def execute_online_migration(self):
        """Execute migration without downtime"""
        # Phase 1: Add new column as nullable
        self.add_nullable_column()
        
        # Phase 2: Backfill data in batches
        self.backfill_data()
        
        # Phase 3: Update application to use new column
        self.deploy_application_update()
        
        # Phase 4: Make column required (if needed)
        self.make_column_required()
        
        # Phase 5: Remove old column (if needed)
        self.remove_old_column()
```

## Documentation and Change Management

### Migration Documentation

#### Migration Record
```markdown
# Migration Record

## Migration Details
- **Migration ID**: 001_add_event_name_to_graphics
- **Date**: 2025-10-14
- **Author**: Development Team
- **Description**: Add event_name column to graphics table

## Technical Details
- **Database Type**: SQLite
- **Migration Type**: Schema modification
- **Affected Tables**: graphics
- **Estimated Duration**: 15 minutes
- **Downtime Required**: No

## Execution Details
- **Execution Time**: 2025-10-14 10:00 UTC
- **Duration**: 12 minutes
- **Success**: Yes
- **Issues**: None

## Validation Results
- **Schema Validation**: Passed
- **Data Validation**: Passed
- **Application Validation**: Passed
- **Performance Impact**: Minimal

## Rollback Information
- **Rollback Available**: Yes
- **Rollback Tested**: Yes
- **Rollback Time**: 8 minutes
```

### Change Management Integration

#### Change Request Process
```markdown
## Database Migration Change Request

### Request Information
- **Request ID**: CR-2025-001
- **Requester**: Development Team
- **Date**: 2025-10-10
- **Priority**: High

### Change Description
- **Change Type**: Database Schema Migration
- **Change Summary**: Add event_name column to graphics table
- **Business Justification**: Support event-based graphics organization

### Technical Details
- **Migration ID**: 001_add_event_name_to_graphics
- **Complexity**: Low
- **Risk Assessment**: Low
- **Testing Required**: Yes

### Approval
- **Technical Approval**: [X] Approved
- **Business Approval**: [X] Approved
- **Security Approval**: [X] Approved
```

## Roles and Responsibilities

### Migration Team

#### Database Administrator
- **Primary Responsibility**: Database migration execution
- **Tasks**:
  - Execute migration scripts
  - Monitor migration progress
  - Handle migration errors
  - Validate migration success

#### Application Developer
- **Primary Responsibility**: Application compatibility
- **Tasks**:
  - Develop migration scripts
  - Test application compatibility
  - Update application code
  - Validate application functionality

#### System Administrator
- **Primary Responsibility**: Infrastructure support
- **Tasks**:
  - Prepare server environment
  - Monitor system resources
  - Handle infrastructure issues
  - Support rollback procedures

#### QA Engineer
- **Primary Responsibility**: Migration testing
- **Tasks**:
  - Develop test cases
  - Execute migration tests
  - Validate migration results
  - Document test results

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-14  
**Related SOPs**: 
- [Backup Recovery](./backup-recovery.md)
- [Emergency Rollback](./emergency-rollback.md)
- [Integration Testing Procedures](./integration-testing-procedures.md)
