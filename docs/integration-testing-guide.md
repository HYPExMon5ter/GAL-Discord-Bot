# Integration Testing Guide

This guide provides comprehensive procedures for testing external integrations in the Guardian Angel League Discord Bot and Dashboard system.

## Overview

Integration testing ensures that external services (Google Sheets, Riot API, Discord API) work correctly with the GAL system. The testing process covers authentication, data synchronization, error handling, and edge cases.

## Test Categories

### 1. Google Sheets Integration
### 2. Riot API Integration  
### 3. Discord API Integration
### 4. WebSocket Integration
### 5. Database Integration

## Testing Environment Setup

### Prerequisites
- **Test Google Sheet**: Create a dedicated test sheet with sample data
- **Test Discord Server**: Use a development server for bot testing
- **Test Riot API Key**: Obtain a development API key with limited access
- **Test Database**: Use SQLite for local testing or staging database

### Configuration
```bash
# Copy environment file for testing
cp .env.test .env.local

# Set test credentials
DISCORD_BOT_TOKEN=test_bot_token_here
GOOGLE_SERVICE_ACCOUNT_KEY=test_service_account.json
RIOT_API_KEY=test_riot_api_key_here
TEST_GUILD_ID=123456789012345678
TEST_SPREADSHEET_ID=1abc123def456ghi789jkl012mno345
```

## Google Sheets Integration Testing

### Test Scenarios

#### 1. User Registration Test
**Objective**: Verify user registration and data synchronization

**Steps:**
1. Start the Discord bot and API backend
2. Use `!register` command with valid IGN
3. Verify user appears in test Google Sheet
4. Check data format matches expected schema
5. Verify user role assignment in Discord

**Expected Results:**
- User row added to Google Sheet
- Data includes: user_id, ign, registration_time, checkin_status
- Discord role assigned successfully

#### 2. Check-in Status Test
**Objective**: Verify check-in state management

**Steps:**
1. Register a test user
2. Use `!checkin` command
3. Verify sheet updates with timestamp
4. Use `!checkout` command
5. Verify sheet check-in status reverts

**Expected Results:**
- Sheet checkin_status changes to "checked_in"
- Timestamp updates to current time
- Status reverts to "registered" on checkout

#### 3. Data Refresh Test
**Objective**: Verify cache refresh functionality

**Steps:**
1. Start bot with cache enabled
2. Modify Google Sheet data manually
3. Use `!cache` command to refresh
4. Verify bot data updates
5. Check timestamp in response

**Expected Results:**
- Bot recognizes manual sheet changes
- Cache refresh completes successfully
- Timestamp reflects refresh time

#### 4. Error Handling Test
**Objective**: Test error scenarios and recovery

**Steps:**
1. Simulate network connectivity issues
2. Test with invalid sheet ID
3. Test with expired service account
4. Test with malformed sheet data
5. Verify graceful error messages

**Expected Results:**
- Clear error messages to users
- System remains stable during errors
- Recovery after service restoration

#### 5. Rate Limiting Test
**Objective**: Verify API rate limiting and retry logic

**Steps:**
1. Execute rapid registration commands
2. Monitor API response times
3. Check for rate limiting responses
4. Verify exponential backoff behavior
5. Test recovery after limit reset

**Expected Results:**
- Rate limiting prevents API abuse
- Backoff logic prevents hammering
- System recovers gracefully

### Test Data Structure

#### Test Google Sheet Headers
```excel
User ID | IGN | Registration Time | Check-in Status | Discord ID | Tournament Mode | Last Updated
--------|-----|------------------|----------------|------------|-----------------|--------------
123456 | test_user | 2025-01-18 10:00:00 | registered | 789012 | normal | 2025-01-18 10:05:00
```

#### Test Cases
```typescript
interface TestCase {
  name: string;
  description: string;
  steps: string[];
  expected: string[];
  assertions: () => boolean;
}

const userRegistrationTest: TestCase = {
  name: "User Registration",
  description: "Test new user registration flow",
  steps: [
    "Start bot",
    "Execute !register with valid IGN",
    "Check Google Sheet",
    "Verify Discord role"
  ],
  expected: [
    "User row created in sheet",
    "Data format correct",
    "Discord role assigned",
    "Success message sent"
  ],
  assertions: () => {
    // Implementation for assertions
    return true;
  }
};
```

## Riot API Integration Testing

### Test Scenarios

#### 1. IGN Verification Test
**Objective**: Verify player identity verification

