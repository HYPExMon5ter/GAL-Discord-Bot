---
id: sops.ign_verification_management
version: 1.0
last_updated: 2025-01-18
tags: [ign, verification, riot-api, discord-bot, user-registration, service-management]
---

# IGN Verification Management SOP

## Overview

This SOP outlines the procedures for managing the IGN (In-Game Name) verification system that integrates with the Riot Games API to validate League of Legends player accounts during user registration in the Guardian Angel League Discord bot.

## System Components

### 1. Dashboard IGN Verification Service
**Location**: `api/routers/ign_verification.py`  
**Purpose**: FastAPI service providing IGN verification endpoints  
**Endpoints**:
- `POST /api/v1/ign-verification/verify` - Verify IGN validity
- `GET /api/v1/ign-verification/health` - Service health check
- `GET /api/v1/ign-verification/stats` - Verification statistics

### 2. Discord Bot Integration
**Location**: `integrations/ign_verification.py`  
**Purpose**: Integration layer for Discord bot registration flow  
**Functions**:
- `verify_ign_for_registration()` - Main verification function
- `is_verification_available()` - Service availability check
- `get_verification_stats()` - Statistics retrieval

### 3. Riot API Integration
**Purpose**: Direct API calls to Riot Games for account validation  
**Data Retrieved**: Account existence, level, region validation

## Operational Procedures

### Daily Operations

#### 1. Service Health Monitoring
**Frequency**: Every 15 minutes (automated)  
**Manual Check**: Daily at 9:00 AM  

**Procedure**:
```bash
# Check dashboard service status
curl -X GET http://localhost:8000/api/v1/ign-verification/health

# Expected response
{"status": "healthy", "timestamp": "2025-01-18T10:00:00Z"}
```

**Health Check Indicators**:
- ✅ **Healthy**: Service responding normally
- ⚠️ **Degraded**: Slow response times (>5 seconds)
- ❌ **Unhealthy**: Service not responding (timeout after 10 seconds)

#### 2. Verification Statistics Review
**Frequency**: Daily at 5:00 PM  

**Procedure**:
```bash
# Get verification statistics
curl -X GET http://localhost:8000/api/v1/ign-verification/stats

# Review metrics:
# - total_cached: Number of cached verification results
# - valid_cached: Successfully verified accounts
# - expired_cached: Expired cache entries
# - recent_verifications: Verifications in last 24 hours
```

**Key Metrics**:
- **Cache Hit Rate**: Should be >80%
- **Verification Success Rate**: Should be >95%
- **Response Time**: Should be <3 seconds average
- **Error Rate**: Should be <1%

#### 3. Log Monitoring
**Frequency**: Continuous (automated alerts)  
**Manual Review**: Daily  

**Log Files to Monitor**:
- `api/logs/ign_verification.log`
- `gal_bot.log` (IGN verification entries)
- Dashboard service logs

**Critical Events to Watch**:
- API rate limiting from Riot
- Service timeouts
- Authentication failures
- Unexpected error spikes

### Weekly Operations

#### 1. Cache Performance Review
**Frequency**: Every Monday at 10:00 AM  

**Procedure**:
```sql
-- Connect to dashboard database
sqlite3 dashboard.db

-- Review cache performance
SELECT 
    COUNT(*) as total_entries,
    SUM(CASE WHEN expires_at > datetime('now') THEN 1 ELSE 0 END) as valid_entries,
    SUM(CASE WHEN expires_at <= datetime('now') THEN 1 ELSE 0 END) as expired_entries,
    AVG(verification_time) as avg_verification_time
FROM ign_cache;

-- Review verification patterns
SELECT 
    DATE(created_at) as date,
    COUNT(*) as verifications,
    SUM(CASE WHEN is_valid THEN 1 ELSE 0 END) as successful,
    AVG(verification_time) as avg_time
FROM ign_cache
WHERE created_at >= date('now', '-7 days')
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

**Performance Targets**:
- Cache efficiency >90%
- Average verification time <2 seconds
- Expired entries <5% of total

#### 2. API Usage Review
**Frequency**: Every Monday at 11:00 AM  

**Procedure**:
```bash
# Check Riot API usage patterns
grep "Riot API request" api/logs/ign_verification.log | tail -100

# Check for rate limiting
grep "rate limit" api/logs/ign_verification.log | tail -50

# Review error patterns
grep "ERROR" api/logs/ign_verification.log | tail -50
```

**Usage Indicators**:
- Request volume trends
- Rate limiting occurrences
- Error patterns and frequency

### Monthly Operations

#### 1. System Performance Analysis
**Frequency**: First of each month  

**Metrics to Analyze**:
- Monthly verification volume
- Peak usage periods
- API quota utilization
- Service uptime percentage
- Error rate trends

**Procedure**:
1. Export monthly statistics from database
2. Create performance report
3. Identify optimization opportunities
4. Plan capacity adjustments if needed

#### 2. Security Review
**Frequency**: Monthly  

**Security Checks**:
- API key rotation status
- Rate limiting effectiveness
- Log data retention compliance
- Access control validation

## Troubleshooting Procedures

### Common Issues and Solutions

#### 1. Service Unavailable
**Symptoms**:
- Discord registration shows "IGN verification temporarily unavailable"
- Health check returns 503 or timeout
- High error rate in logs

**Troubleshooting Steps**:
```bash
# 1. Check if dashboard service is running
ps aux | grep "start_dashboard.py"

