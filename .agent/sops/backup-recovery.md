---
id: sops.backup_recovery
version: 1.0
last_updated: 2025-01-11
tags: [backup, recovery, disaster-recovery, sop]
---

# Backup and Recovery SOP

## Overview
Standard Operating Procedure for backing up and recovering Guardian Angel League Discord Bot and Live Graphics Dashboard systems.

## Backup Procedures

### Database Backups
**Frequency**: Daily automated, weekly verification
**Location**: `/backups/database/`
**Retention**: 30 days daily, 12 weeks weekly, 12 months monthly

```bash
# Automated backup script
./scripts/backup_database.sh
```

**Manual Backup**:
1. Access production server
2. Navigate to project directory
3. Execute backup script: `./scripts/backup_database.sh --manual`
4. Verify backup integrity: `./scripts/verify_backup.sh <backup_file>`

### Configuration Backups
**Files to backup**:
- `config.yaml`
- `.env.local`
- `.env` (non-sensitive portions)
- Google Sheets credentials
- Database schema and migrations

**Procedure**:
1. Stop services: `docker-compose down`
2. Backup configuration files
3. Archive: `tar -czf config_backup_$(date +%Y%m%d).tar.gz config/ .env*`
4. Store in secure location with encryption

### Code Repository Backups
- Git remote backups (GitHub, GitLab)
- Local mirror repositories
- Automated repository cloning to backup servers

## Recovery Procedures

### Database Recovery
**Scenario 1: Minor Corruption**
1. Stop all services
2. Restore from latest backup: `./scripts/restore_database.sh <backup_file>`
3. Verify data integrity
4. Restart services

**Scenario 2: Complete Loss**
1. Provision new database server
2. Restore from latest verified backup
3. Run data validation scripts
4. Update connection strings
5. Test all integrations

### Application Recovery
**Service Restoration**:
1. Restore code from repository
2. Rebuild containers: `docker-compose build --no-cache`
3. Restore configuration files
4. Update environment variables
5. Start services sequentially

### Data Verification
Post-recovery verification checklist:
- [ ] Database connectivity
- [ ] API endpoints responding
- [ ] Discord bot functionality
- [ ] Dashboard loading
- [ ] External integrations (Google Sheets, Riot API)
- [ ] Event system processing

## Emergency Contacts
- Database Administrator: [Contact Info]
- System Administrator: [Contact Info]
- Lead Developer: [Contact Info]

## Testing
**Monthly**: Test backup restoration procedures
**Quarterly**: Full disaster recovery drill
**Annually**: Complete system recovery test

## Dependencies
- [Data Access Layer](../system/data-access-layer.md) - Database structure
- [API Deployment SOP](./api-deployment.md) - Application deployment
- [Security SOP](./security.md) - Credential management
