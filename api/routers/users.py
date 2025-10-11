"""
User API endpoints
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..dependencies import get_database_session, get_current_authenticated_user
from ..services.user_service import UserService
from ..schemas.user import (
    User, 
    UserCreate, 
    UserUpdate, 
    UserList
)
from ..main import TokenData

router = APIRouter()

@router.get("/", response_model=UserList)
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get list of users with pagination and optional filtering
    """
    try:
        service = UserService(db)
        return await service.get_users(skip=skip, limit=limit, is_active=is_active)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get a specific user by ID
    """
    try:
        service = UserService(db)
        return await service.get_user(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/discord/{discord_id}", response_model=User)
async def get_user_by_discord_id(
    discord_id: str,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get a user by Discord ID
    """
    try:
        service = UserService(db)
        return await service.get_user_by_discord_id(discord_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=User)
async def create_user(
    user_data: UserCreate,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Create a new user
    """
    try:
        service = UserService(db)
        return await service.create_user(user_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Update an existing user
    """
    try:
        service = UserService(db)
        return await service.update_user(user_id, user_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Delete a user
    """
    try:
        service = UserService(db)
        await service.delete_user(user_id)
        return {"message": f"User {user_id} deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics/overview")
async def get_user_statistics(
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get user statistics overview
    """
    try:
        service = UserService(db)
        return await service.get_user_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
