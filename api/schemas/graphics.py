"""
Pydantic schemas for graphics management
"""

from datetime import datetime
from typing import Dict, Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class GraphicBase(BaseModel):
    """Base schema for graphics"""
    title: str = Field(..., min_length=1, max_length=255, description="Graphic title")
    event_name: str = Field(..., min_length=1, max_length=255, description="Event name (required)")
    data_json: Optional[Dict[str, Any]] = Field(default=None, description="Canvas data as JSON")


class GraphicCreate(GraphicBase):
    """Schema for creating a new graphic"""
    pass


class GraphicUpdate(BaseModel):
    """Schema for updating an existing graphic"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Graphic title")
    event_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Event name")
    data_json: Optional[str] = Field(None, description="Canvas data as JSON string")


class GraphicResponse(BaseModel):
    """Schema for graphic response"""
    id: int
    title: str
    event_name: Optional[str]
    data_json: Optional[str]  # Store as string in database, return as string in API
    created_by: str
    created_at: datetime
    updated_at: datetime
    archived: bool

    model_config = ConfigDict(from_attributes=True)


class GraphicListResponse(BaseModel):
    """Schema for graphics list response"""
    graphics: list[GraphicResponse]
    total: int


class CanvasLockBase(BaseModel):
    """Base schema for canvas locks"""
    graphic_id: int
    user_name: str


class CanvasLockCreate(CanvasLockBase):
    """Schema for creating a canvas lock"""
    pass


class CanvasLockResponse(CanvasLockBase):
    """Schema for canvas lock response"""
    id: int
    locked: bool
    locked_at: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LockStatusResponse(BaseModel):
    """Schema for lock status response"""
    locked: bool
    lock_info: Optional[CanvasLockResponse] = None
    can_edit: bool


class ArchiveActionRequest(BaseModel):
    """Schema for archive action requests"""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for archiving")


class ArchiveResponse(BaseModel):
    """Schema for archive action response"""
    success: bool
    message: str
    graphic_id: int
    archived_at: Optional[datetime] = None
    restored_at: Optional[datetime] = None


class ArchiveListResponse(BaseModel):
    """Schema for archive list response"""
    archives: list[GraphicResponse]
    total: int
    can_delete: bool  # Admin permission flag
