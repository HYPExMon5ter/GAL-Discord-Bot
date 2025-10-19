# Integration Testing Documentation

This document provides comprehensive guidelines for integration testing within the GAL Discord Bot and Live Graphics Dashboard ecosystem.

## Testing Philosophy

Our testing strategy follows a pyramid approach:

1. **Unit Tests**: Individual component/function testing
2. **Integration Tests**: Component interaction and API integration
3. **End-to-End Tests**: Full user workflows
4. **Performance Tests**: Load and stress testing

## Testing Tools and Frameworks

### Backend Testing
- **pytest**: Primary testing framework
- **pytest-cov**: Coverage reporting
- **httpx**: HTTP client for API testing
- **pytest-mock**: Mocking utilities
- **factory-boy**: Test data factories

### Frontend Testing
- **React Testing Library**: Component testing
- **Jest**: Test runner and assertion library
- **@testing-library/user-event**: User interaction simulation
- **Cypress**: End-to-end testing

### Test Data Management
- **SQLite**: Test database (in-memory)
- **Faker**: Test data generation
- **Fixtures**: Reusable test data

## Test Structure

```
tests/
├── api/                    # API integration tests
│   ├── test_auth.py
│   ├── test_graphics.py
│   ├── test_tournaments.py
│   └── test_configuration.py
├── bot/                   # Discord bot integration tests
│   ├── test_commands.py
│   ├── test_events.py
│   └── test_integrations.py
├── dashboard/             # Frontend integration tests
│   ├── test_components.js
│   ├── test_auth.js
│   └── test_api.js
├── integration/           # Cross-system integration tests
│   ├── test_graphics_workflow.py
│   ├── test_tournament_flow.py
│   └── test_dashboard_sync.py
├── fixtures/              # Test data and fixtures
│   ├── data/
│   ├── factories/
│   └── mocks/
└── conftest.py           # Shared test configuration
```

## API Integration Testing

### Testing API Endpoints

#### Authentication Tests
```python
# tests/api/test_auth.py
def test_login_success():
    """Test successful login with valid credentials"""
    response = client.post("/auth/login", json={
        "master_password": "correct_password"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_failure():
    """Test login failure with invalid credentials"""
    response = client.post("/auth/login", json={
        "master_password": "wrong_password"
    })
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]
```

#### Graphics API Tests
```python
# tests/api/test_graphics.py
@pytest.fixture
def sample_graphic():
    return {
        "title": "Test Tournament",
        "event_name": "Winter Championship",
        "data_json": {"type": "bracket"}
    }

def test_create_graphic(sample_graphic, auth_headers):
    """Test creating a new graphic"""
    response = client.post("/api/v1/graphics/", 
                         json=sample_graphic,
                         headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["title"] == sample_graphic["title"]

def test_get_graphics(auth_headers):
    """Test retrieving graphics list"""
    response = client.get("/api/v1/graphics/", headers=auth_headers)
    assert response.status_code == 200
    assert "graphics" in response.json()
    assert "total" in response.json()
```

#### Data Validation Tests
```python
def test_graphic_data_validation():
    """Test graphic data validation and error handling"""
    # Invalid data
    invalid_data = {
        "title": "",  # Empty title
        "event_name": "Test Event"
    }
    response = client.post("/api/v1/graphics/", 
                         json=invalid_data,
                         headers=auth_headers)
    assert response.status_code == 422
    assert "title" in response.json()["detail"][0]["loc"]
```

### API Testing Best Practices

1. **Authentication Headers**: Always include auth headers for protected endpoints
2. **Status Codes**: Test both success and error scenarios
3. **Data Validation**: Test boundary conditions and invalid inputs
4. **Pagination**: Test skip/limit parameters
5. **Error Handling**: Test proper error responses and messages

## Frontend Integration Testing

### Component Testing

