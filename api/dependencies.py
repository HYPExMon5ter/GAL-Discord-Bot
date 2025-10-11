"""
Common dependencies for the API
"""

from typing import Generator

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.data_access.connection_manager import get_db_session
from .main import verify_token, TokenData

def get_database_session() -> Generator[Session, None, None]:
    """
    Get database session dependency
    """
    session = next(get_db_session())
    try:
        yield session
    finally:
        session.close()

def get_current_authenticated_user(token_data: TokenData = Depends(verify_token)) -> TokenData:
    """
    Dependency to ensure user is authenticated
    """
    return token_data
