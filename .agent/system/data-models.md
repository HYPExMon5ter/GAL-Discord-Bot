---
id: system.data_models
version: 1.0
last_updated: 2025-10-11
tags: [models, entities, data-structures, validation, business-logic]
---

# Data Models

**Purpose**: Comprehensive data entity definitions providing validation, serialization, business logic, and audit trail capabilities for all system data structures.

## Overview

The Data Models (`core/models/`) provide a comprehensive foundation for all data entities in the Guardian Angel League system. Each model includes validation, serialization, business logic, audit trails, and relationship management capabilities.

**Location**: `core/models/` directory  
**Total Files**: 6 core model files  
**Primary Dependencies**: dataclasses, datetime, enum, typing  
**Lines of Code**: ~3,200 lines across all modules  

## Architecture

### Directory Structure
```
core/models/
├── __init__.py           # Model package initialization and exports
├── base_model.py         # Abstract base model with common functionality
├── tournament.py         # Tournament-related entities
├── user.py              # User-related entities
├── guild.py             # Discord guild entities
└── configuration.py     # Configuration management entities
```

### Model Inheritance Hierarchy
```
BaseModel (Abstract)
├── Tournament
│   ├── TournamentRegistration
│   ├── TournamentMatch
│   └── TournamentParticipant
├── User
│   ├── UserProfile
│   ├── UserStats
│   ├── UserPermission
│   └── UserSession
├── Guild
│   ├── GuildConfiguration
│   ├── GuildChannel
│   └── GuildRole
└── Configuration
    ├── SystemConfig
    ├── TournamentConfig
    └── FeatureFlag
```

## Core Components

### 1. Base Model (`base_model.py`)
**Lines**: 157 lines  
**Purpose**: Abstract base class providing common functionality for all data models

**Key Features**:
- **Serialization**: JSON serialization and deserialization
- **Validation**: Abstract validation framework
- **Audit Trail**: Automatic creation/update tracking
- **Version Control**: Model versioning for migrations
- **Metadata Storage**: Flexible metadata storage
- **Change Tracking**: Automatic change detection
- **Comparison**: Model equality and comparison operations

**Base Model Interface**:
```python
@dataclass
class BaseModel(ABC):
    # Core identity fields
    id: Optional[str] = None
    created_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    version: int = 1
    
    # Flexible metadata storage
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Abstract methods
    @abstractmethod
    def validate(self) -> None: pass
    
    # Common functionality
    def to_dict(self) -> Dict[str, Any]: pass
    def from_dict(self, data: Dict[str, Any]): pass
    def to_json(self) -> str: pass
    def get_changes(self) -> Dict[str, Any]: pass
```

**Base Model Features**:
- **Automatic Timestamps**: Creation and update timestamp management
- **User Tracking**: Created by/updated by user tracking
- **Version Management**: Automatic version incrementing
- **Change Detection**: Track field changes between versions
- **Metadata Support**: Flexible key-value metadata storage
- **Serialization**: JSON and dictionary serialization

### 2. Tournament Models (`tournament.py`)
**Lines**: 213 lines  
**Purpose**: Tournament lifecycle management and related entities

#### Core Tournament Entity
```python
@dataclass
class Tournament(BaseModel):
    name: str
    description: Optional[str] = None
    tournament_type: TournamentType = TournamentType.SINGLES
    status: TournamentStatus = TournamentStatus.DRAFT
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    registration_open_date: Optional[datetime] = None
    registration_close_date: Optional[datetime] = None
    max_participants: int = 100
    current_participants: int = 0
    prize_pool: float = 0.0
    entry_fee: float = 0.0
    rules: Optional[str] = None
    format: Optional[str] = None
    discord_channel_id: Optional[str] = None
    organizer_id: Optional[str] = None
    is_public: bool = True
    require_approval: bool = False
```

#### Tournament Registration
```python
@dataclass
class TournamentRegistration(BaseModel):
    tournament_id: str
    user_id: str
    status: RegistrationStatus = RegistrationStatus.PENDING
    registration_date: datetime = field(default_factory=datetime.utcnow)
    approved_by: Optional[str] = None
    approved_date: Optional[datetime] = None
    notes: Optional[str] = None
    seed_position: Optional[int] = None
    disqualification_reason: Optional[str] = None
```