#### Authentication Components
```javascript
// tests/dashboard/test_auth.js
import { render, screen, fireEvent } from '@testing-library/react';
import { LoginForm } from '@/components/auth/LoginForm';
import { useAuth } from '@/hooks/use-auth';

// Mock the auth hook
jest.mock('@/hooks/use-auth');

describe('LoginForm', () => {
  beforeEach(() => {
    useAuth.mockReturnValue({
      login: jest.fn().mockResolvedValue(true),
      loading: false,
      isAuthenticated: false
    });
  });

  test('renders login form', () => {
    render(<LoginForm />);
    expect(screen.getByLabelText(/Master Password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /access dashboard/i })).toBeInTheDocument();
  });

  test('handles successful login', async () => {
    render(<LoginForm />);
    
    fireEvent.change(screen.getByLabelText(/Master Password/i), {
      target: { value: 'correct_password' }
    });
    
    fireEvent.click(screen.getByRole('button', { name: /access dashboard/i }));
    
    await waitFor(() => {
      expect(useAuth().login).toHaveBeenCalledWith('correct_password');
    });
  });
});
```

#### Canvas Editor Testing
```javascript
// tests/dashboard/test_canvas.js
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CanvasEditor } from '@/components/canvas/CanvasEditor';

describe('CanvasEditor', () => {
  const mockGraphic = {
    id: 1,
    title: 'Test Graphic',
    event_name: 'Test Event',
    data_json: '{"elements": []}'
  };

  const mockOnSave = jest.fn().mockResolvedValue(true);
  const mockOnClose = jest.fn();

  beforeEach(() => {
    mockOnSave.mockClear();
    mockOnClose.mockClear();
  });

  test('renders canvas editor with graphic data', () => {
    render(<CanvasEditor 
      graphic={mockGraphic}
      onClose={mockOnClose}
      onSave={mockOnSave}
    />);

    expect(screen.getByDisplayValue('Test Graphic')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Test Event')).toBeInTheDocument();
  });

  test('handles element creation', () => {
    render(<CanvasEditor 
      graphic={mockGraphic}
      onClose={mockOnClose}
      onSave={mockOnSave}
    />);

    fireEvent.click(screen.getByRole('button', { name: /add text/i }));
    
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
  });
});
```

### Hook Testing

#### useAuth Hook
```javascript
// tests/hooks/test_use-auth.js
import { renderHook, act } from '@testing-library/react';
import { useAuth } from '@/hooks/use-auth';

describe('useAuth', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  test('provides initial authentication state', () => {
    const { result } = renderHook(() => useAuth());
    
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.loading).toBe(true);
  });

  test('handles successful login', async () => {
    const { result } = renderHook(() => useAuth());
    
    await act(async () => {
      const success = await result.current.login('correct_password');
      expect(success).toBe(true);
      expect(result.current.isAuthenticated).toBe(true);
    });
  });
});
```

### API Integration Testing (Frontend)

#### API Service Tests
```javascript
// tests/dashboard/test_api.js
import { renderHook, act } from '@testing-library/react';
import { useDashboardData } from '@/hooks/use-dashboard-data';
import { graphicsApi } from '@/lib/api';

// Mock API
jest.mock('@/lib/api');

describe('useDashboardData', () => {
  beforeEach(() => {
    graphicsApi.get.mockResolvedValue({
      graphics: [
        { id: 1, title: 'Graphic 1' },
        { id: 2, title: 'Graphic 2' }
      ],
      total: 2
    });
  });

  test('fetches graphics data', async () => {
    const { result } = renderHook(() => useDashboardData());
    
    await act(async () => {
      await result.current.refetch();
    });
    
    expect(result.current.graphics).toHaveLength(2);
    expect(result.current.loading).toBe(false);
  });

  test('handles API errors', async () => {
    graphicsApi.get.mockRejectedValue(new Error('API Error'));
    
    const { result } = renderHook(() => useDashboardData());
    
    await act(async () => {
      await result.current.refetch();
    });
    
    expect(result.current.error).toBe('API Error');
  });
});
```

## Bot Integration Testing

