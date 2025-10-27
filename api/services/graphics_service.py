"""
Service layer for graphics management.

Acts as the orchestration layer between the FastAPI routers and the underlying
SQLAlchemy models, exposing operations as simple Python methods while raising
domain-specific `ServiceError`s when something goes wrong.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from api.services.errors import ConflictError, NotFoundError
from ..models import Archive, CanvasLock, Graphic
from ..schemas.graphics import (
    CanvasLockCreate,
    GraphicCreate,
    GraphicUpdate,
    LockStatusResponse,
)


class GraphicsService:
    """Service for managing graphics and canvas locks."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _utcnow() -> datetime:
        """Return a timezone-aware UTC datetime."""
        return datetime.now(UTC)

    # --------------------------------------------------------------------- #
    # Utility helpers
    # --------------------------------------------------------------------- #
    def _serialize_graphic(self, graphic: Graphic) -> Dict[str, Any]:
        return {
            "id": graphic.id,
            "title": graphic.title,
            "event_name": graphic.event_name,
            "data_json": graphic.data_json,
            "created_by": graphic.created_by,
            "created_at": graphic.created_at,
            "updated_at": graphic.updated_at,
            "archived": graphic.archived,
        }

    def _serialize_lock(self, lock: CanvasLock) -> Dict[str, Any]:
        return {
            "id": lock.id,
            "graphic_id": lock.graphic_id,
            "user_name": lock.user_name,
            "locked": lock.locked,
            "locked_at": lock.locked_at,
            "expires_at": lock.expires_at,
        }

    def _get_graphic_or_error(self, graphic_id: int) -> Graphic:
        graphic = (
            self.db.query(Graphic)
            .filter(Graphic.id == graphic_id)
            .first()
        )
        if not graphic:
            raise NotFoundError(f"Graphic {graphic_id} was not found.")
        return graphic

    def _get_active_lock_model(self, graphic_id: int) -> Optional[CanvasLock]:
        return (
            self.db.query(CanvasLock)
            .filter(
                and_(
                    CanvasLock.graphic_id == graphic_id,
                    CanvasLock.locked.is_(True),
                    CanvasLock.expires_at > self._utcnow(),
                )
            )
            .first()
        )

    # --------------------------------------------------------------------- #
    # CRUD operations
    # --------------------------------------------------------------------- #
    def create_graphic(self, graphic: GraphicCreate, created_by: str) -> Dict[str, Any]:
        """Create a new graphic."""
        db_graphic = Graphic(
            title=graphic.title,
            event_name=graphic.event_name,
            data_json=json.dumps(graphic.data_json or {}),
            created_by=created_by,
            archived=False,
        )

        self.db.add(db_graphic)
        self.db.commit()
        self.db.refresh(db_graphic)
        return self._serialize_graphic(db_graphic)

    def get_graphics(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Return all graphics, optionally including archived ones."""
        query = self.db.query(Graphic)
        if not include_archived:
            query = query.filter(Graphic.archived.is_(False))

        graphics = query.order_by(Graphic.updated_at.desc()).all()
        return [self._serialize_graphic(graphic) for graphic in graphics]

    def get_graphic_by_id(self, graphic_id: int) -> Dict[str, Any]:
        """Return a graphic by ID or raise ``NotFoundError``."""
        graphic = self._get_graphic_or_error(graphic_id)
        return self._serialize_graphic(graphic)

    def update_graphic(
        self,
        graphic_id: int,
        graphic_update: GraphicUpdate,
        user_name: str,
    ) -> Dict[str, Any]:
        """Update an existing graphic."""
        graphic = self._get_graphic_or_error(graphic_id)

        if graphic_update.title is not None:
            graphic.title = graphic_update.title
        if graphic_update.event_name is not None:
            graphic.event_name = graphic_update.event_name
        if graphic_update.data_json is not None:
            graphic.data_json = graphic_update.data_json

        graphic.updated_at = self._utcnow()
        self.db.commit()
        self.db.refresh(graphic)

        return self._serialize_graphic(graphic)

    def duplicate_graphic(
        self,
        graphic_id: int,
        user_name: str,
        new_title: Optional[str] = None,
        new_event_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a duplicate of an existing graphic."""
        source = self._get_graphic_or_error(graphic_id)
        duplicate = Graphic(
            title=new_title or f"{source.title} (Copy)",
            event_name=new_event_name if new_event_name is not None else source.event_name,
            data_json=source.data_json,
            created_by=user_name,
            archived=False,
        )

        self.db.add(duplicate)
        self.db.commit()
        self.db.refresh(duplicate)

        return self._serialize_graphic(duplicate)

    def delete_graphic(self, graphic_id: int, user_name: str, is_admin: bool = False) -> None:
        """
        Soft-delete (archive) a graphic.

        Raises:
            NotFoundError: if the graphic does not exist.
            ConflictError: if the graphic is currently locked.
        """
        graphic = self._get_graphic_or_error(graphic_id)
        lock = self._get_active_lock_model(graphic_id)
        if lock and lock.user_name != user_name and not is_admin:
            raise ConflictError("Graphic is locked by another user.")

        graphic.archived = True
        graphic.updated_at = self._utcnow()
        self.db.commit()

    # --------------------------------------------------------------------- #
    # Lock management
    # --------------------------------------------------------------------- #
    def acquire_lock(self, lock_request: CanvasLockCreate) -> Dict[str, Any]:
        """Acquire or extend a lock for editing a graphic."""
        existing_lock = self._get_active_lock_model(lock_request.graphic_id)

        if existing_lock and existing_lock.user_name != lock_request.user_name:
            raise ConflictError("Graphic is already locked by another user.")

        if existing_lock:
            existing_lock.expires_at = self._utcnow() + timedelta(minutes=30)
            self.db.commit()
            self.db.refresh(existing_lock)
            return self._serialize_lock(existing_lock)

        lock = CanvasLock(
            graphic_id=lock_request.graphic_id,
            user_name=lock_request.user_name,
            locked=True,
            locked_at=self._utcnow(),
            expires_at=self._utcnow() + timedelta(minutes=5),
        )
        self.db.add(lock)
        self.db.commit()
        self.db.refresh(lock)
        return self._serialize_lock(lock)

    def release_lock(self, graphic_id: int, user_name: str) -> None:
        """
        Release a lock owned by the caller.

        Raises:
            NotFoundError: if no active lock exists for the user.
        """
        lock = (
            self.db.query(CanvasLock)
            .filter(
                and_(
                    CanvasLock.graphic_id == graphic_id,
                    CanvasLock.user_name == user_name,
                    CanvasLock.locked.is_(True),
                )
            )
            .first()
        )
        if not lock:
            raise NotFoundError("No active lock found for this user.")

        lock.locked = False
        self.db.commit()

    def get_active_lock(self, graphic_id: int) -> Optional[Dict[str, Any]]:
        """Return the active lock for a graphic, if any."""
        lock = self._get_active_lock_model(graphic_id)
        return self._serialize_lock(lock) if lock else None

    def get_lock_status(self, graphic_id: int, user_name: str) -> LockStatusResponse:
        """Return lock status information for the caller."""
        lock = self.get_active_lock(graphic_id)
        if not lock:
            return LockStatusResponse(locked=False, lock_info=None, can_edit=True)

        return LockStatusResponse(
            locked=True,
            lock_info=lock,
            can_edit=lock["user_name"] == user_name,
        )

    def cleanup_expired_locks(self) -> int:
        """Unlock any expired locks."""
        expired_locks = (
            self.db.query(CanvasLock)
            .filter(
                or_(
                    CanvasLock.expires_at <= self._utcnow(),
                    CanvasLock.locked.is_(False),
                )
            )
            .all()
        )

        count = len(expired_locks)
        for lock in expired_locks:
            lock.locked = False

        self.db.commit()
        return count

    def refresh_lock(self, graphic_id: int, user_name: str) -> Dict[str, Any]:
        """Extend an existing lock owned by the caller."""
        lock = (
            self.db.query(CanvasLock)
            .filter(
                and_(
                    CanvasLock.graphic_id == graphic_id,
                    CanvasLock.user_name == user_name,
                    CanvasLock.locked.is_(True),
                    CanvasLock.expires_at > self._utcnow(),
                )
            )
            .first()
        )

        if not lock:
            raise NotFoundError("No active lock to refresh for this user.")

        lock.expires_at = self._utcnow() + timedelta(minutes=5)
        self.db.commit()
        self.db.refresh(lock)
        return {
            "lock": self._serialize_lock(lock),
            "success": True,
            "message": "Lock refreshed successfully",
        }

    # --------------------------------------------------------------------- #
    # Archive operations
    # --------------------------------------------------------------------- #
    def archive_graphic(self, graphic_id: int, user_name: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Archive a graphic with an optional reason."""
        graphic = self._get_graphic_or_error(graphic_id)
        lock = self._get_active_lock_model(graphic_id)
        if lock and lock.user_name != user_name:
            raise ConflictError("Cannot archive while another user holds the lock.")

        archive = Archive(graphic_id=graphic_id, archived_by=user_name, reason=reason)
        graphic.archived = True
        graphic.updated_at = self._utcnow()

        self.db.add(archive)
        self.db.commit()
        self.db.refresh(archive)

        return {
            "success": True,
            "message": "Graphic archived successfully",
            "graphic_id": graphic_id,
            "archived_at": archive.archived_at,
        }

    def restore_graphic(self, graphic_id: int, user_name: str) -> Dict[str, Any]:
        """Restore a previously archived graphic."""
        graphic = self._get_graphic_or_error(graphic_id)
        if not graphic.archived:
            raise ConflictError("Graphic is not archived.")

        graphic.archived = False
        graphic.updated_at = self._utcnow()

        restore_record = Archive(
            graphic_id=graphic_id,
            archived_by=user_name,
            reason="Restored from archive",
        )

        self.db.add(restore_record)
        self.db.commit()
        self.db.refresh(restore_record)

        return {
            "success": True,
            "message": "Graphic restored successfully",
            "graphic_id": graphic_id,
            "restored_at": restore_record.archived_at,
        }

    def permanent_delete_graphic(self, graphic_id: int, user_name: str) -> None:
        """
        Permanently delete a graphic, regardless of its archived state.

        Raises:
            NotFoundError: if the graphic does not exist.
            ConflictError: if the graphic is locked by another user.
        """
        graphic = self._get_graphic_or_error(graphic_id)

        lock = self._get_active_lock_model(graphic_id)
        if lock and lock.user_name != user_name:
            raise ConflictError("Cannot delete while another user holds the lock.")

        reason = "Permanently deleted"
        if not graphic.archived:
            reason = "Permanently deleted (active state)"

        archive_record = Archive(
            graphic_id=graphic_id,
            archived_by=user_name,
            reason=reason,
        )

        self.db.add(archive_record)
        self.db.delete(graphic)
        self.db.commit()

    # --------------------------------------------------------------------- #
    # Simplified Element System Support
    # --------------------------------------------------------------------- #
    def get_ranked_players(
        self,
        *,
        tournament_id: Optional[str] = None,
        guild_id: Optional[str] = None,
        sort_by: str = "total_points",
        sort_order: str = "desc",
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Get ranked player data for simplified element system.
        
        This method pulls from the latest scoreboard snapshot and returns
        player data sorted by the specified criteria.
        """
        from api.services import StandingsService
        standings_service = StandingsService(self.db)
        
        # Get the latest snapshot
        if tournament_id:
            snapshot = standings_service.get_latest_snapshot(tournament_id=tournament_id)
        elif guild_id:
            snapshot = standings_service.get_latest_snapshot(guild_id=guild_id)
        else:
            # If no filters specified, get the most recent snapshot
            snapshot = standings_service.get_latest_snapshot()
        
        if not snapshot:
            return {
                "players": [],
                "total": 0,
                "snapshot_id": None,
                "message": "No player data available"
            }
        
        # Convert entries to player data format
        players = []
        for entry in snapshot.entries:
            players.append({
                "player_name": entry.player_name,
                "total_points": entry.total_points,
                "standing_rank": entry.standing_rank or 0,
                "player_id": entry.player_id,
                "discord_id": entry.discord_id,
                "riot_id": entry.riot_id,
                "round_scores": entry.round_scores or {},
            })
        
        # Sort players based on criteria
        valid_sort_fields = {"total_points", "player_name", "standing_rank"}
        if sort_by not in valid_sort_fields:
            sort_by = "total_points"
        
        reverse_order = sort_order.lower() == "desc"
        
        if sort_by == "player_name":
            players.sort(key=lambda x: x["player_name"].lower(), reverse=reverse_order)
        else:
            players.sort(key=lambda x: x[sort_by], reverse=reverse_order)
        
        # Apply limit
        limited_players = players[:limit] if limit > 0 else players
        
        return {
            "players": limited_players,
            "total": len(limited_players),
            "snapshot_id": snapshot.id,
            "snapshot_created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
            "tournament_id": snapshot.tournament_id,
            "tournament_name": snapshot.tournament_name,
        }

    # --------------------------------------------------------------------- #
    # Public helpers
    # --------------------------------------------------------------------- #
    def public_view(self, graphic_id: int) -> Dict[str, Any]:
        """
        Retrieve a graphic for public consumption.

        Raises:
            NotFoundError: if the graphic does not exist or is archived.
        """
        graphic = self._get_graphic_or_error(graphic_id)
        if graphic.archived:
            raise NotFoundError("Graphic not available.")

        serialized = self._serialize_graphic(graphic)
        return {
            "id": serialized["id"],
            "title": serialized["title"],
            "data_json": serialized["data_json"],
        }