**Steps:**
1. Use `!register` with valid player IGN
2. Monitor Riot API request/response
3. Verify successful verification
4. Test with invalid/non-existent IGN
5. Test with special characters in IGN

**Expected Results:**
- Valid IGNs are verified successfully
- Invalid IGNs return appropriate errors
- Special characters are handled properly
- API rate limiting is respected

#### 2. Player Stats Test
**Objective**: Verify player statistics retrieval

**Steps:**
1. Register a test player
2. Use stats-related commands
3. Monitor API response data
4. Verify data completeness
5. Test with different regions

**Expected Results:**
- Player data retrieved successfully
- Stats include required fields (wins, losses, placement)
- Region-specific data correct
- Error handling for API failures

#### 3. Rate Limiting Test
**Objective**: Test Riot API rate limiting

**Steps:**
1. Execute rapid stat requests
2. Monitor response codes
435
3. Verify backoff behavior
4. Test recovery after limit reset
5. Monitor for excessive usage

**Expected Results:**
- 429 HTTP status when rate limited
- Exponential backoff implemented
- System recovers after limit reset
- No API abuse detected

### Test Data

#### Test IGNs
```typescript
const testIGNs = [
  "ValidPlayer123",           // Valid IGN
  "InvalidPlayer",           // Likely invalid
  "Player With Spaces",       // Spaces should be handled
  "玩家名称",                 // Non-ASCII characters
  "",                        // Empty string
  "VeryLongPlayerName123456789" // Long IGN
];
```

## Discord API Integration Testing

### Test Scenarios

#### 1. Bot Authentication Test
**Objective**: Verify bot authentication and permissions

**Steps:**
1. Start bot with test token
2. Verify bot connects to Discord
3. Check permissions in test server
4. Test token expiration scenarios
5. Test invalid token scenarios

**Expected Results:**
- Bot connects successfully
- Correct permissions verified
- Graceful handling of auth failures
- Clear error messages

#### 2. Message Processing Test
**Objective**: Test message command processing

**Steps:**
1. Send various bot commands
2. Monitor message processing
3. Test message parsing
4. Verify response generation
5. Test malformed commands

**Expected Results:**
- Commands processed correctly
- Valid responses generated
- Error handling for malformed input
- Response time within acceptable limits

#### 3. Role Management Test
**Objective**: Test role assignment and management

**Steps:**
1. Register test users
2. Verify role assignment
3. Test role removal
4. Test role conflict scenarios
5. Test permission inheritance

**Expected Results:**
- Roles assigned correctly
- Role conflicts resolved
- Permission hierarchy maintained
- Clear audit trail

### Test Commands
```typescript
const testCommands = [
  { command: "!register", ign: "TestPlayer" },
  { command: "!checkin", expected: "success" },
  { command: "!checkout", expected: "success" },
  { command: "!registeredlist", expected: "list" },
  { command: "!help", expected: "help" }
];
```

## WebSocket Integration Testing

### Test Scenarios

#### 1. Connection Test
**Objective**: Verify WebSocket connection establishment

**Steps:**
1. Start WebSocket server
2. Connect dashboard client
3. Verify handshake completion
4. Test connection stability
5. Test connection closure

**Expected Results:**
- Connection established successfully
- Handshake completes properly
- Connection remains stable
- Clean shutdown on disconnect

#### 2. Real-time Updates Test
**Objective**: Test real-time data synchronization

**Steps:**
1. Establish WebSocket connection
2. Modify data on backend
3. Monitor client updates
4. Test bidirectional communication
5. Test message queue management

**Expected Results:**
- Real-time updates received
- Bidirectional communication works
- Message order preserved
- No message loss

#### 3. Error Handling Test
**Objective**: Test WebSocket error scenarios

**Steps:**
1. Simulate network issues
2. Test malformed messages
3. Test connection drops
4. Test reconnection logic
5. Test authentication failures

**Expected Results:**
- Graceful error handling
- Automatic reconnection
- Clear error messages
- No data corruption

## Database Integration Testing

### Test Scenarios

#### 1. Data Persistence Test
**Objective**: Verify data storage and retrieval

**Steps:**
1. Create test data entries
2. Store in database
3. Retrieve stored data
4. Verify data integrity
5. Test concurrent access

**Expected Results:**
- Data stored correctly
- Data retrieved accurately
- Data integrity maintained
- Concurrent access handled properly

#### 2. Migration Testing
**Objective**: Test database schema migrations

