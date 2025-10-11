---
id: sops.troubleshooting
version: 1.0
last_updated: 2025-10-10
tags: [sop, troubleshooting, support, maintenance]
---

# Troubleshooting SOP

## Purpose
This SOP provides systematic procedures for diagnosing and resolving common issues with the Guardian Angel League Discord Bot and its integrated systems.

## Scope
- Bot connectivity and performance issues
- Integration failures (Google Sheets, Riot API)
- User permission and role problems
- Database synchronization issues
- Command execution errors

## Troubleshooting Framework

### 1. Issue Classification
- **Critical**: Bot offline, complete functionality loss
- **High**: Major features broken, significant user impact
- **Medium**: Partial functionality loss, limited user impact
- **Low**: Minor issues, cosmetic problems

### 2. Response Priority
- **Critical**: Immediate response (within 15 minutes)
- **High**: Urgent response (within 1 hour)
- **Medium**: Standard response (within 4 hours)
- **Low**: Scheduled response (within 24 hours)

## Common Issues and Solutions

### Bot Connectivity Issues

#### Bot Not Responding
**Symptoms**: Commands failing, no response from bot
**Diagnostic Steps**:
1. Check bot status in Discord server
2. Verify bot process is running
3. Check Discord API connectivity
4. Review bot logs for errors

**Solutions**:
- Restart bot process: `python bot.py`
- Check Discord API status page
- Verify bot token is valid
- Check internet connectivity

#### Bot Lagging or Slow Response
**Symptoms**: Delayed responses, timeout errors
**Diagnostic Steps**:
1. Monitor system resource usage
2. Check database connection performance
3. Review API rate limits
4. Analyze bot execution logs

**Solutions**:
- Optimize database queries
- Implement caching for frequent operations
- Check for memory leaks
- Scale up resources if needed

### Integration Issues

#### Google Sheets Integration Failures
**Symptoms**: Sheet synchronization errors, data not updating
**Diagnostic Steps**:
1. Check Google API credentials
2. Verify sheet permissions
3. Test API connectivity
4. Review authentication tokens

**Solutions**:
- Refresh Google API credentials
- Update service account permissions
- Reauthorize access to Google Sheets
- Check sheet sharing settings

#### Riot API Integration Problems
**Symptoms**: Summoner verification failures, API errors
**Diagnostic Steps**:
1. Check Riot API key validity
2. Verify API rate limits
3. Test network connectivity
4. Review API response codes

**Solutions**:
- Renew Riot API key
- Implement rate limiting
- Use regional endpoints correctly
- Handle API errors gracefully

### User Permission Issues

#### Users Not Receiving Roles
**Symptoms**: New users not getting appropriate roles
**Diagnostic Steps**:
1. Check bot role permissions
2. Verify role hierarchy in Discord
3. Review role assignment logic
4. Check for role conflicts

**Solutions**:
- Ensure bot has "Manage Roles" permission
- Place bot role above user roles in hierarchy
- Fix role assignment logic in code
- Resolve role conflicts

#### Command Permission Errors
**Symptoms**: Users can't execute commands they should have access to
**Diagnostic Steps**:
1. Check command permission settings
2. Verify user roles and permissions
3. Review role-based access control logic
4. Test command execution

**Solutions**:
- Update command permission requirements
- Fix role assignment logic
- Check for permission inheritance issues
- Test with different user roles

### Database Issues

#### Database Connection Failures
**Symptoms**: Errors when accessing user data, synchronization failures
**Diagnostic Steps**:
1. Check database service status
2. Verify connection string and credentials
3. Test database connectivity
4. Review database logs

**Solutions**:
- Restart database service
- Update connection credentials
- Check database file permissions
- Implement connection retry logic

#### Data Synchronization Issues
**Symptoms**: Inconsistent data between database and Google Sheets
**Diagnostic Steps**:
1. Check last synchronization timestamp
2. Compare data between sources
3. Review sync logs for errors
4. Test manual synchronization

**Solutions**:
- Run manual synchronization
- Fix data mapping issues
- Resolve conflict resolution logic
- Update sync frequency

## Diagnostic Tools and Commands

### Bot Status Commands
- `/status` - Check bot health and uptime
- `/ping` - Test bot responsiveness
- `/debug` - Get detailed diagnostic information
- `/logs` - View recent bot activity logs

