"""
User API endpoints.

Endpoints remain lean by relying on the UserService for all business logic,
with shared dependencies enforcing authentication and permissions.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.auth import TokenData
from api.dependencies import (
    get_active_user,
    get_user_service,
    require_write_access,
)
from api.services.user_service import UserService
from api.utils.service_runner import execute_service
from ..schemas.user import User, UserCreate, UserList, UserUpdate

router = APIRouter()


@router.get("/", response_model=UserList)
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    _user: TokenData = Depends(get_active_user),
    service: UserService = Depends(get_user_service),
) -> UserList:
    return await execute_service(service.get_users, skip=skip, limit=limit, is_active=is_active)


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: int,
    _user: TokenData = Depends(get_active_user),
    service: UserService = Depends(get_user_service),
) -> User:
    return await execute_service(service.get_user, user_id)


@router.get("/discord/{discord_id}", response_model=User)
async def get_user_by_discord_id(
    discord_id: str,
    _user: TokenData = Depends(get_active_user),
    service: UserService = Depends(get_user_service),
) -> User:
    return await execute_service(service.get_user_by_discord_id, discord_id)


@router.post("/", response_model=User)
async def create_user(
    user_data: UserCreate,
    _user: TokenData = Depends(require_write_access),
    service: UserService = Depends(get_user_service),
) -> User:
    return await execute_service(service.create_user, user_data)


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    _user: TokenData = Depends(require_write_access),
    service: UserService = Depends(get_user_service),
) -> User:
    return await execute_service(service.update_user, user_id, user_data)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    _user: TokenData = Depends(require_write_access),
    service: UserService = Depends(get_user_service),
) -> dict:
    await execute_service(service.delete_user, user_id)
    return {"message": f"User {user_id} deleted successfully"}


@router.get("/statistics/overview")
async def get_user_statistics(
    _user: TokenData = Depends(get_active_user),
    service: UserService = Depends(get_user_service),
) -> dict:
    return await execute_service(service.get_user_statistics)
