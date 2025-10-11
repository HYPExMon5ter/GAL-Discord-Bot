"""
User business logic service
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from core.data_access.user_repository import UserRepository
from ..schemas.user import UserCreate, UserUpdate, UserList

class UserService:
    """
    Service class for user business logic
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    async def get_users(
        self, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> UserList:
        """
        Get list of users with optional filtering
        """
        users, total = await self.user_repo.get_all(
            skip=skip, 
            limit=limit, 
            is_active=is_active
        )
        
        return UserList(
            users=users,
            total=total,
            page=skip // limit + 1 if limit > 0 else 1,
            per_page=limit
        )
    
    async def get_user(self, user_id: int):
        """
        Get a specific user by ID
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        return user
    
    async def get_user_by_discord_id(self, discord_id: str):
        """
        Get a user by Discord ID
        """
        user = await self.user_repo.get_by_discord_id(discord_id)
        if not user:
            raise ValueError(f"User with Discord ID {discord_id} not found")
        return user
    
    async def create_user(self, user_data: UserCreate):
        """
        Create a new user
        """
        # Check if user with Discord ID already exists
        existing = await self.user_repo.get_by_discord_id(user_data.discord_id)
        if existing:
            raise ValueError(f"User with Discord ID {user_data.discord_id} already exists")
        
        return await self.user_repo.create(user_data.dict())
    
    async def update_user(self, user_id: int, user_data: UserUpdate):
        """
        Update an existing user
        """
        # Check if user exists
        existing = await self.user_repo.get_by_id(user_id)
        if not existing:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Update user
        update_data = {k: v for k, v in user_data.dict().items() if v is not None}
        return await self.user_repo.update(user_id, update_data)
    
    async def delete_user(self, user_id: int):
        """
        Delete a user
        """
        # Check if user exists
        existing = await self.user_repo.get_by_id(user_id)
        if not existing:
            raise ValueError(f"User with ID {user_id} not found")
        
        return await self.user_repo.delete(user_id)
    
    async def get_user_statistics(self):
        """
        Get user statistics
        """
        total_users, active_users = await self.user_repo.get_statistics()
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "activity_rate": (active_users / total_users * 100) if total_users > 0 else 0
        }
