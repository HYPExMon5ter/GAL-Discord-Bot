"""
API router for graphics management
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..auth import get_current_user, TokenData
from ..schemas.graphics import (
    GraphicCreate, GraphicUpdate, GraphicResponse, GraphicListResponse,
    CanvasLockCreate, CanvasLockResponse, LockStatusResponse,
    ArchiveActionRequest, ArchiveResponse, ArchiveListResponse
)
from ..services.graphics_service import GraphicsService


router = APIRouter()


@router.post("/graphics", response_model=GraphicResponse)
async def create_graphic(
    graphic: GraphicCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new graphic
    """
    try:
        service = GraphicsService(db)
        result = service.create_graphic(graphic, current_user.username)
        return GraphicResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create graphic: {str(e)}"
        )


@router.get("/graphics", response_model=GraphicListResponse)
async def get_graphics(
    include_archived: bool = Query(False, description="Include archived graphics"),
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all graphics
    """
    try:
        service = GraphicsService(db)
        graphics = service.get_graphics(include_archived=include_archived)
        return GraphicListResponse(
            graphics=[GraphicResponse(**g) for g in graphics],
            total=len(graphics)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve graphics: {str(e)}"
        )


@router.get("/graphics/{graphic_id}", response_model=GraphicResponse)
async def get_graphic(
    graphic_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific graphic by ID
    """
    try:
        service = GraphicsService(db)
        graphic = service.get_graphic_by_id(graphic_id)
        
        if not graphic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Graphic not found"
            )
        
        return GraphicResponse(**graphic)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve graphic: {str(e)}"
        )


@router.put("/graphics/{graphic_id}", response_model=GraphicResponse)
async def update_graphic(
    graphic_id: int,
    graphic_update: GraphicUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing graphic
    """
    try:
        service = GraphicsService(db)
        
        # Check if user has permission to edit (owns the lock)
        lock_status = service.get_lock_status(graphic_id, current_user.username)
        if not lock_status.can_edit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Graphic is locked by another user"
            )
        
        result = service.update_graphic(graphic_id, graphic_update, current_user.username)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Graphic not found"
            )
        
        return GraphicResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update graphic: {str(e)}"
        )


@router.delete("/graphics/{graphic_id}")
async def delete_graphic(
    graphic_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a graphic (soft delete by archiving)
    """
    try:
        service = GraphicsService(db)
        success = service.delete_graphic(graphic_id, current_user.username)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Graphic not found or is locked"
            )
        
        return {"message": "Graphic deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete graphic: {str(e)}"
        )


# Canvas Lock Management
@router.post("/lock/{graphic_id}", response_model=CanvasLockResponse)
async def acquire_lock(
    graphic_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Acquire a canvas lock for editing
    """
    try:
        service = GraphicsService(db)
        lock_request = CanvasLockCreate(
            graphic_id=graphic_id,
            user_name=current_user.username
        )
        
        result = service.acquire_lock(lock_request)
        
        if not result.get("can_edit", True):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Graphic is locked by {result.get('locked_by', 'another user')}"
            )
        
        return CanvasLockResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acquire lock: {str(e)}"
        )


@router.delete("/lock/{graphic_id}")
async def release_lock(
    graphic_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Release a canvas lock
    """
    try:
        service = GraphicsService(db)
        success = service.release_lock(graphic_id, current_user.username)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active lock found for this graphic"
            )
        
        return {"message": "Lock released successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to release lock: {str(e)}"
        )


@router.get("/lock/{graphic_id}/status", response_model=LockStatusResponse)
async def get_lock_status(
    graphic_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get lock status for a graphic
    """
    try:
        service = GraphicsService(db)
        status = service.get_lock_status(graphic_id, current_user.username)
        return status
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get lock status: {str(e)}"
        )


@router.get("/lock/status")
async def get_all_lock_status(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get status of all active locks
    """
    try:
        service = GraphicsService(db)
        # This would need to be implemented in the service
        return {"message": "All lock status endpoint not yet implemented"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get lock status: {str(e)}"
        )


# Archive Management
@router.post("/archive/{graphic_id}", response_model=ArchiveResponse)
async def archive_graphic(
    graphic_id: int,
    archive_request: Optional[ArchiveActionRequest] = None,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Archive a graphic
    """
    try:
        service = GraphicsService(db)
        reason = archive_request.reason if archive_request else None
        
        result = service.archive_graphic(graphic_id, current_user.username, reason)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return ArchiveResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive graphic: {str(e)}"
        )


@router.post("/archive/{graphic_id}/restore", response_model=ArchiveResponse)
async def restore_graphic(
    graphic_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Restore an archived graphic
    """
    try:
        service = GraphicsService(db)
        result = service.restore_graphic(graphic_id, current_user.username)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return ArchiveResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore graphic: {str(e)}"
        )


@router.get("/archive", response_model=ArchiveListResponse)
async def get_archived_graphics(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all archived graphics
    """
    try:
        service = GraphicsService(db)
        graphics = service.get_graphics(include_archived=True)
        
        # Filter only archived graphics
        archived_graphics = [g for g in graphics if g["archived"]]
        
        # TODO: Implement admin check for delete permission
        can_delete = True  # Placeholder - should check user permissions
        
        return ArchiveListResponse(
            archives=[GraphicResponse(**g) for g in archived_graphics],
            total=len(archived_graphics),
            can_delete=can_delete
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve archived graphics: {str(e)}"
        )


@router.delete("/archive/{graphic_id}/permanent")
async def permanent_delete_archive(
    graphic_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently delete an archived graphic (admin only)
    """
    try:
        # TODO: Implement admin permission check
        is_admin = True  # Placeholder - should check user permissions
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # TODO: Implement permanent deletion
        return {"message": "Permanent deletion not yet implemented"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to permanently delete graphic: {str(e)}"
        )


# Maintenance endpoint
@router.post("/maintenance/cleanup-locks")
async def cleanup_expired_locks(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clean up expired locks (maintenance endpoint)
    """
    try:
        # TODO: Implement admin permission check
        is_admin = True  # Placeholder - should check user permissions
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        service = GraphicsService(db)
        cleaned_count = service.cleanup_expired_locks()
        
        return {
            "message": f"Cleaned up {cleaned_count} expired locks",
            "cleaned_count": cleaned_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup locks: {str(e)}"
        )