#### Tournament Match
```python
@dataclass
class TournamentMatch(BaseModel):
    tournament_id: str
    round_number: int
    match_number: int
    participant1_id: str
    participant2_id: str
    winner_id: Optional[str] = None
    score_participant1: int = 0
    score_participant2: int = 0
    scheduled_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    status: MatchStatus = MatchStatus.SCHEDULED
    bracket_position: Optional[str] = None
    stream_url: Optional[str] = None
```

**Tournament Enums**:
- **TournamentType**: SINGLES, DOUBLES, TEAM, CUSTOM
- **TournamentStatus**: DRAFT, REGISTRATION_OPEN, REGISTRATION_CLOSED, IN_PROGRESS, COMPLETED, CANCELLED, POSTPONED
- **RegistrationStatus**: PENDING, APPROVED, REJECTED, WAITLIST, WITHDRAWN
- **MatchStatus**: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED, POSTPONED

**Tournament Business Logic**:
- **Registration Management**: Handle registration lifecycle
- **Participant Limits**: Enforce maximum participant limits
- **Date Validation**: Validate tournament dates and registration periods
- **Status Transitions**: Manage tournament status changes
- **Match Generation**: Generate tournament brackets and matches

### 3. User Models (`user.py`)
**Lines**: 254 lines  
**Purpose**: User management, profiles, permissions, and statistics

#### Core User Entity
```python
@dataclass
class User(BaseModel):
    discord_id: str
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    status: UserStatus = UserStatus.UNVERIFIED
    roles: List[UserRole] = field(default_factory=list)
    guilds: List[str] = field(default_factory=list)
    timezone: Optional[str] = None
    language: str = "en"
    is_verified: bool = False
    verification_code: Optional[str] = None
    last_login: Optional[datetime] = None
    banned_until: Optional[datetime] = None
    ban_reason: Optional[str] = None
```

#### User Profile
```python
@dataclass
class UserProfile(BaseModel):
    user_id: str
    bio: Optional[str] = None
    preferred_name: Optional[str] = None
    pronouns: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    primary_game: Optional[str] = None
    skill_level: Optional[str] = None
    team: Optional[str] = None
    social_links: Dict[str, str] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    privacy_settings: Dict[str, bool] = field(default_factory=dict)
```

#### User Statistics
```python
@dataclass
class UserStats(BaseModel):
    user_id: str
    tournaments_played: int = 0
    tournaments_won: int = 0
    matches_played: int = 0
    matches_won: int = 0
    win_rate: float = 0.0
    average_placement: float = 0.0
    earnings: float = 0.0
    ranking_points: float = 0.0
    current_rank: Optional[str] = None
    peak_rank: Optional[str] = None
    last_active: Optional[datetime] = field(default_factory=datetime.utcnow)
```

#### User Permissions
```python
@dataclass
class UserPermission(BaseModel):
    user_id: str
    permission: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    granted_by: Optional[str] = None
    granted_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_active: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
```

**User Enums**:
- **UserRole**: MEMBER, MODERATOR, ADMIN, TOURNAMENT_ORGANIZER, STREAMER, CASTER
- **UserStatus**: ACTIVE, INACTIVE, BANNED, SUSPENDED, VERIFIED, UNVERIFIED

**User Business Logic**:
- **Role Management**: Handle role assignments and permissions
- **Verification**: User verification process
- **Ban Management**: User ban/unban functionality
- **Statistics**: Automatic statistics calculation
- **Privacy Settings**: User privacy and data control

### 4. Guild Models (`guild.py`)
**Lines**: 189 lines  
**Purpose**: Discord guild management and configuration

#### Core Guild Entity
```python
@dataclass
class Guild(BaseModel):
    discord_id: str
    name: str
    owner_id: str
    member_count: int = 0
    icon_url: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None
    preferred_language: str = "en"
    is_active: bool = True
    features: List[str] = field(default_factory=list)
    boost_level: int = 0
    boost_count: int = 0
    joined_at: Optional[datetime] = None
```

#### Guild Configuration
```python
@dataclass
class GuildConfiguration(BaseModel):
    guild_id: str
    prefix: str = "!"
    welcome_channel_id: Optional[str] = None
    log_channel_id: Optional[str] = None
    admin_role_id: Optional[str] = None
    moderator_role_id: Optional[str] = None
    member_role_id: Optional[str] = None
    auto_roles: List[str] = field(default_factory=list)
    welcome_message: Optional[str] = None
    rules_channel_id: Optional[str] = None
    announcements_channel_id: Optional[str] = None
    tournament_category_id: Optional[str] = None
    voice_category_id: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)
```

