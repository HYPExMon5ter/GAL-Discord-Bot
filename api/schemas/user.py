"""
User schemas
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

class User(BaseModel):
    id: int
    discord_id: str
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    discord_id: str
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None

class UserList(BaseModel):
    users: List[User]
    total: int
    page: int
    per_page: int
