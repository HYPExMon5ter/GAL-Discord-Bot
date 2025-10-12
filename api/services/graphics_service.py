"""
Service layer for graphics management
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..dependencies import get_db
from ..schemas.graphics import (
    GraphicCreate, GraphicUpdate, CanvasLockCreate,
    LockStatusResponse, ArchiveActionRequest
)


class GraphicsService:
    """Service for managing graphics and canvas locks"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_graphic(self, graphic: GraphicCreate, created_by: str) -> Dict[str, Any]:
        """Create a new graphic"""
        # Import here to avoid circular imports
        from ..models import Graphic
        
        db_graphic = Graphic(
            title=graphic.title,
            data_json=graphic.data_json or {},
            created_by=created_by,
            archived=False
        )
        
        self.db.add(db_graphic)
        self.db.commit()
        self.db.refresh(db_graphic)
        
        return {
            "id": db_graphic.id,
            "title": db_graphic.title,
            "data_json": db_graphic.data_json,
            "created_by": db_graphic.created_by,
            "created_at": db_graphic.created_at,
            "updated_at": db_graphic.updated_at,
            "archived": db_graphic.archived
        }
    
    def get_graphics(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get all graphics, optionally including archived ones"""
        from ..models import Graphic
        
        query = self.db.query(Graphic)
        
        if not include_archived:
            query = query.filter(Graphic.archived == False)
        
        graphics = query.order_by(Graphic.updated_at.desc()).all()
        
        return [
            {
                "id": graphic.id,
                "title": graphic.title,
                "data_json": graphic.data_json,
                "created_by": graphic.created_by,
                "created_at": graphic.created_at,
                "updated_at": graphic.updated_at,
                "archived": graphic.archived
            }
            for graphic in graphics
        ]
    
    def get_graphic_by_id(self, graphic_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific graphic by ID"""
        from ..models import Graphic
        
        graphic = self.db.query(Graphic).filter(Graphic.id == graphic_id).first()
        
        if not graphic:
            return None
        
        return {
            "id": graphic.id,
            "title": graphic.title,
            "data_json": graphic.data_json,
            "created_by": graphic.created_by,
            "created_at": graphic.created_at,
            "updated_at": graphic.updated_at,
            "archived": graphic.archived
        }
    
    def update_graphic(self, graphic_id: int, graphic_update: GraphicUpdate, user_name: str) -> Optional[Dict[str, Any]]:
        """Update an existing graphic"""
        from ..models import Graphic
        
        graphic = self.db.query(Graphic).filter(Graphic.id == graphic_id).first()
        
        if not graphic:
            return None
        
        if graphic_update.title is not None:
            graphic.title = graphic_update.title
        
        if graphic_update.data_json is not None:
            graphic.data_json = graphic_update.data_json
        
        graphic.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(graphic)
        
        return {
            "id": graphic.id,
            "title": graphic.title,
            "data_json": graphic.data_json,
            "created_by": graphic.created_by,
            "created_at": graphic.created_at,
            "updated_at": graphic.updated_at,
            "archived": graphic.archived
        }
    
    def delete_graphic(self, graphic_id: int, user_name: str, is_admin: bool = False) -> bool:
        """Delete a graphic (soft delete by archiving)"""
        from ..models import Graphic
        
        graphic = self.db.query(Graphic).filter(Graphic.id == graphic_id).first()
        
        if not graphic:
            return False
        
        # Check if graphic is locked
        lock = self.get_active_lock(graphic_id)
        if lock:
            return False  # Cannot delete locked graphic
        
        graphic.archived = True
        graphic.updated_at = datetime.utcnow()
        
        self.db.commit()
        return True
    
    def acquire_lock(self, lock_request: CanvasLockCreate) -> Dict[str, Any]:
        """Acquire a canvas lock for editing"""
        from ..models import CanvasLock
        
        # Check if there's an existing active lock
        existing_lock = self.get_active_lock(lock_request.graphic_id)
        
        if existing_lock:
            # If lock belongs to the same user and is still valid, extend it
            if existing_lock.user_name == lock_request.user_name and existing_lock.expires_at > datetime.utcnow():
                existing_lock.expires_at = datetime.utcnow() + timedelta(minutes=5)
                self.db.commit()
                self.db.refresh(existing_lock)
                
                return {
                    "id": existing_lock.id,
                    "graphic_id": existing_lock.graphic_id,
                    "user_name": existing_lock.user_name,
                    "locked": True,
                    "locked_at": existing_lock.locked_at,
                    "expires_at": existing_lock.expires_at
                }
            
            # Lock is owned by someone else
            return {
                "locked": True,
                "locked_by": existing_lock.user_name,
                "expires_at": existing_lock.expires_at,
                "can_edit": False
            }
        
        # Create new lock
        new_lock = CanvasLock(
            graphic_id=lock_request.graphic_id,
            user_name=lock_request.user_name,
            locked=True,
            locked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        
        self.db.add(new_lock)
        self.db.commit()
        self.db.refresh(new_lock)
        
        return {
            "id": new_lock.id,
            "graphic_id": new_lock.graphic_id,
            "user_name": new_lock.user_name,
            "locked": True,
            "locked_at": new_lock.locked_at,
            "expires_at": new_lock.expires_at,
            "can_edit": True
        }
    
    def release_lock(self, graphic_id: int, user_name: str) -> bool:
        """Release a canvas lock"""
        from ..models import CanvasLock
        
        lock = self.db.query(CanvasLock).filter(
            and_(
                CanvasLock.graphic_id == graphic_id,
                CanvasLock.user_name == user_name,
                CanvasLock.locked == True
            )
        ).first()
        
        if lock:
            lock.locked = False
            self.db.commit()
            return True
        
        return False
    
    def get_active_lock(self, graphic_id: int) -> Optional[Dict[str, Any]]:
        """Get the active lock for a graphic"""
        from ..models import CanvasLock
        
        lock = self.db.query(CanvasLock).filter(
            and_(
                CanvasLock.graphic_id == graphic_id,
                CanvasLock.locked == True,
                CanvasLock.expires_at > datetime.utcnow()
            )
        ).first()
        
        if not lock:
            return None
        
        return {
            "id": lock.id,
            "graphic_id": lock.graphic_id,
            "user_name": lock.user_name,
            "locked": lock.locked,
            "locked_at": lock.locked_at,
            "expires_at": lock.expires_at
        }
    
    def get_lock_status(self, graphic_id: int, user_name: str) -> LockStatusResponse:
        """Get lock status for a graphic"""
        lock = self.get_active_lock(graphic_id)
        
        if not lock:
            return LockStatusResponse(
                locked=False,
                lock_info=None,
                can_edit=True
            )
        
        can_edit = lock["user_name"] == user_name
        
        return LockStatusResponse(
            locked=True,
            lock_info=lock,
            can_edit=can_edit
        )
    
    def cleanup_expired_locks(self) -> int:
        """Clean up expired locks (called by cron job)"""
        from ..models import CanvasLock
        
        expired_locks = self.db.query(CanvasLock).filter(
            or_(
                CanvasLock.expires_at <= datetime.utcnow(),
                CanvasLock.locked == False
            )
        ).all()
        
        count = len(expired_locks)
        
        for lock in expired_locks:
            lock.locked = False
        
        self.db.commit()
        return count
    
    def archive_graphic(self, graphic_id: int, user_name: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Archive a graphic"""
        from ..models import Graphic, Archive
        
        graphic = self.db.query(Graphic).filter(Graphic.id == graphic_id).first()
        
        if not graphic:
            return {"success": False, "message": "Graphic not found"}
        
        # Check if graphic is locked
        lock = self.get_active_lock(graphic_id)
        if lock:
            return {"success": False, "message": "Cannot archive locked graphic"}
        
        # Create archive record
        archive = Archive(
            graphic_id=graphic_id,
            archived_by=user_name,
            reason=reason
        )
        
        # Mark graphic as archived
        graphic.archived = True
        graphic.updated_at = datetime.utcnow()
        
        self.db.add(archive)
        self.db.commit()
        
        return {
            "success": True,
            "message": "Graphic archived successfully",
            "graphic_id": graphic_id,
            "archived_at": archive.archived_at
        }
    
    def restore_graphic(self, graphic_id: int, user_name: str) -> Dict[str, Any]:
        """Restore an archived graphic"""
        from ..models import Graphic, Archive
        
        graphic = self.db.query(Graphic).filter(Graphic.id == graphic_id).first()
        
        if not graphic:
            return {"success": False, "message": "Graphic not found"}
        
        if not graphic.archived:
            return {"success": False, "message": "Graphic is not archived"}
        
        # Mark graphic as active
        graphic.archived = False
        graphic.updated_at = datetime.utcnow()
        
        # Create restore record
        restore_archive = Archive(
            graphic_id=graphic_id,
            archived_by=user_name,
            reason="Restored from archive"
        )
        
        self.db.add(restore_archive)
        self.db.commit()
        
        return {
            "success": True,
            "message": "Graphic restored successfully",
            "graphic_id": graphic_id,
            "restored_at": restore_archive.archived_at
        }