# 2. Check port availability
netstat -an | grep 8000

# 3. Check service logs
tail -50 api/logs/ign_verification.log

# 4. Restart service if needed
python start_dashboard.py &
```

**Escalation**:
- If service doesn't restart within 5 minutes, escalate to system administrator
- Document incident in `.agent/tasks/active/` with timestamp

#### 2. High Response Times
**Symptoms**:
- Verification requests taking >10 seconds
- Discord registration timeouts
- Performance monitoring alerts

**Troubleshooting Steps**:
```bash
# 1. Check system resources
top -p $(pgrep -f "start_dashboard.py")

# 2. Check database performance
sqlite3 dashboard.db ".timer on" "SELECT COUNT(*) FROM ign_cache;"

# 3. Check network connectivity to Riot API
ping api.riotgames.com

# 4. Review recent API changes
curl -s https://developer.riotgames.com/api-status/
```

**Solutions**:
- Clear expired cache entries if database is bloated
- Increase cache timeout for popular regions
- Consider adding Redis for better caching performance

#### 3. Riot API Rate Limiting
**Symptoms**:
- HTTP 429 errors from Riot API
- Sudden drop in verification success rate
- "Rate limit exceeded" messages in logs

**Immediate Actions**:
```bash
# 1. Check current rate limit status
grep "rate limit" api/logs/ign_verification.log | tail -10

# 2. Implement temporary backoff
# (Automatically handled by the service, but monitor)

# 3. Reduce verification frequency if needed
# Edit config.yaml to increase cache timeout
```

**Prevention**:
- Monitor API quota usage daily
- Implement proper caching strategies
- Use exponential backoff for retries

#### 4. Invalid Verification Results
**Symptoms**:
- Valid IGNs being marked as invalid
- False negatives in verification
- User complaints about verification failures

**Troubleshooting Steps**:
```bash
# 1. Test verification manually
curl -X POST http://localhost:8000/api/v1/ign-verification/verify \
  -H "Content-Type: application/json" \
  -d '{"ign": "test_ign", "region": "na"}'

# 2. Check Riot API changes
curl -s https://developer.riotgames.com/docs/lor

# 3. Review recent code changes
git log --oneline --since="1 week ago" -- integrations/ign_verification.py

# 4. Test Riot API directly
# (Use Riot API testing tools)
```

## Maintenance Procedures

### Cache Management

#### Cache Cleanup
**Frequency**: Weekly  
**Procedure**:
```sql
-- Connect to database
sqlite3 dashboard.db

-- Remove expired entries
DELETE FROM ign_cache WHERE expires_at <= datetime('now');

-- Optimize database
VACUUM;

-- Check cache size
SELECT 
    COUNT(*) as total_entries,
    SUM(LENGTH(account_data)) as total_size_bytes
FROM ign_cache;
```

#### Cache Performance Tuning
**Frequency**: Monthly or as needed  

**Configuration Adjustments**:
```yaml
# config.yaml
ign_verification:
  cache_timeout_hours: 24  # Adjust based on usage patterns
  max_cache_size: 10000    # Limit cache entries
  cleanup_interval_hours: 6 # Cleanup frequency
```

### API Key Management

#### API Key Rotation
**Frequency**: Every 90 days (Riot requirement)  

**Procedure**:
1. Generate new API key from Riot Developer Portal
2. Update environment variables
3. Test new API key functionality
4. Decommission old API key
5. Update documentation

**Environment Variables**:
```bash
# Update .env file
RIOT_API_KEY=new_api_key_here
```

#### API Usage Monitoring
**Frequency**: Daily  

**Monitoring Commands**:
```bash
# Check API key usage
curl -X GET "https://na1.api.riotgames.com/lor/status/v1/platform" \
  -H "X-Riot-Token: $RIOT_API_KEY"

# Monitor quota usage (if available through dashboard)
curl -X GET http://localhost:8000/api/v1/ign-verification/quota
```

## Integration Testing

### Verification Service Testing
**Frequency**: Weekly  
**Test Cases**:
1. Valid IGN verification
2. Invalid IGN handling
3. Service unavailable scenarios
4. Rate limiting behavior
5. Cache performance

**Test Script**:
```python
# test_ign_verification.py
import asyncio
import aiohttp

