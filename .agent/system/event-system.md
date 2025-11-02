---
id: system.event_system
version: 1.0
last_updated: 2025-10-11
tags: [events, messaging, real-time, handlers, subscribers]
---

# Event System

**Purpose**: Centralized event-driven architecture providing real-time communication, prioritized event handling, and decoupled system integration through publish-subscribe patterns.

## Overview

The Event System (`core/events/`) is a comprehensive event-driven architecture that enables real-time communication between all system components. It provides prioritized event handling, retry logic, event filtering, and seamless integration with Discord, Dashboard, and external services.

**Location**: `core/events/` directory  
**Total Files**: 9 files across 3 subdirectories  
**Primary Dependencies**: asyncio, weakref, dataclasses  
**Lines of Code**: ~8,000 lines across all modules  

## Architecture

### Directory Structure
```
core/events/
├── __init__.py                    # Event system package initialization
├── event_bus.py                   # Central event dispatcher and management
├── event_types.py                 # Event type definitions and base classes
├── handlers/                      # Event handlers for business logic
│   ├── __init__.py
│   ├── configuration_events.py    # Configuration change handlers
│   ├── guild_events.py            # Discord guild event handlers
│   ├── tournament_events.py       # Tournament lifecycle handlers
│   └── user_events.py             # User management event handlers
└── subscribers/                   # Event subscribers for integrations
    ├── __init__.py
    ├── dashboard_subscribers.py   # Dashboard real-time updates
    └── discord_subscribers.py     # Discord bot integration
```

### Event Flow Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Event Source  │───▶│   Event Bus     │───▶│ Event Handlers  │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Event Queue     │    │ Business Logic  │
                       │                 │    │                 │
                       └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Event           │    │ Event           │
                       │ Subscribers     │    │ Publishers      │
                       │                 │    │                 │
                       └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Dashboard     │    │   Discord Bot   │
                       │   Updates       │    │   Responses     │
                       │                 │    │                 │
                       └─────────────────┘    └─────────────────┘
```

## Core Components

### 1. Event Bus (`event_bus.py`)
**Lines**: 533 lines  
**Purpose**: Central event dispatcher with prioritization, retry logic, and event filtering

**Key Features**:
- **Central Event Dispatcher**: Core event routing and management
- **Event Prioritization**: Priority-based event processing
- **Retry Logic**: Automatic retry with exponential backoff
- **Event Filtering**: Conditional event processing
- **Async Processing**: Full async/await support
- **Memory Management**: Weak references for handler lifecycle
- **Performance Monitoring**: Event processing metrics and statistics

**Event Bus Configuration**:
```python
@dataclass
class EventBusConfig:
    max_queue_size: int = 10000
    max_workers: int = 10
    retry_attempts: int = 3
    retry_delay: timedelta = timedelta(seconds=1)
    enable_metrics: bool = True
    batch_size: int = 100
    batch_timeout: timedelta = timedelta(seconds=5)
