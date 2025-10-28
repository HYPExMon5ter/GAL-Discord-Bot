"""
Common dependency helpers for the API layer.

Provides scoped database sessions, typed authentication contexts, and
service factory helpers so routers can remain thin.
"""

from __future__ import annotations

import os
from typing import Callable, Generator

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .auth import TokenData, get_current_user
from .services.configuration_service import ConfigurationService
from .services.graphics_service import GraphicsService
from .services.standings_aggregator import StandingsAggregator
from .services.standings_service import StandingsService
from .services.tournament_service import TournamentService
from .services.user_service import UserService

# Ensure environment variables are loaded with correct precedence
# Load .env first, then .env.local overrides from parent directory
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(parent_dir, ".env"))
load_dotenv(os.path.join(parent_dir, ".env.local"), override=True)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dashboard/dashboard.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models to ensure they're created exactly once at startup.
from .models import Base  # noqa: E402

Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Yield a scoped database session with rollback on failure.

    Ensures each request receives an isolated session and failures do not
    leak uncommitted changes into subsequent operations.
    """
    db = SessionLocal()
    try:
        yield db
        db.flush()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_database_session() -> Generator[Session, None, None]:
    """
    Backwards-compatible alias for `get_db`.
    """
    yield from get_db()


def get_active_user(token: TokenData = Depends(get_current_user)) -> TokenData:
    """
    Retrieve the authenticated user context for read-only endpoints.
    """
    return token


def require_write_access(user: TokenData = Depends(get_current_user)) -> TokenData:
    """
    Ensure the caller has write access (used for mutating endpoints).
    """
    if user.read_only:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only credentials cannot modify resources.",
        )
    return user


def require_roles(*required_roles: str) -> Callable[[TokenData], TokenData]:
    """
    Build a dependency that enforces the caller has one of the required roles.
    """
    normalized = {role.lower() for role in required_roles}

    def dependency(user: TokenData = Depends(get_current_user)) -> TokenData:
        if not normalized:
            return user
        roles = {role.lower() for role in user.roles or []}
        if normalized.isdisjoint(roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role permissions for this operation.",
            )
        return user

    return dependency


def _service_factory(service_cls):
    def factory(db: Session = Depends(get_db)):
        return service_cls(db)

    return factory


get_configuration_service = _service_factory(ConfigurationService)
get_graphics_service = _service_factory(GraphicsService)
get_standings_service = _service_factory(StandingsService)
get_tournament_service = _service_factory(TournamentService)
get_user_service = _service_factory(UserService)


def get_standings_aggregator(
    standings_service: StandingsService = Depends(get_standings_service),
) -> StandingsAggregator:
    """
    Provide a standings aggregator bound to the current database session.
    """
    return StandingsAggregator(standings_service)


__all__ = [
    "get_db",
    "get_database_session",
    "get_active_user",
    "require_write_access",
    "require_roles",
    "get_configuration_service",
    "get_graphics_service",
    "get_tournament_service",
    "get_user_service",
    "get_standings_service",
    "get_standings_aggregator",
]
