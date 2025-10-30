"""
Graphics API endpoints.

Routers delegate to the graphics service and keep controller logic minimal.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Query
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import NoResultFound

from api.auth import TokenData
from api.dependencies import (
    get_active_user,
    get_graphics_service,
    require_roles,
    require_write_access,
)
from api.services.graphics_service import GraphicsService
from api.utils.service_runner import execute_service
from ..schemas.graphics import (
    ArchiveActionRequest,
    ArchiveListResponse,
    ArchiveResponse,
    CanvasLockCreate,
    CanvasLockResponse,
    GraphicCreate,
    GraphicListResponse,
    GraphicResponse,
    GraphicUpdate,
    LockStatusResponse,
)

router = APIRouter()


# --------------------------------------------------------------------------- #
# Graphics CRUD
# --------------------------------------------------------------------------- #
@router.post("/graphics", response_model=GraphicResponse)
async def create_graphic(
    graphic: GraphicCreate,
    current_user: TokenData = Depends(require_write_access),
    service: GraphicsService = Depends(get_graphics_service),
) -> GraphicResponse:
    payload = await execute_service(service.create_graphic, graphic, current_user.username)
    return GraphicResponse(**payload)


@router.get("/graphics", response_model=GraphicListResponse)
async def get_graphics(
    include_archived: bool = Query(False, description="Include archived graphics"),
    _user: TokenData = Depends(get_active_user),
    service: GraphicsService = Depends(get_graphics_service),
) -> GraphicListResponse:
    payload = await execute_service(service.get_graphics, include_archived=include_archived)
    graphics = [GraphicResponse(**graphic) for graphic in payload]
    return GraphicListResponse(graphics=graphics, total=len(graphics))


@router.get("/graphics/{graphic_id}", response_model=GraphicResponse)
async def get_graphic(
    graphic_id: int,
    _user: TokenData = Depends(get_active_user),
    service: GraphicsService = Depends(get_graphics_service),
) -> GraphicResponse:
    payload = await execute_service(service.get_graphic_by_id, graphic_id)
    return GraphicResponse(**payload)


@router.put("/graphics/{graphic_id}", response_model=GraphicResponse)
async def update_graphic(
    graphic_id: int,
    graphic_update: GraphicUpdate,
    current_user: TokenData = Depends(require_write_access),
    service: GraphicsService = Depends(get_graphics_service),
) -> GraphicResponse:
    payload = await execute_service(
        service.update_graphic,
        graphic_id,
        graphic_update,
        current_user.username,
    )
    return GraphicResponse(**payload)


@router.post("/graphics/{graphic_id}/duplicate", response_model=GraphicResponse)
async def duplicate_graphic(
    graphic_id: int,
    duplicate_request: Optional[Dict[str, Any]] = Body(None),
    new_title: Optional[str] = None,
    new_event_name: Optional[str] = None,
    current_user: TokenData = Depends(require_write_access),
    service: GraphicsService = Depends(get_graphics_service),
) -> GraphicResponse:
    title = new_title
    event_name = new_event_name
    if duplicate_request:
        title = duplicate_request.get("new_title", title)
        event_name = duplicate_request.get("new_event_name", event_name)

    payload = await execute_service(
        service.duplicate_graphic,
        graphic_id,
        current_user.username,
        title,
        event_name,
    )
    return GraphicResponse(**payload)


@router.delete("/graphics/{graphic_id}")
async def delete_graphic(
    graphic_id: int,
    current_user: TokenData = Depends(require_write_access),
    service: GraphicsService = Depends(get_graphics_service),
) -> dict:
    await execute_service(
        service.delete_graphic,
        graphic_id,
        current_user.username,
        current_user.is_admin,
    )
    return {"message": "Graphic deleted successfully"}


@router.get("/events")
async def get_event_names(
    _user: TokenData = Depends(get_active_user),
    service: GraphicsService = Depends(get_graphics_service),
) -> list[str]:
    """Get list of unique event names from all graphics."""
    payload = await execute_service(service.get_event_names)
    return payload


@router.delete("/graphics/{graphic_id}/permanent")
async def permanent_delete_graphic(
    graphic_id: int,
    _admin: TokenData = Depends(require_roles("Administrator")),
    service: GraphicsService = Depends(get_graphics_service),
) -> dict:
    await execute_service(service.permanent_delete_graphic, graphic_id, _admin.username)
    return {"message": "Graphic permanently deleted successfully"}


# --------------------------------------------------------------------------- #
# Lock management
# --------------------------------------------------------------------------- #
@router.post("/lock/{graphic_id}", response_model=CanvasLockResponse)
async def acquire_lock(
    graphic_id: int,
    lock_request: CanvasLockCreate,
    current_user: TokenData = Depends(require_write_access),
    service: GraphicsService = Depends(get_graphics_service),
) -> CanvasLockResponse:
    # Ensure the graphic_id in the URL matches the one in the request body
    lock_request.graphic_id = graphic_id
    payload = await execute_service(service.acquire_lock, lock_request)
    return CanvasLockResponse(**payload)


@router.delete("/lock/{graphic_id}")
async def release_lock(
    graphic_id: int,
    session_request: dict = Body(...),
    current_user: TokenData = Depends(require_write_access),
    service: GraphicsService = Depends(get_graphics_service),
) -> dict:
    session_id = session_request.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    await execute_service(service.release_lock, graphic_id, session_id, current_user.username)
    return {"message": "Lock released successfully"}


@router.get("/lock/{graphic_id}/status", response_model=LockStatusResponse)
async def get_lock_status(
    graphic_id: int,
    session_id: Optional[str] = Query(None, description="Session ID for lock ownership check"),
    current_user: TokenData = Depends(get_active_user),
    service: GraphicsService = Depends(get_graphics_service),
) -> LockStatusResponse:
    return await execute_service(service.get_lock_status, graphic_id, session_id, current_user.username)


@router.post("/lock/{graphic_id}/refresh", response_model=CanvasLockResponse)
async def refresh_lock(
    graphic_id: int,
    session_request: dict = Body(...),
    current_user: TokenData = Depends(require_write_access),
    service: GraphicsService = Depends(get_graphics_service),
) -> CanvasLockResponse:
    session_id = session_request.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    payload = await execute_service(service.refresh_lock, graphic_id, session_id, current_user.username)
    return CanvasLockResponse(**payload["lock"])


@router.get("/lock/status")
async def get_all_lock_status(
    _user: TokenData = Depends(get_active_user),
) -> dict:
    # Still pending implementation in the service layer.
    return {"message": "All lock status endpoint not yet implemented"}


# --------------------------------------------------------------------------- #
# Archive operations
# --------------------------------------------------------------------------- #
@router.post("/archive/{graphic_id}", response_model=ArchiveResponse)
async def archive_graphic(
    graphic_id: int,
    archive_request: Optional[ArchiveActionRequest] = Body(None),
    current_user: TokenData = Depends(require_write_access),
    service: GraphicsService = Depends(get_graphics_service),
) -> ArchiveResponse:
    reason = archive_request.reason if archive_request else None
    payload = await execute_service(
        service.archive_graphic,
        graphic_id,
        current_user.username,
        reason,
    )
    return ArchiveResponse(**payload)


@router.post("/archive/{graphic_id}/restore", response_model=ArchiveResponse)
async def restore_graphic(
    graphic_id: int,
    current_user: TokenData = Depends(require_write_access),
    service: GraphicsService = Depends(get_graphics_service),
) -> ArchiveResponse:
    payload = await execute_service(service.restore_graphic, graphic_id, current_user.username)
    return ArchiveResponse(**payload)


@router.get("/archive", response_model=ArchiveListResponse)
async def get_archived_graphics(
    current_user: TokenData = Depends(get_active_user),
    service: GraphicsService = Depends(get_graphics_service),
) -> ArchiveListResponse:
    payload = await execute_service(service.get_graphics, include_archived=True)
    archived = [GraphicResponse(**graphic) for graphic in payload if graphic["archived"]]
    return ArchiveListResponse(
        archives=archived,
        total=len(archived),
        can_delete=current_user.is_admin,
    )


@router.delete("/archive/{graphic_id}/permanent")
async def permanent_delete_archive(
    graphic_id: int,
    _admin: TokenData = Depends(require_roles("Administrator")),
    service: GraphicsService = Depends(get_graphics_service),
) -> dict:
    await execute_service(service.permanent_delete_graphic, graphic_id, _admin.username)
    return {"message": "Graphic permanently deleted successfully"}


@router.post("/maintenance/cleanup-locks")
async def cleanup_expired_locks(
    _admin: TokenData = Depends(require_roles("Administrator")),
    service: GraphicsService = Depends(get_graphics_service),
) -> dict:
    cleaned_count = await execute_service(service.cleanup_expired_locks)
    return {
        "message": f"Cleaned up {cleaned_count} expired locks",
        "cleaned_count": cleaned_count,
    }


# --------------------------------------------------------------------------- #
# Player data for simplified elements
# --------------------------------------------------------------------------- #
@router.get("/players/ranked")
async def get_ranked_players(
    tournament_id: Optional[str] = Query(None, description="Tournament ID to filter by"),
    guild_id: Optional[str] = Query(None, description="Guild ID to filter by"),
    sort_by: str = Query("total_points", description="Sort field: total_points, player_name, standing_rank"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    limit: int = Query(50, description="Maximum number of players to return"),
    service: GraphicsService = Depends(get_graphics_service),
) -> dict:
    """Get ranked player data for simplified element system."""
    return await execute_service(
        service.get_ranked_players,
        tournament_id=tournament_id,
        guild_id=guild_id,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit
    )


# --------------------------------------------------------------------------- #
# Public view
# --------------------------------------------------------------------------- #
@router.get("/graphics/{graphic_id}/view")
async def view_graphic(
    graphic_id: int,
    service: GraphicsService = Depends(get_graphics_service),
) -> dict:
    return await execute_service(service.public_view, graphic_id)