```

**Event Processing Flow**:
1. **Event Reception**: Receive event from any source
2. **Validation**: Validate event structure and permissions
3. **Prioritization**: Queue events by priority level
4. **Handler Routing**: Route to appropriate handlers
5. **Execution**: Execute handlers with retry logic
6. **Completion**: Track completion and handle failures

### 2. Event Types (`event_types.py`)
**Lines**: 372 lines  
**Purpose**: Comprehensive event type definitions and base event classes

**Event Categories**:

#### Tournament Events
- `TOURNAMENT_CREATED` - New tournament creation
- `TOURNAMENT_UPDATED` - Tournament modification
- `TOURNAMENT_DELETED` - Tournament removal
- `TOURNAMENT_STARTED` - Tournament initiation
- `TOURNAMENT_COMPLETED` - Tournament conclusion
- `REGISTRATION_OPENED` - Registration period start
- `REGISTRATION_CLOSED` - Registration period end
- `USER_REGISTERED` - User tournament registration
- `USER_WITHDRAWN` - User withdrawal from tournament
- `MATCH_CREATED` - Match creation
- `MATCH_UPDATED` - Match modification
- `MATCH_COMPLETED` - Match conclusion

#### User Events
- `USER_CREATED` - New user creation
- `USER_UPDATED` - User profile modification
- `USER_DELETED` - User account removal
- `USER_BANNED` - User ban action
- `USER_UNBANNED` - User unban action
- `USER_ROLE_ADDED` - Role assignment
- `USER_ROLE_REMOVED` - Role removal
- `USER_JOINED_GUILD` - Guild membership
- `USER_LEFT_GUILD` - Guild departure

#### Guild Events
- `GUILD_CREATED` - New guild creation
- `GUILD_UPDATED` - Guild configuration update
- `GUILD_DELETED` - Guild removal
- `GUILD_CONFIGURATION_UPDATED` - Configuration changes

#### Configuration Events
- `CONFIGURATION_UPDATED` - System configuration changes
- `CONFIGURATION_RELOADED` - Configuration reload
- `FEATURE_FLAG_CHANGED` - Feature flag modifications

#### System Events
- `SYSTEM_STARTED` - System startup
- `SYSTEM_SHUTDOWN` - System shutdown
- `HEALTH_CHECK` - System health monitoring
- `ERROR_OCCURRED` - Error notifications

**Event Base Classes**:
```python
@dataclass
class Event:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "system"
    data: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    category: EventCategory = EventCategory.SYSTEM
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**Event Priorities**:
- **CRITICAL**: Immediate processing (system alerts, security events)
- **HIGH**: High priority processing (user actions, important notifications)
- **NORMAL**: Standard priority processing (routine operations)
- **LOW**: Background processing (analytics, logging)

### 3. Event Handlers

#### Tournament Event Handler (`core/events/handlers/tournament_events.py`)
**Lines**: 217 lines  
**Purpose**: Tournament lifecycle management and business logic

**Handler Functions**:
- `_handle_tournament_created` - Tournament creation logic
- `_handle_tournament_updated` - Tournament update processing
- `_handle_tournament_started` - Tournament start procedures
- `_handle_tournament_completed` - Tournament completion handling
- `_handle_registration_opened` - Registration management
- `_handle_user_registered` - User registration processing
- `_handle_match_completed` - Match result processing

**Business Logic Features**:
- **Tournament Validation**: Ensure tournament data integrity
- **Registration Management**: Handle user registrations and withdrawals
- **Match Processing**: Process match results and rankings
- **Notification Handling**: Send appropriate notifications
- **State Management**: Update tournament states correctly

#### User Event Handler (`core/events/handlers/user_events.py`)
**Lines**: 164 lines  
**Purpose**: User management and permissions handling

**Handler Functions**:
- `_handle_user_created` - New user setup
- `_handle_user_updated` - Profile updates
- `_handle_user_banned` - Ban enforcement
- `_handle_user_role_added` - Role assignment
- `_handle_user_joined_guild` - Guild membership processing

**User Management Features**:
- **Profile Management**: Handle user profile updates
- **Permission Management**: Process role changes
- **Guild Integration**: Manage Discord guild membership
- **Ban Management**: Enforce ban/unban actions
- **Activity Tracking**: Track user activity

#### Guild Event Handler (`core/events/handlers/guild_events.py`)
**Lines**: 189 lines  
**Purpose**: Discord guild management and configuration

**Handler Functions**:
- `_handle_guild_created` - New guild setup
- `_handle_guild_updated` - Guild configuration updates
- `_handle_guild_configuration_updated` - Configuration changes

**Guild Management Features**:
- **Configuration Management**: Handle guild settings
- **Channel Management**: Manage Discord channels
- **Role Management**: Handle guild roles
- **Integration Setup**: Configure bot integrations

#### Configuration Event Handler (`core/events/handlers/configuration_events.py`)
**Lines**: 143 lines  
**Purpose**: System configuration management and hot reloading

**Handler Functions**:
- `_handle_configuration_updated` - Configuration changes
- `_handle_configuration_reloaded` - Configuration reload
- `_handle_feature_flag_changed` - Feature flag updates

**Configuration Features**:
- **Hot Reload**: Dynamic configuration updates
- **Validation**: Configuration validation and error handling
- **Feature Flags**: Runtime feature toggle management
- **Change Tracking**: Track configuration changes

### 4. Event Subscribers

#### Dashboard Subscriber (`core/events/subscribers/dashboard_subscribers.py`)
**Lines**: 127 lines  
**Purpose**: Real-time dashboard updates via WebSocket connections