async def test_verification_service():
    """Test IGN verification service functionality"""
    
    base_url = "http://localhost:8000/api/v1/ign-verification"
    
    async with aiohttp.ClientSession() as session:
        # Test health check
        async with session.get(f"{base_url}/health") as response:
            assert response.status == 200
            health_data = await response.json()
            print(f"Health check: {health_data}")
        
        # Test valid IGN
        async with session.post(
            f"{base_url}/verify",
            json={"ign": "valid_ign", "region": "na"}
        ) as response:
            assert response.status == 200
            result = await response.json()
            print(f"Valid IGN test: {result}")
        
        # Test invalid IGN
        async with session.post(
            f"{base_url}/verify",
            json={"ign": "invalid_ign_12345", "region": "na"}
        ) as response:
            assert response.status == 200
            result = await response.json()
            print(f"Invalid IGN test: {result}")
        
        # Test statistics
        async with session.get(f"{base_url}/stats") as response:
            assert response.status == 200
            stats = await response.json()
            print(f"Statistics: {stats}")

# Run tests
asyncio.run(test_verification_service())
```

### Discord Bot Integration Testing
**Frequency**: After any bot updates  

**Test Procedure**:
1. Create test Discord account
2. Initiate registration with test IGN
3. Verify verification process works
4. Check embed messages and formatting
5. Test graceful fallback behavior

## Performance Optimization

### Monitoring Key Metrics

#### Response Time Targets
- **Health Check**: <100ms
- **Verification Request**: <3 seconds (with cache)
- **Statistics Request**: <500ms

#### Cache Performance Targets
- **Hit Rate**: >80%
- **Cache Size**: <10MB memory usage
- **Cleanup Time**: <1 second

#### API Usage Targets
- **Success Rate**: >95%
- **Rate Limit Hits**: <1% of requests
- **Error Rate**: <1%

### Optimization Strategies

#### Caching Improvements
1. **TTL Optimization**: Adjust cache timeout based on usage patterns
2. **Pre-warming**: Cache popular accounts proactively
3. **Distributed Caching**: Consider Redis for multi-instance deployments

#### API Efficiency
1. **Batch Requests**: Combine multiple verification requests when possible
2. **Request Optimization**: Minimize API calls through smart caching
3. **Error Handling**: Implement proper retry logic with exponential backoff

## Emergency Procedures

### Service Outage Response

#### Immediate Response (First 5 Minutes)
1. **Check Service Status**: Run health check
2. **Identify Issue**: Review recent logs and metrics
3. **Implement Fallback**: Ensure bot registration continues with warnings
4. **Alert Team**: Notify relevant team members

#### Extended Response (5-30 Minutes)
1. **Root Cause Analysis**: Investigate the underlying issue
2. **Temporary Fix**: Implement workaround if possible
3. **Communication**: Update team on progress
4. **Documentation**: Log incident details

#### Recovery (30+ Minutes)
1. **Full Service Restoration**: Return to normal operation
2. **Verification**: Test all functionality
3. **Post-Incident Review**: Document lessons learned
4. **Prevention**: Implement measures to prevent recurrence

### Critical Error Handling

#### Riot API Outage
**Symptoms**: All verification requests failing  
**Response**:
1. Enable graceful fallback mode
2. Allow registrations without verification
3. Add clear warning messages
4. Monitor Riot API status page
5. Communicate with users about the issue

#### Database Corruption
**Symptoms**: Cache errors, data inconsistency  
**Response**:
1. Stop the verification service
2. Restore database from backup
3. Verify data integrity
4. Restart service
5. Monitor for issues

#### Security Incident
**Symptoms**: Unauthorized access, data exposure  
**Response**:
1. Immediately stop affected services
2. Rotate API keys and secrets
3. Review access logs
4. Patch security vulnerabilities
5. Conduct security audit

## Documentation and Reporting

### Incident Documentation
**Location**: `.agent/tasks/active/`  
**Required Information**:
- Incident timestamp and duration
- Symptoms and impact
- Root cause analysis
- Resolution steps taken
- Prevention measures implemented

### Performance Reports
**Frequency**: Monthly  
**Content**:
- Verification volume statistics
- Performance metrics and trends
- Incident summary
- Optimization recommendations
- Capacity planning analysis

### Service Status Dashboard
**Real-time Metrics**:
- Service health status
- Current response times
- Active verification count
- Cache hit rate
- Error rate

## Configuration Management

### Environment Variables
```bash
# Riot API Configuration
RIOT_API_KEY=your_riot_api_key_here
RIOT_API_TIMEOUT=10

# Cache Configuration
IGN_CACHE_TIMEOUT_HOURS=24
IGN_MAX_CACHE_SIZE=10000

# Service Configuration
IGN_VERIFICATION_ENABLED=true
IGN_VERIFICATION_PORT=8000
```

### Service Configuration
```yaml
# config.yaml
ign_verification:
  enabled: true
  cache_timeout_hours: 24
  max_cache_size: 10000
  cleanup_interval_hours: 6
  rate_limit_per_minute: 60
  retry_attempts: 3
  timeout_seconds: 10
```

---

**SOP Version**: 1.0  
**Last Updated**: 2025-01-18  
**Related Documentation**: [Discord Bot Registration](../system/discord-bot-architecture.md), [API Integration](../system/api-integration.md)