### Command Testing
```python
# tests/bot/test_commands.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from discord.ext import commands

@pytest.fixture
def mock_bot():
    bot = commands.Bot(command_prefix='!')
    bot.user = MagicMock()
    bot.user.name = 'TestBot'
    return bot

@pytest.fixture
def mock_channel():
    channel = MagicMock()
    channel.send = AsyncMock()
    return channel

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.name = 'TestUser'
    user.mention = '@TestUser'
    return user

async def test_tournament_command(mock_bot, mock_channel, mock_user):
    """Test tournament command functionality"""
    @mock_bot.command()
    async def tournament(ctx, tournament_name: str):
        await ctx.send(f"Tournament {tournament_name} created!")
    
    # Mock the context
    ctx = MagicMock()
    ctx.channel = mock_channel
    ctx.author = mock_user
    
    # Execute command
    await tournament.callback(ctx, "Winter Championship")
    
    # Verify response
    mock_channel.send.assert_called_once_with("Tournament Winter Championship created!")
```

### Event Testing
```python
# tests/bot/test_events.py
async def test_message_event(mock_bot):
    """Test message event handling"""
    @mock_bot.event
    async def on_message(message):
        if message.content == '!hello':
            await message.channel.send('Hello!')
    
    # Mock message
    message = MagicMock()
    message.content = '!hello'
    message.channel = MagicMock()
    message.channel.send = AsyncMock()
    
    # Trigger event
    await mock_bot.process_commands(message)
    await mock_bot.on_message(message)
    
    # Verify response
    message.channel.send.assert_called_once_with('Hello!')
```

### Integration Testing with External Services
```python
# tests/bot/test_integrations.py
def test_google_sheets_integration():
    """Test Google Sheets integration functionality"""
    from integrations.sheets import GoogleSheetsIntegration
    
    sheets = GoogleSheetsIntegration()
    
    # Mock Google Sheets API
    sheets.service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
        'values': [['Player1', 'Score1'], ['Player2', 'Score2']]
    }
    
    result = sheets.get_tournament_data('test_spreadsheet')
    
    assert len(result) == 2
    assert result[0] == ['Player1', 'Score1']

def test_discord_api_integration():
    """Test Discord API integration"""
    from discord.ext import commands
    
    # Mock Discord API calls
    mock_guild = MagicMock()
    mock_guild.id = '12345'
    
    # Test guild creation or retrieval
    guild = get_or_create_guild(mock_guild.id)
    
    assert guild.id == mock_guild.id
    assert isinstance(guild, MagicMock)
```

## Cross-System Integration Testing

### Graphics Workflow Testing
```python
# tests/integration/test_graphics_workflow.py
def test_full_graphics_workflow():
    """Test complete graphics creation and management workflow"""
    # 1. Login and authenticate
    auth_response = client.post("/auth/login", json={
        "master_password": "correct_password"
    })
    auth_token = auth_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # 2. Create graphic
    graphic_data = {
        "title": "Test Tournament",
        "event_name": "Winter Championship",
        "data_json": {"type": "bracket"}
    }
    
    create_response = client.post("/api/v1/graphics/", 
                                json=graphic_data,
                                headers=headers)
    graphic_id = create_response.json()["id"]
    
    # 3. Edit graphic
    update_data = {
        "title": "Updated Tournament",
        "event_name": "Spring Championship"
    }
    
    update_response = client.put(f"/api/v1/graphics/{graphic_id}",
                                json=update_data,
                                headers=headers)
    
    # 4. Archive graphic
    archive_response = client.post(f"/api/v1/archive/{graphic_id}",
                                  headers=headers)
    
    # 5. Verify workflow completion
    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert archive_response.status_code == 200
```

### Dashboard-Bot Synchronization Testing
```python
# tests/integration/test_dashboard_sync.py
def test_dashboard_bot_sync():
    """Test synchronization between dashboard and bot"""
    # Simulate dashboard update
    dashboard_data = {
        "tournament_name": "Spring Championship",
        "participants": ["Player1", "Player2", "Player3"]
    }
    
    # Update database through API
    response = client.post("/api/v1/tournaments/sync",
                          json=dashboard_data,
                          headers=admin_headers)
    
    # Verify bot received update
    assert response.status_code == 200
    
    # Check tournament data in bot
    tournament = get_tournament_from_db("Spring Championship")
    assert tournament.name == "Spring Championship"
    assert len(tournament.participants) == 3
```

## Test Data Management