**Subscription Features**:
- **WebSocket Updates**: Real-time dashboard data updates
- **User Presence**: Track active dashboard users
- **Data Synchronization**: Keep dashboard data in sync
- **Connection Management**: Handle WebSocket connections

**WebSocket Events**:
```python
# Dashboard update events
{
    "type": "tournament_update",
    "data": {"tournament_id": "123", "status": "active"},
    "timestamp": "2025-10-11T12:00:00Z"
}

{
    "type": "user_activity",
    "data": {"user_id": "456", "action": "registered"},
    "timestamp": "2025-10-11T12:00:00Z"
}
```

#### Discord Subscriber (`core/events/subscribers/discord_subscribers.py`)
**Lines**: 118 lines  
**Purpose**: Discord bot integration and user notifications

**Subscription Features**:
- **Discord Notifications**: Send Discord messages and embeds
- **User Interactions**: Handle Discord user interactions
- **Channel Updates**: Update Discord channels
- **Command Processing**: Process Discord bot commands

**Discord Integration**:
- **Message Broadcasting**: Send notifications to Discord channels
- **Embed Creation**: Generate rich embed messages
- **User Mentions**: Handle user mentions and notifications
- **Channel Management**: Update channel information

## Event Processing Patterns

### 1. Synchronous Event Processing
```python
# Immediate event processing
await event_bus.emit(Event(
    event_type=EventType.TOURNAMENT_CREATED,
    data={"tournament_id": tournament.id},
    priority=EventPriority.HIGH
))
```

### 2. Asynchronous Event Processing
```python
# Background event processing
event_bus.emit_async(Event(
    event_type=EventType.USER_UPDATED,
    data={"user_id": user.id},
    priority=EventPriority.NORMAL
))
```

### 3. Batch Event Processing
```python
# Process multiple events together
events = [
    Event(event_type=EventType.USER_REGISTERED, data=...),
    Event(event_type=EventType.TOURNAMENT_UPDATED, data=...),
    Event(event_type=EventType.CONFIGURATION_UPDATED, data=...)
]
await event_bus.emit_batch(events)
```

### 4. Conditional Event Processing
```python
# Filter events based on conditions
@event_bus.filter(lambda e: e.data.get("guild_id") == target_guild)
async def guild_specific_handler(event: Event):
    # Handle guild-specific events
    pass
```

## Performance Optimizations

### 1. Event Queue Management
```python
# Priority queue configuration
event_bus = EventBus(
    max_queue_size=10000,
    max_workers=20,
    batch_size=100,
    batch_timeout=timedelta(seconds=5)
)
```

### 2. Handler Optimization
```python
# Efficient handler implementation
class OptimizedEventHandler(EventHandler):
    async def can_handle(self, event: Event) -> bool:
        # Quick filter to avoid unnecessary processing
        return event.event_type in self.handled_types
    
    async def handle(self, event: Event) -> None:
        # Use connection pooling and caching
        async with get_db_session() as session:
            await self.process_event(event, session)
```

### 3. Memory Management
```python
# Weak references to prevent memory leaks
self._handlers = weakref.WeakSet()
self._subscribers = weakref.WeakValueDictionary()
```

## Error Handling and Resilience

### 1. Retry Logic
```python
# Exponential backoff retry configuration
@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_delay: timedelta = timedelta(seconds=1)
    max_delay: timedelta = timedelta(seconds=60)
    backoff_factor: float = 2.0
```

### 2. Error Recovery
```python
# Error handling in event processing
async def handle_event_with_recovery(event: Event):
    try:
        await handler.handle(event)
    except Exception as e:
        logger.error(f"Handler {handler.name} failed: {e}")
        await event_bus.emit(Event(
            event_type=EventType.ERROR_OCCURRED,
            data={"error": str(e), "original_event": event}
        ))
```

### 3. Circuit Breaker Pattern
```python
# Circuit breaker for resilient event handling
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30.0,
    expected_exception=ConnectionError
)

@circuit_breaker
async def resilient_event_handler(event: Event):
    # Handle event with circuit breaker protection
    pass
```

## Monitoring and Observability

### 1. Event Metrics
```python
# Event processing metrics
@dataclass
class EventMetrics:
    total_events: int = 0
    events_by_type: Dict[EventType, int] = field(default_factory=dict)
    events_by_priority: Dict[EventPriority, int] = field(default_factory=dict)
    processing_times: List[float] = field(default_factory=list)
    error_rates: Dict[str, float] = field(default_factory=dict)
    queue_sizes: List[int] = field(default_factory=list)
```