#### Guild Channel
```python
@dataclass
class GuildChannel(BaseModel):
    guild_id: str
    discord_id: str
    name: str
    type: ChannelType
    category_id: Optional[str] = None
    position: int = 0
    topic: Optional[str] = None
    nsfw: bool = False
    slowmode: int = 0
    user_limit: Optional[int] = None
    bitrate: Optional[int] = None
    parent_id: Optional[str] = None
    permission_overwrites: Dict[str, Any] = field(default_factory=dict)
```

**Guild Enums**:
- **ChannelType**: TEXT, VOICE, CATEGORY, NEWS, STORE, STAGE

**Guild Business Logic**:
- **Configuration Management**: Guild settings and preferences
- **Channel Management**: Discord channel organization
- **Role Management**: Guild role assignments
- **Member Management**: Guild member tracking

### 5. Configuration Models (`configuration.py`)
**Lines**: 201 lines  
**Purpose**: System configuration management and feature flags

#### System Configuration
```python
@dataclass
class SystemConfig(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
    config_type: ConfigType = ConfigType.STRING
    is_sensitive: bool = False
    is_readonly: bool = False
    environment: Optional[str] = None
    category: Optional[str] = None
    validation_rules: Optional[Dict[str, Any]] = None
    default_value: Optional[Any] = None
```

#### Tournament Configuration
```python
@dataclass
class TournamentConfig(BaseModel):
    tournament_type: str
    default_settings: Dict[str, Any] = field(default_factory=dict)
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    status_transitions: Dict[str, List[str]] = field(default_factory=dict)
    notification_settings: Dict[str, Any] = field(default_factory=dict)
```

#### Feature Flag
```python
@dataclass
class FeatureFlag(BaseModel):
    name: str
    is_enabled: bool = False
    description: Optional[str] = None
    rollout_percentage: float = 0.0
    target_users: List[str] = field(default_factory=list)
    target_roles: List[str] = field(default_factory=list)
    target_guilds: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    enabled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
```

**Configuration Enums**:
- **ConfigType**: STRING, INTEGER, FLOAT, BOOLEAN, JSON, LIST, DATETIME

**Configuration Business Logic**:
- **Type Validation**: Ensure configuration values match expected types
- **Validation Rules**: Apply custom validation rules
- **Feature Flag Logic**: Complex feature flag evaluation
- **Environment Management**: Environment-specific configurations

## Model Validation Framework

### 1. Validation Patterns
```python
# Base validation method
def validate(self) -> None:
    """Validate model data and raise exceptions for invalid data."""
    self._validate_required_fields()
    self._validate_field_types()
    self._validate_business_rules()
    self._validate_relationships()

# Field validation
def _validate_required_fields(self) -> None:
    """Validate all required fields are present."""
    for field_name, field_type in self.__dataclass_fields__.items():
        if field_type.default == dataclasses.MISSING and getattr(self, field_name) is None:
            raise ValueError(f"Required field '{field_name}' is missing")

# Business rule validation
def _validate_business_rules(self) -> None:
    """Validate business rules specific to the model."""
    pass  # Implemented by concrete models
```

### 2. Custom Validation Examples
```python
# Tournament validation
def _validate_business_rules(self) -> None:
    """Validate tournament business rules."""
    if self.start_date and self.end_date and self.start_date >= self.end_date:
        raise ValueError("Start date must be before end date")
    
    if self.max_participants <= 0:
        raise ValueError("Max participants must be greater than 0")
    
    if self.current_participants > self.max_participants:
        raise ValueError("Current participants cannot exceed max participants")

# User validation
def _validate_business_rules(self) -> None:
    """Validate user business rules."""
    if not self.discord_id or not self.discord_id.isdigit():
        raise ValueError("Discord ID must be a valid snowflake ID")
    
    if self.banned_until and self.banned_until <= datetime.utcnow():
        self.banned_until = None  # Auto-expire ban
        self.ban_reason = None
```

## Serialization and Deserialization

### 1. JSON Serialization
```python
# Model to JSON
def to_json(self) -> str:
    """Serialize model to JSON string."""
    data = self.to_dict()
    # Handle datetime serialization
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
        elif isinstance(value, Enum):
            data[key] = value.value
    return json.dumps(data, default=str)

# Model from JSON
def from_json(self, json_str: str) -> 'BaseModel':
    """Deserialize model from JSON string."""
    data = json.loads(json_str)
    return self.from_dict(data)
```

