---
id: system.integration-modules
version: 1.2
last_updated: 2025-06-17
tags: [system, integrations, modules, documentation]
---

# Integration Modules Documentation

## Overview
The `integrations/` directory contains modules that handle external service integrations including Google Sheets, Riot Games API, IGN verification, and specialized sheet optimization systems.

## Module Details

### `integrations/__init__.py`
- **Purpose**: Integration package initialization and exports
- **Key Functions**: Module imports and package setup
- **Dependencies**: External integration modules

### `integrations/sheets.py`
- **Purpose**: Google Sheets integration and data synchronization (43,741 lines)
- **Key Functions**:
  - `get_sheet_for_guild()` - Open correct Google Sheet with error handling
  - `refresh_sheet_cache()` - Async cache refresh with performance optimization
  - `reset_registered_roles_and_sheet()` - Role management with sheet updates
  - `reset_checked_in_roles_and_sheet()` - Check-in role management
  - Sheet data retrieval and caching with asyncio support
  - Batch write operations with comprehensive error handling
  - Multi-source authentication (file and environment)
- **Dependencies**: gspread, oauth2client, asyncio, threading, sheet_optimizer
- **Used By**: Core commands, tournament management, all data operations
- **Caching**: 10-minute refresh cycle with thread-safe operations using cache_lock
- **Security**: Multiple authentication methods with proper error handling
- **Recent Changes**: Enhanced async support, improved caching, better error recovery

### `integrations/riot_api.py`
- **Purpose**: Riot Games API integration for player verification (9,454 lines)
- **Key Functions**:
  - Player account verification with regional routing
  - Match history retrieval for TFT (Teamfight Tactics)
  - Rank and statistics fetching
  - API rate limiting with custom exceptions
  - Regional endpoint mapping (NA, EUW, KR, etc.)
  - Platform-specific API calls
- **Dependencies**: Riot Games API, aiohttp, custom exceptions
- **Used By**: Player registration, verification systems
- **Rate Limits**: Custom RateLimitError handling with retry logic
- **API Endpoints**: Regional routing for TFT Match API and Summoner API

### `integrations/ign_verification.py`
- **Purpose**: IGN (In-Game Name) validation system (4,522 lines)
- **Key Functions**:
  - IGN format validation
  - Duplicate IGN detection
  - IGN assignment and management
  - Verification workflows
- **Dependencies**: Validation helpers, persistence
- **Used By**: Registration, tournament management

### `integrations/sheet_integration.py`
- **Purpose**: Advanced sheet integration bridging config-based and persistence-based systems (18,846 lines)
- **Key Functions**:
  - `get_sheet_and_column_config()` - Bridge configuration systems
  - `SheetIntegrationHelper` - Class for handling integration complexity
  - Complex data synchronization between multiple systems
  - Data transformation and mapping workflows
- **Dependencies**: Sheets API, persistence layer, config system
- **Used By**: Tournament operations requiring both config and persistence data

### `integrations/sheet_base.py`
- **Purpose**: Base functionality and common operations for all sheet modules (4,773 lines)
- **Key Functions**:
  - `get_sheet_for_guild()` - Base sheet opening functionality
  - Base exception classes (`SheetsError`, `AuthenticationError`)
  - Common sheet operations and connection management
  - Shared utilities and error handling patterns
- **Dependencies**: Google Sheets API, gspread
- **Used By**: All sheet-related modules as foundation
- **Note**: Duplicated functionality from integrations/sheets.py for modularity

### `integrations/sheet_utils.py`
- **Purpose**: Utility functions and helpers for sheet operations (3,713 lines)
- **Key Functions**:
  - Cell manipulation utilities
  - Data formatting helpers
  - Sheet structure analysis tools
  - Common validation and formatting functions
- **Dependencies**: Google Sheets API, dataclasses
- **Used By**: All sheet operation modules for common functionality

### `integrations/sheet_optimizer.py`
- **Purpose**: Performance optimization and batch operations for sheets (9,774 lines)
- **Key Functions**:
  - `SheetDataOptimizer` - Main optimization class
  - `fetch_sheet_data_batch()` - Optimized batch data retrieval
  - `fetch_required_columns_batch()` - Selective column fetching
  - `update_cells_batch()` - Batch cell updates
  - `detect_columns_optimized()` - Optimized column detection
  - Performance monitoring and caching strategies
- **Dependencies**: asyncio, Google Sheets API, dataclasses
- **Used By**: High-volume sheet operations and performance-critical paths
- **Performance**: Significantly reduces API calls and improves response times

### `integrations/sheet_detector.py`
- **Purpose**: Automatic sheet structure detection and column mapping (12,627 lines)
- **Key Classes**:
  - `ColumnDetection` - Dataclass for column detection results
  - `ColumnMapping` - Dataclass for column mapping information
  - `SheetColumnDetector` - Main detection class
- **Key Functions**:
  - `detect_sheet_columns()` - Automatic column detection
  - Schema analysis and format validation
  - Intelligent column mapping discovery
- **Dependencies**: dataclasses, Google Sheets API
- **Used By**: Sheet setup, configuration, and dynamic column management
- **Features**: Automatic detection of required columns with fallback strategies

## Integration Patterns

### Data Flow
```
Discord Commands → Integration Module → External API → Data Processing → Bot Response
     ↓                ↓                  ↓            ↓              ↓
User Request → API Call → External Service → Data Transform → Discord Embed
```

### Error Handling
- **API Failures**: Graceful degradation with user notifications
- **Rate Limits**: Automatic retry with exponential backoff
- **Authentication**: Token refresh and reconnection logic
- **Data Validation**: Schema validation before processing

### Caching Strategy
- **Google Sheets**: 10-minute cache with invalidation
- **Riot API**: Per-user cache with TTL
- **IGN Data**: Real-time with optional caching
- **Sheet Structure**: Cache until manual refresh

## Key Integration Points
- **Sheets Integration**: Primary data store for tournament information
- **Riot API**: Player verification and statistics
- **IGN System**: Player identity management
- **Sheet Optimization**: Performance for large datasets

## Security Considerations
- **API Keys**: Secure storage and rotation
- **Rate Limiting**: Prevent API abuse
- **Data Privacy**: Minimal data collection
- **Authentication**: OAuth 2.0 for Google Sheets

## Recent Updates (2025-06-17)
- **Added**: IGN verification system
- **Enhanced**: Sheet optimization with better caching
- **Improved**: Error handling for API failures
- **Updated**: Rate limiting and performance optimization
- **Documentation**: Updated line counts and module descriptions to match current codebase

## Configuration Requirements
- **Google Sheets**: API credentials and sheet IDs
- **Riot API**: API key with proper permissions
- **IGN System**: Configuration for validation rules
- **Sheet Optimization**: Performance tuning parameters

---
**Module Count**: 9 integration modules  
**Documentation Status**: Complete  
**Last Reviewed**: 2025-06-17
