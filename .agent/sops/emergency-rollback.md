---
id: sops.emergency_rollback
version: 1.0
last_updated: 2025-01-11
tags: [emergency, rollback, disaster-recovery, sop]
---

# Emergency Rollback SOP

## Overview
Standard Operating Procedure for emergency rollback of Guardian Angel League systems when deployments cause critical issues.

## Rollback Triggers

### Critical Conditions (Immediate Rollback Required)
- Service downtime > 5 minutes
- Data corruption or loss
- Security vulnerabilities in production
- Complete system failure
- API error rate > 10%

### High Priority (Rollback within 30 minutes)
- Performance degradation > 50%
- Critical functionality broken
- User data access issues
- Integration failures

### Medium Priority (Rollback within 2 hours)
- Non-critical feature failures
- Minor performance issues
- UI/UX problems
- Non-essential integrations broken

## Pre-Rollback Assessment

### Step 1: Impact Analysis (5 minutes)
1. **Identify Affected Systems**
   - API Backend status
   - Database connectivity
   - Discord bot functionality
   - Dashboard accessibility
   - External integrations

2. **User Impact Assessment**
   - Number of affected users
   - Critical functionality affected
   - Data safety confirmation
   - Business impact evaluation

3. **Root Cause Identification**
   - Recent deployment changes
   - Infrastructure modifications
   - External service issues
   - Configuration changes

### Step 2: Rollback Decision (2 minutes)
**Rollback Approval Matrix**:
- **Critical**: Automatic approval, proceed immediately
- **High**: Team lead approval required
- **Medium**: Development team consensus
- **Low**: Schedule for maintenance window

## Rollback Procedures

### Option 1: Git Rollback (Code Changes)
**When to use**: Code deployment issues, feature failures

```bash
# Identify last known good commit
git log --oneline -10

# Rollback to previous stable version
git checkout <last_stable_commit_tag>

# Force push to main branch (emergency only)
git push origin main --force

# Redeploy services
docker-compose down
docker-compose up -d --build
```

### Option 2: Database Rollback
**When to use**: Database schema issues, data migration failures

```bash
# Identify migration to rollback
alembic history

# Rollback to previous migration
alembic downgrade <previous_migration_id>

# Verify data integrity
./scripts/verify_data_integrity.sh
```

### Option 3: Configuration Rollback
**When to use**: Configuration changes causing issues

1. **Environment Variables**:
   ```bash
   # Restore from backup
   cp /backups/config/.env.backup .env.local
   
   # Restart services
   docker-compose restart
   ```

2. **YAML Configuration**:
   ```bash
   # Restore config files
   git checkout HEAD~1 config.yaml
   
   # Reload configuration
   curl -X POST http://localhost:8000/config/reload
   ```

### Option 4: Container/Service Rollback
**When to use**: Container image issues, service failures

```bash
# List previous images
docker images | grep gal-bot

# Rollback to previous image tag
docker-compose down
sed -i 's/:latest/:v1.2.3/' docker-compose.yml
docker-compose up -d
```

## Rollback Verification

### Immediate Verification (5 minutes)
1. **Service Health Checks**:
   ```bash
   # API health check
   curl http://localhost:8000/health
   
   # Database connectivity
   curl http://localhost:8000/health/database
   
   # Event system status
   curl http://localhost:8000/health/events
   ```

2. **Critical Functionality Tests**:
   - Discord bot responsive
   - Dashboard loading
   - API endpoints responding
   - Database queries working

### Comprehensive Testing (15 minutes)
1. **User Journey Testing**:
   - Tournament creation/editing
   - User registration/login
   - Configuration management
   - Real-time updates

2. **Integration Testing**:
   - Google Sheets connectivity
   - Riot API integration
   - Event processing
   - Caching functionality

3. **Performance Validation**:
   - Response times within acceptable limits
   - Memory usage stable
   - Error rates normal
   - Resource utilization appropriate

## Post-Rollback Actions

### Stabilization (30 minutes)
1. **Monitor System Stability**:
   - Watch error rates
   - Monitor performance metrics
   - Check user feedback
   - Validate data integrity

2. **Communication**:
   - Notify team of rollback completion
   - Update status page if public-facing
   - Document rollback incident
   - Schedule post-mortem

### Root Cause Analysis
1. **Investigation**:
   - Analyze what went wrong
   - Review deployment process
   - Identify testing gaps
   - Document lessons learned

2. **Prevention**:
   - Update deployment procedures
   - Enhance testing coverage
   - Implement additional safeguards
   - Improve monitoring and alerting

## Emergency Contacts

### Primary Contact Chain
1. **On-call Engineer**: [Contact Info]
2. **Team Lead**: [Contact Info]
3. **System Administrator**: [Contact Info]
4. **Development Manager**: [Contact Info]

### Escalation Procedures
- **Level 1**: On-call engineer (response time: 15 minutes)
- **Level 2**: Team lead (response time: 30 minutes)
- **Level 3**: System admin (response time: 1 hour)

## Rollback Testing

### Monthly Rollback Drills
1. Simulate rollback scenario
2. Test rollback procedures
3. Verify rollback effectiveness
4. Update documentation based on findings

### Deployment Validation
1. Pre-deployment rollback plan
2. Automated rollback testing
3. Health check validation
4. Performance baseline verification

## Documentation Requirements

### Rollback Log Entry
- Timestamp and trigger
- Systems affected
- Rollback method used
- Root cause analysis
- Prevention measures
- Lessons learned

### Incident Report
- Executive summary
- Detailed timeline
- Impact assessment
- Resolution steps
- Follow-up actions

## Dependencies
- [Deployment SOP](./deployment.md) - Deployment procedures
- [Troubleshooting SOP](./troubleshooting.md) - Issue resolution
- [API Deployment SOP](./api-deployment.md) - API specific procedures
- [Backup and Recovery SOP](./backup-recovery-sop.md) - Data recovery