### Test Fixtures
```python
# tests/fixtures/data.py
import pytest
from datetime import datetime

@pytest.fixture
def sample_tournament():
    return {
        "name": "Winter Championship",
        "start_date": datetime.now(),
        "end_date": datetime.now(),
        "status": "active",
        "participants": []
    }

@pytest.fixture
def sample_user():
    return {
        "username": "testuser",
        "discord_id": "123456789",
        "role": "admin"
    }

@pytest.fixture
def sample_graphic():
    return {
        "title": "Test Graphic",
        "event_name": "Test Event",
        "data_json": {"elements": []},
        "created_by": "testuser"
    }
```

### Test Factories
```python
# tests/factories.py
from factory import Faker, LazyAttribute
from factory.alchemy import SQLAlchemyModelFactory
from models import Tournament, User, Graphic

class TournamentFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Tournament
    
    name = Faker('word')
    start_date = Faker('date_this_year')
    end_date = LazyAttribute(lambda obj: obj.start_date)
    status = 'active'

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
    
    username = Faker('user_name')
    discord_id = Faker('numerify', text='###########')
    role = 'user'

class GraphicFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Graphic
    
    title = Faker('word')
    event_name = Faker('word')
    data_json = "{}"
    created_by = LazyAttribute(lambda obj: obj.user.username)
```

## Test Configuration

### pytest Configuration
```python
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80

# Test markers
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
```

### conftest.py Configuration
```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from api.main import app
from database import get_db
import tempfile
from pathlib import Path

# Test client
@pytest.fixture(scope="session")
def client():
    return TestClient(app)

# Test database
@pytest.fixture(scope="session")
def test_db():
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    # Initialize test database
    from database import init_db
    init_db(db_path)
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)

# Authentication headers
@pytest.fixture
def auth_headers(client):
    response = client.post("/auth/login", json={
        "master_password": "test_password"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# Admin headers
@pytest.fixture
def admin_headers(client):
    response = client.post("/auth/login", json={
        "master_password": "admin_password"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

## Performance Testing

### Load Testing with Locust
```python
# tests/performance/test_load.py
from locust import HttpUser, task, between

class DashboardUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        # Login
        response = self.client.post("/auth/login", json={
            "master_password": "test_password"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task
    def browse_graphics(self):
        self.client.get("/api/v1/graphics/", headers=self.headers)
    
    @task(3)
    def create_graphic(self):
        graphic_data = {
            "title": "Load Test Graphic",
            "event_name": "Load Test Event",
            "data_json": {"type": "simple"}
        }
        self.client.post("/api/v1/graphics/",
                        json=graphic_data,
                        headers=self.headers)
```

## CI/CD Integration

### GitHub Actions Workflow
```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]
        node-version: [18, 20]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov httpx
    
    - name: Run API tests
      run: |
        pytest tests/api/ -v --cov=api
    
    - name: Set up Node.js ${{ matrix.node-version }}
      uses: actions/setup-node@v4
      with:
        node-version: ${{ matrix.node-version }}
        cache: 'npm'
    
    - name: Install Node.js dependencies
      run: |
        cd dashboard
        npm install
    
    - name: Run frontend tests
      run: |
        cd dashboard
        npm test
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
```

## Test Documentation and Reporting

### Test Results
All test results are automatically reported through:
- **pytest-cov**: Coverage reports
- **GitHub Actions**: CI/CD pipeline status
- **Codecov**: Code coverage badge
- **Allure Reports**: Detailed test reports

### Test Metrics
- **Code Coverage**: Minimum 80% coverage requirement
- **Test Execution Time**: Monitor for performance regressions
- **Flaky Tests**: Track and fix unstable tests
- **Integration Test Success Rate**: Monitor system health

## Troubleshooting Common Issues

### API Testing Issues
1. **Authentication Errors**: Check token validity and headers
2. **Database State**: Use fixtures to ensure clean state
3. **Async Operations**: Properly await async test functions

### Frontend Testing Issues
1. **Component Rendering**: Check for missing dependencies
2. **State Management**: Verify hook usage and context
3. **API Mocks**: Ensure proper mocking of external services

### Bot Testing Issues
1. **Discord API Limits**: Mock API calls to avoid rate limiting
2. **Event Timing**: Use proper async/await patterns
3. **Command Registration**: Ensure commands are properly registered

---

**Last Updated**: 2025-01-18  
**Maintained by**: Guardian Angel League Development Team
