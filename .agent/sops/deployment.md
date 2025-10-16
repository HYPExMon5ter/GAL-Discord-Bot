---
id: sops.deployment
version: 1.0
last_updated: 2025-10-10
tags: [sops, deployment, bot, operations]
---

# Bot Deployment SOP

## Overview
This SOP covers the deployment process for the Guardian Angel League Discord Bot in production environments.

## Prerequisites

### System Requirements
- **Python**: 3.9+ (recommended 3.11)
- **Memory**: Minimum 512MB RAM, recommended 1GB+
- **Storage**: Minimum 1GB free space
- **Network**: Stable internet connection for API access

### Required Files and Configurations
- Discord Bot Token (secure storage required)
- Google Sheets API credentials
- Riot Games API key
- Configuration files (config.yaml, .env)
- Database files (SQLite or PostgreSQL connection)

### Deployment Feature Flags
- `GAL_FEATURE_SHEETS_REFACTOR` (default `true`): disable to revert Google Sheets
  integration to the legacy implementation during staged rollout or rollback.
- `GAL_DEPLOYMENT_STAGE` (optional): set to `integrations`, `backend`, `bot`, or
  `dashboard` to document the active rollout phase in logs and diagnostics.

## Deployment Process

### 1. Environment Setup

#### 1.1 Clone Repository
```bash
git clone <repository-url>
cd New-GAL-Discord-Bot
```

#### 1.2 Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

#### 1.3 Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configuration Setup

#### 2.1 Environment Variables
Create `.env` file with required variables:
```env
DISCORD_BOT_TOKEN=your_bot_token_here
GOOGLE_SHEETS_CREDENTIALS_PATH=path/to/creds.json
RIOT_API_KEY=your_riot_api_key
ENVIRONMENT=production
LOG_LEVEL=INFO
```

#### 2.2 Configuration File
Ensure `config.yaml` is properly configured for production:
```yaml
bot:
  token: ${DISCORD_BOT_TOKEN}
  guild_id: your_guild_id
  
database:
  type: sqlite  # or postgresql
  path: data/gal_bot.db
  
logging:
  level: INFO
  file: logs/gal_bot.log
```

### 3. Database Setup

#### 3.1 SQLite (Development)
```bash
# Database will be created automatically
mkdir -p data
```

#### 3.2 PostgreSQL (Production)
```bash
# Create database
createdb gal_bot

# Set connection string in config.yaml
database:
  type: postgresql
  host: localhost
  port: 5432
  name: gal_bot
  user: gal_bot_user
  password: secure_password
```

### 4. Service Configuration

#### 4.1 Create Systemd Service (Linux)
```ini
[Unit]
Description=Guardian Angel League Bot
After=network.target

[Service]
Type=simple
User=gal_bot
WorkingDirectory=/opt/gal-bot
Environment=PATH=/opt/gal-bot/.venv/bin
ExecStart=/opt/gal-bot/.venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 4.2 Enable and Start Service
```bash
sudo systemctl enable gal-bot
sudo systemctl start gal-bot
```

### 5. Health Checks

#### 5.1 Verify Bot Status
```bash
# Check service status
sudo systemctl status gal-bot

# Check logs
sudo journalctl -u gal-bot -f
```

#### 5.2 Test Discord Integration
- Verify bot is online in Discord
- Test basic commands
- Check role permissions

### 6. Monitoring Setup

#### 6.1 Log Monitoring
```bash
# Monitor bot logs
tail -f gal_bot.log

# Check for errors
grep ERROR gal_bot.log
```

#### 6.2 Resource Monitoring
- Monitor memory usage
- Track API call rates
- Monitor database connections

## Deployment Verification Checklist

### Pre-Deployment
- [ ] All dependencies installed
- [ ] Configuration files validated
- [ ] Database connection tested
- [ ] API credentials verified
- [ ] Backup of existing data (if applicable)

### Post-Deployment
- [ ] Bot starts without errors
- [ ] Discord connection established
- [ ] Basic commands responding
- [ ] Database operations working
- [ ] External API integrations functional
- [ ] Logs generating correctly
- [ ] Monitoring active

## Troubleshooting

### Common Issues

#### Bot Won't Start
1. Check Python version compatibility
2. Verify all dependencies installed
3. Check configuration file syntax
4. Review log files for errors

#### Discord Connection Issues
1. Verify bot token is correct
2. Check internet connectivity
3. Validate Discord API status
4. Review bot permissions in Discord

#### Database Issues
1. Check database file permissions
2. Verify database connection string
3. Validate database schema
4. Check available disk space

#### API Integration Failures
1. Verify API credentials
2. Check API rate limits
3. Review network connectivity
4. Validate API endpoints

## Maintenance Tasks

### Daily
- Monitor bot logs for errors
- Check resource usage
- Verify basic functionality

### Weekly
- Review API usage statistics
- Check database size and performance
- Update bot status in documentation

### Monthly
- Update dependencies
- Review and rotate API keys
- Backup configuration and data
- Performance optimization review

## Security Considerations

### Credential Management
- Store tokens in environment variables
- Use secure credential storage
- Rotate API keys regularly
- Never commit secrets to version control

### Network Security
- Use HTTPS for all API calls
- Implement rate limiting
- Monitor for unusual activity
- Keep dependencies updated

## Rollback Procedure

### Emergency Rollback
1. Stop the bot service
2. Restore previous version from backup
3. Restore database backup if needed
4. Restart bot service
5. Verify functionality

### Data Recovery
1. Stop bot to prevent data corruption
2. Restore database from recent backup
3. Verify data integrity
4. Restart bot service

---
**Version**: 1.0  
**Last Updated**: 2025-10-10  
**Next Review**: 2025-11-10
