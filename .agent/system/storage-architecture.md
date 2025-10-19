---
id: system.storage_architecture
version: 1.0
last_updated: 2025-01-17
tags: [storage, database, architecture, persistence, fallback]
---

# Storage Architecture

## Overview

The Guardian Angel League bot implements a robust 3-layer storage system that ensures data persistence and reliability across different deployment environments.

## Storage Layers

### Layer 1: Primary Storage (PostgreSQL)
**Purpose**: Production-grade database with full features
**Use Case**: Production environments, Railway deployments

**Configuration**: See `config.py` for database URL configuration and `core/data_access/connection_manager.py` for connection handling.

### Layer 2: Fallback Storage (SQLite)
**Purpose**: Development and offline scenarios
**Use Case**: Local development, PostgreSQL connection failures

**Configuration**: See `storage/fallback.db` and `core/storage_service.py` for fallback storage implementation.

### Layer 3: Emergency Storage (JSON Files)
**Purpose**: Legacy emergency fallback
**Use Case**: Complete database unavailability, migration scenarios

## Storage Service Architecture

### Core Components

#### Storage Service (`core/storage_service.py`)
**Purpose**: Unified storage abstraction layer
**Responsibilities**:
- Database connection management
- Automatic fallback switching
- Health monitoring
- Data migration
- Backup operations

## Configuration Management

### Environment Variables
See `.env` and `.env.local` files for database configuration. Key variables:
- `DATABASE_URL`: Database connection string (see `config.py` for usage)
- `RAILWAY_ENVIRONMENT_NAME`: Environment indicator (see `services/dashboard_manager.py`)

### Configuration Detection
Database type detection logic is implemented in `core/storage_service.py` in the `_is_postgresql_url()` method.

## Benefits

- **Reliability**: PostgreSQL with automatic fallback
- **Performance**: Connection pooling and optimized queries
- **Simplicity**: No database setup required (SQLite fallback)
- **Zero Downtime**: Automatic fallback prevents service interruption

---

**Architecture Version**: 1.0  
**Last Updated**: 2025-01-17