### 2. Performance Monitoring
```python
# Real-time performance monitoring
class EventMonitor:
    def track_event_processing(self, event: Event, duration: float):
        self.metrics.total_events += 1
        self.metrics.processing_times.append(duration)
        self.metrics.events_by_type[event.event_type] += 1
```

### 3. Health Checks
```python
# Event system health monitoring
async def check_event_system_health():
    health_status = {
        "event_bus": await event_bus.health_check(),
        "handlers": await check_handlers_health(),
        "queue_size": event_bus.queue_size(),
        "error_rate": calculate_error_rate()
    }
    return health_status
```

## Security Considerations

### 1. Event Validation
```python
# Input validation for events
def validate_event(event: Event) -> bool:
    # Validate event structure
    if not event.event_type:
        return False
    
    # Validate event data
    if not isinstance(event.data, dict):
        return False
    
    # Validate event source
    if event.source not in ALLOWED_SOURCES:
        return False
    
    return True
```

### 2. Access Control
```python
# Role-based event access control
class EventAccessControl:
    def can_emit_event(self, user: User, event_type: EventType) -> bool:
        required_permissions = EVENT_PERMISSIONS.get(event_type, [])
        return user.has_permissions(required_permissions)
```

### 3. Audit Logging
```python
# Comprehensive event audit logging
async def audit_event(event: Event, user: Optional[User] = None):
    audit_entry = {
        "timestamp": datetime.utcnow(),
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "source": event.source,
        "user_id": user.id if user else None,
        "data_hash": hash(json.dumps(event.data, sort_keys=True))
    }
    await audit_log.create(audit_entry)
```

## Testing Strategy

### 1. Unit Testing
```python
# Event handler unit testing
class TestTournamentEventHandler(unittest.TestCase):
    async def test_tournament_created_handling(self):
        event = TournamentEvent(
            event_type=EventType.TOURNAMENT_CREATED,
            data={"tournament_id": "test_id"}
        )
        handler = TournamentEventHandler()
        await handler.handle(event)
        # Assert handler behavior
```

### 2. Integration Testing
```python
# Event system integration testing
class TestEventBusIntegration(unittest.TestCase):
    async def test_event_end_to_end(self):
        # Test complete event flow
        event_bus = EventBus()
        handler = MockEventHandler()
        event_bus.subscribe(EventType.TOURNAMENT_CREATED, handler)
        
        await event_bus.emit(test_event)
        await asyncio.sleep(0.1)  # Allow processing
        
        self.assertTrue(handler.was_called)
```

### 3. Performance Testing
```python
# Event system performance testing
class TestEventPerformance(unittest.TestCase):
    async def test_high_volume_events(self):
        start_time = time.time()
        
        # Emit 1000 events
        for i in range(1000):
            await event_bus.emit(create_test_event(i))
        
        duration = time.time() - start_time
        self.assertLess(duration, 10.0)  # Should process in under 10 seconds
```

## Best Practices and Guidelines

### 1. Event Design
- Keep events small and focused on single changes
- Include all necessary context in event data
- Use consistent event naming conventions
- Version events to handle schema changes

### 2. Handler Implementation
- Make handlers idempotent (safe to retry)
- Handle exceptions gracefully
- Use proper logging and monitoring
- Implement proper cleanup in error cases

### 3. Performance Optimization
- Use appropriate event priorities
- Implement efficient filtering
- Monitor queue sizes and processing times
- Use batch processing when possible

### 4. Security Considerations
- Validate all event data
- Implement proper access controls
- Audit all event processing
- Use secure communication channels

## Related Documentation

- [Data Access Layer](./data-access-layer.md) - Database integration
- [API Backend System](./api-backend-system.md) - WebSocket integration
- [Data Models](./data-models.md) - Event data structures
- [Architecture Overview](./architecture.md) - System architecture details

---

**Event System Status**: ✅ Production Ready  
**Performance**: Highly optimized with priority queues and batch processing  
**Reliability**: Comprehensive error handling and retry logic  
**Scalability**: Horizontal scaling support with distributed processing  
**Monitoring**: Complete metrics and health monitoring system
