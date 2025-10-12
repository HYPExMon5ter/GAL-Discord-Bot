"""
Common dependencies for the API
"""

from typing import Generator

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

from dotenv import load_dotenv
load_dotenv('.env.local')

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dashboard.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models to ensure they're created
from .models import Base
Base.metadata.create_all(bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    Get database session dependency
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Legacy compatibility
def get_database_session() -> Generator[Session, None, None]:
    """
    Get database session dependency (legacy name)
    """
    return get_db()

# Authentication dependencies will be imported in main.py to avoid circular imports
# These will be defined in main.py and re-exported here