### 2. Dictionary Serialization
```python
# Model to dictionary
def to_dict(self) -> Dict[str, Any]:
    """Serialize model to dictionary."""
    result = {}
    for field_name, field_value in self.__dict__.items():
        if isinstance(field_value, Enum):
            result[field_name] = field_value.value
        elif isinstance(field_value, datetime):
            result[field_name] = field_value.isoformat()
        else:
            result[field_name] = field_value
    return result

# Model from dictionary
def from_dict(self, data: Dict[str, Any]) -> 'BaseModel':
    """Deserialize model from dictionary."""
    for field_name, field_value in data.items():
        if hasattr(self, field_name):
            field_type = self.__dataclass_fields__[field_name].type
            if hasattr(field_type, '__origin__') and field_type.__origin__ is Union:
                # Handle Optional types
                inner_type = field_type.__args__[0]
                if isinstance(inner_type, type) and issubclass(inner_type, Enum):
                    field_value = inner_type(field_value) if field_value else None
            elif isinstance(field_value, str) and hasattr(field_type, '__bases__') and issubclass(field_type, Enum):
                field_value = field_type(field_value)
            elif isinstance(field_value, str) and field_type == datetime:
                field_value = datetime.fromisoformat(field_value)
            setattr(self, field_name, field_value)
    return self
```

## Change Tracking and Audit

### 1. Change Detection
```python
# Track model changes
def get_changes(self, original: 'BaseModel') -> Dict[str, Any]:
    """Get changes between this model and original version."""
    changes = {}
    for field_name in self.__dataclass_fields__:
        current_value = getattr(self, field_name)
        original_value = getattr(original, field_name)
        if current_value != original_value:
            changes[field_name] = {
                'from': original_value,
                'to': current_value,
                'changed_at': datetime.utcnow()
            }
    return changes

# Check if model has changes
def has_changes(self, original: 'BaseModel') -> bool:
    """Check if this model has changes compared to original."""
    return len(self.get_changes(original)) > 0
```

### 2. Audit Trail
```python
# Create audit entry
def create_audit_entry(self, action: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Create audit entry for model action."""
    return {
        'model_type': self.__class__.__name__,
        'model_id': self.id,
        'action': action,
        'user_id': user_id,
        'timestamp': datetime.utcnow(),
        'data': self.to_dict(),
        'version': self.version
    }

# Update with audit
def update_with_audit(self, updates: Dict[str, Any], user_id: Optional[str] = None) -> None:
    """Update model with audit trail."""
    original = self.__class__.from_dict(self.to_dict())
    
    for field_name, value in updates.items():
        if hasattr(self, field_name):
            setattr(self, field_name, value)
    
    self.updated_at = datetime.utcnow()
    self.updated_by = user_id
    self.version += 1
    
    # Create audit entry
    audit_entry = {
        'action': 'update',
        'changes': self.get_changes(original),
        'user_id': user_id,
        'timestamp': datetime.utcnow()
    }
    
    if 'audit_log' in self.metadata:
        self.metadata['audit_log'].append(audit_entry)
    else:
        self.metadata['audit_log'] = [audit_entry]
```

## Business Logic Integration

### 1. Lifecycle Hooks
```python
# Pre-save hook
def before_save(self) -> None:
    """Called before model is saved."""
    self.validate()
    self.updated_at = datetime.utcnow()
    self.version += 1

# Post-save hook
def after_save(self) -> None:
    """Called after model is saved."""
    # Send events or notifications
    pass

# Pre-delete hook
def before_delete(self) -> None:
    """Called before model is deleted."""
    # Cleanup related data
    pass
```

### 2. Business Rules
```python
# Tournament business rules
def can_register(self, user: User) -> Tuple[bool, str]:
    """Check if user can register for tournament."""
    if self.status != TournamentStatus.REGISTRATION_OPEN:
        return False, "Registration is not open"
    
    if self.current_participants >= self.max_participants:
        return False, "Tournament is full"
    
    if user.status != UserStatus.ACTIVE:
        return False, "User account is not active"
    
    return True, "Can register"

# User business rules
def can_join_tournament(self, tournament: Tournament) -> Tuple[bool, str]:
    """Check if user can join tournament."""
    if UserStatus.BANNED in self.roles:
        return False, "Banned users cannot join tournaments"
    
    if not self.is_verified:
        return False, "User must be verified to join tournaments"
    
    return True, "Can join tournament"
```