**Steps:**
1. Create test database
2. Apply migration scripts
3. Verify schema changes
4. Test data transformation
5. Verify rollback scenarios

**Expected Results:**
- Migration completes successfully
- Schema changes applied
- Data transformed correctly
- Rollback works when needed

### Test Database Schema
```sql
-- Test database schema
CREATE TABLE test_users (
    id INTEGER PRIMARY KEY,
    discord_id TEXT UNIQUE,
    ign TEXT,
    registered_at TIMESTAMP,
    checkin_status TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE test_graphics (
    id INTEGER PRIMARY KEY,
    title TEXT,
    event_name TEXT,
    data_json TEXT,
    created_by TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    archived BOOLEAN
);
```

## Testing Tools and Utilities

### Test Scripts
```bash
# Run integration tests
python -m pytest tests/integration/

# Run specific integration tests
python -m pytest tests/integration/test_sheets.py

# Run with coverage
python -m pytest tests/integration/ --cov=integrations

# Run with verbose output
python -m pytest tests/integration/ -v
```

### Test Framework Configuration
```python
# conftest.py
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_discord_client():
    return Mock()

@pytest.fixture
def mock_sheets_client():
    return AsyncMock()

@pytest.fixture
def mock_riot_client():
    return AsyncMock()

@pytest.fixture
def test_database():
    # Setup test database
    pass
```

### Mock Data Generation
```python
# test_data.py
def generate_test_user():
    return {
        "discord_id": "123456789012345678",
        "ign": "TestPlayer",
        "registered_at": datetime.now(),
        "checkin_status": "registered"
    }

def generate_test_graphic():
    return {
        "title": "Test Graphic",
        "event_name": "Test Tournament",
        "data_json": "{}",
        "created_by": "test_user"
    }
```

## Performance Testing

### Response Time Benchmarks
- **Discord API**: < 100ms response time
- **Google Sheets**: < 2000ms response time
- **Riot API**: < 500ms response time
- **WebSocket**: < 50ms message delivery

### Load Testing
- **Concurrent Users**: 100+ simultaneous connections
- **Message Rate**: 50+ messages per second
- **Database Connections**: 20+ concurrent connections
- **API Rate**: 1000+ requests per minute

## Error Scenarios Testing

### Common Error Cases
1. **Network Timeouts**: Verify timeout handling
2. **API Failures**: Test service unavailability
3. **Authentication Failures**: Test invalid credentials
4. **Data Corruption**: Test malformed data handling
5. **Resource Exhaustion**: Test memory/CPU limits

### Error Recovery Testing
```typescript
// Error recovery test case
const errorRecoveryTest = {
  name: "Error Recovery",
  steps: [
    "Simulate API failure",
    "Execute dependent operations", 
    "Verify graceful degradation",
    "Restore service",
    "Verify recovery"
  ],
  assertions: () => {
    // Check that system recovers gracefully
    return true;
  }
};
```

## Reporting and Monitoring

### Test Results Dashboard
```typescript
interface TestResult {
  test_name: string;
  status: "passed" | "failed" | "skipped";
  duration: number;
  timestamp: Date;
  error?: string;
  details?: any;
}

const testResults: TestResult[] = [
  {
    test_name: "User Registration",
    status: "passed",
    duration: 1500,
    timestamp: new Date()
  }
];
```

### Monitoring Metrics
- **Test Success Rate**: > 95%
- **Response Time**: Within thresholds
- **Error Rate**: < 1%
- **Coverage Rate**: > 90%

## Continuous Integration

### GitHub Actions Configuration
```yaml
name: Integration Tests
on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run integration tests
        run: pytest tests/integration/
```

## Troubleshooting Common Issues

### Google Sheets Issues
- **Authentication**: Verify service account credentials
- **Permissions**: Check sheet sharing settings
- **Rate Limits**: Monitor API usage
- **Data Format**: Verify column headers match expected format

### Discord API Issues
- **Token**: Verify bot token validity
- **Permissions**: Check server permissions
- **Rate Limits**: Monitor Discord rate limits
- **Gateway**: Verify WebSocket connection

### Riot API Issues
- **API Key**: Verify key validity and limits
- **Region**: Check correct region endpoint
- **Rate Limits**: Monitor Riot rate limits
- **Data Format**: Verify response schema

---

**Note**: Always test in a development environment before deploying changes to production.  
**Version**: 1.0.0  
**Last Updated**: 2025-01-18