### System Monitoring Commands
- `/system-info` - Get system resource usage
- `/api-status` - Check integration API status
- `/db-status` - Verify database connectivity
- `/sync-status` - Check synchronization status

### Administrative Commands
- `/restart` - Restart bot services
- `/reload-config` - Reload configuration files
- `/clear-cache` - Clear bot cache
- `/force-sync` - Force data synchronization

## Log Analysis

### Log Locations
- **Bot Logs**: `gal_bot.log` - Main bot activity logs
- **Error Logs**: Error messages and stack traces
- **Integration Logs**: API call logs and responses
- **Security Logs**: Authentication and authorization events

### Log Analysis Patterns
1. **Error Frequency**: Look for recurring error patterns
2. **Performance Metrics**: Track response times and resource usage
3. **User Activity**: Monitor command usage patterns
4. **Integration Health**: Track API success/failure rates

### Common Log Messages
- `Token masked in log` - Normal security behavior
- `API rate limit exceeded` - Implement rate limiting
- `Database connection failed` - Check database service
- `Permission denied` - Fix role/permission issues

## Emergency Procedures

### Bot Complete Failure
1. **Immediate Action**: Restart bot process
2. **Investigation**: Check system resources and logs
3. **Communication**: Notify users of downtime
4. **Recovery**: Restore from backup if needed
5. **Prevention**: Implement monitoring and alerts

### Data Corruption
1. **Isolation**: Stop bot to prevent further damage
2. **Assessment**: Determine extent of corruption
3. **Recovery**: Restore from recent backup
4. **Verification**: Validate data integrity
5. **Prevention**: Implement regular backups

### Security Incident
1. **Containment**: Isolate affected systems
2. **Investigation**: Analyze security breach
3. **Notification**: Inform stakeholders and users
4. **Recovery**: Secure systems and restore services
5. **Prevention**: Update security measures

## Prevention and Maintenance

### Regular Maintenance Tasks
- **Daily**: Review bot logs and performance metrics
- **Weekly**: Check integration API status and limits
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Comprehensive system health review

### Monitoring Setup
- **Uptime Monitoring**: Bot availability and response times
- **Performance Monitoring**: Resource usage and response metrics
- **Error Monitoring**: Automated alerts for critical errors
- **Security Monitoring**: Authentication and access pattern analysis

### Backup Procedures
- **Database Backups**: Daily automated backups
- **Configuration Backups**: Version control for config files
- **Log Rotation**: Regular log file cleanup and archiving
- **Disaster Recovery**: Documented recovery procedures

## Communication Protocols

### Incident Reporting
- **Critical Issues**: Immediate notification to all admins
- **High Priority**: Alert within 1 hour to core team
- **Medium Priority**: Create support ticket for resolution
- **Low Priority**: Log for future resolution

### User Communication
- **Planned Maintenance**: 24-hour advance notice
- **Unplanned Downtime**: Immediate notification and updates
- **Feature Issues**: Clear explanation and ETA for resolution
- **Security Events**: Transparent communication about impacts

## Documentation and Knowledge Base

### Troubleshooting Guides
- Common error scenarios and solutions
- Step-by-step diagnostic procedures
- Contact information for escalation
- Reference documentation for all integrations

### Knowledge Sharing
- Regular team training sessions
- Documentation updates after incident resolution
- Shared troubleshooting best practices
- Lessons learned from major incidents

## Escalation Procedures

### Level 1 Support
- Basic troubleshooting and user guidance
- Common issue resolution
- Documentation and knowledge base usage

### Level 2 Support
- Complex technical issues
- Integration problem resolution
- System configuration and optimization

### Level 3 Support
- Critical system failures
- Security incident response
- Development and code-level issues

## Contact Information

### Primary Contacts
- **Bot Administrator**: Primary technical contact
- **System Administrator**: Infrastructure and deployment
- **Development Team**: Code-level issues and features

### Escalation Contacts
- **Project Lead**: Critical incidents and decisions
- **Security Team**: Security incidents and concerns
- **External Support**: Third-party integration support

---

**Version**: 1.0  
**Last Updated**: 2025-10-10  
**Next Review**: 2025-12-10  
**Maintained By**: Guardian Angel League Development Team