## Performance Optimizations

### 1. Lazy Loading
```python
# Lazy loading for expensive fields
@dataclass
class Tournament(BaseModel):
    # Basic fields
    name: str
    status: TournamentStatus
    
    # Expensive fields (lazy loaded)
    _registrations: Optional[List[TournamentRegistration]] = field(default=None, init=False)
    _matches: Optional[List[TournamentMatch]] = field(default=None, init=False)
    
    @property
    def registrations(self) -> List[TournamentRegistration]:
        """Lazy load tournament registrations."""
        if self._registrations is None:
            self._registrations = self._load_registrations()
        return self._registrations
```

### 2. Caching
```python
# Model-level caching
class ModelCache:
    def __init__(self):
        self._cache = {}
        self._cache_times = {}
        self.cache_ttl = timedelta(minutes=5)
    
    def get(self, model_class: Type[BaseModel], model_id: str) -> Optional[BaseModel]:
        """Get model from cache."""
        cache_key = f"{model_class.__name__}:{model_id}"
        if cache_key in self._cache:
            cached_time = self._cache_times[cache_key]
            if datetime.utcnow() - cached_time < self.cache_ttl:
                return self._cache[cache_key]
        return None
    
    def set(self, model: BaseModel) -> None:
        """Set model in cache."""
        cache_key = f"{model.__class__.__name__}:{model.id}"
        self._cache[cache_key] = model
        self._cache_times[cache_key] = datetime.utcnow()
```

## Testing Strategy

### 1. Model Validation Testing
```python
# Validation testing
class TestTournamentValidation(unittest.TestCase):
    def test_valid_tournament(self):
        tournament = Tournament(
            name="Test Tournament",
            start_date=datetime.utcnow() + timedelta(days=1),
            end_date=datetime.utcnow() + timedelta(days=2),
            max_participants=100
        )
        tournament.validate()  # Should not raise
    
    def test_invalid_dates(self):
        tournament = Tournament(
            name="Test Tournament",
            start_date=datetime.utcnow() + timedelta(days=2),
            end_date=datetime.utcnow() + timedelta(days=1),
            max_participants=100
        )
        with self.assertRaises(ValueError):
            tournament.validate()
```

### 2. Serialization Testing
```python
# Serialization testing
class TestModelSerialization(unittest.TestCase):
    def test_json_serialization(self):
        user = User(discord_id="123456789", username="testuser")
        json_str = user.to_json()
        loaded_user = User().from_json(json_str)
        self.assertEqual(user.discord_id, loaded_user.discord_id)
        self.assertEqual(user.username, loaded_user.username)
```

### 3. Business Logic Testing
```python
# Business logic testing
class TestTournamentBusinessLogic(unittest.TestCase):
    def test_can_register(self):
        tournament = Tournament(
            name="Test Tournament",
            status=TournamentStatus.REGISTRATION_OPEN,
            max_participants=100,
            current_participants=50
        )
        user = User(discord_id="123", username="test", status=UserStatus.ACTIVE)
        
        can_register, reason = tournament.can_register(user)
        self.assertTrue(can_register)
        self.assertEqual(reason, "Can register")
```

## Best Practices and Guidelines

### 1. Model Design
- Keep models focused on single responsibilities
- Use appropriate data types for fields
- Implement comprehensive validation
- Document all fields and business rules

### 2. Validation
- Validate all input data
- Use clear error messages
- Implement both field-level and model-level validation
- Handle edge cases gracefully

### 3. Serialization
- Handle all data types in serialization
- Use consistent serialization formats
- Handle timezone information correctly
- Preserve data integrity during serialization

### 4. Performance
- Use lazy loading for expensive operations
- Implement appropriate caching strategies
- Optimize database queries
- Monitor model performance

## Related Documentation

- [Data Access Layer](./data-access-layer.md) - Database persistence and querying
- [Event System](./event-system.md) - Event-driven updates
- [API Backend System](./api-backend-system.md) - API schema definitions
- [Architecture Overview](./architecture.md) - System architecture details

---

**Data Models Status**: ✅ Production Ready  
**Validation**: Comprehensive validation framework with business rules  
**Serialization**: Complete JSON and dictionary serialization support  
**Audit Trail**: Automatic change tracking and audit logging  
**Performance**: Optimized with caching and lazy loading capabilities
