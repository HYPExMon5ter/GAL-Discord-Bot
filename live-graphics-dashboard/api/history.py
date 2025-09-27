"""
History API endpoints for undo/redo functionality and state tracking.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from models.history import GraphicsStateHistory, SyncQueue
from models.sessions import EditingSession
from storage.adapters.base import DatabaseManager


router = APIRouter()


# Pydantic models for request/response
class GraphicsStateHistoryCreate(BaseModel):
    template_id: int
    command_type: str
    state_before: Optional[Dict[str, Any]] = None
    state_after: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    command_data: Optional[Dict[str, Any]] = {}


class GraphicsStateHistoryResponse(BaseModel):
    id: int
    template_id: int
    command_type: str
    state_before: Optional[Dict[str, Any]]
    state_after: Optional[Dict[str, Any]]
    timestamp: datetime
    user_id: Optional[str]
    command_data: Dict[str, Any]
    description: str
    can_undo: bool
    can_redo: bool

    class Config:
        from_attributes = True


class EditingSessionResponse(BaseModel):
    id: int
    user_id: str
    template_id: int
    current_position: int
    max_history_depth: int
    created_at: datetime
    last_activity: datetime
    is_active: bool
    can_undo: bool

    class Config:
        from_attributes = True


class UndoRedoRequest(BaseModel):
    user_id: str
    template_id: int


async def get_db_session():
    """Dependency to get database session."""
    from app import db_manager
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    return await db_manager.get_session()


@router.get("/templates/{template_id}", response_model=List[GraphicsStateHistoryResponse])
async def get_template_history(
    template_id: int,
    user_id: Optional[str] = None,
    limit: int = 50,
    session = Depends(get_db_session)
):
    """Get history for a specific template."""
    try:
        query = session.query(GraphicsStateHistory).filter(
            GraphicsStateHistory.template_id == template_id
        )

        if user_id:
            query = query.filter(GraphicsStateHistory.user_id == user_id)

        history = query.order_by(GraphicsStateHistory.timestamp.desc()).limit(limit).all()

        return [
            GraphicsStateHistoryResponse(
                **item.to_dict(),
                description=item.get_description(),
                can_undo=item.can_undo(),
                can_redo=item.can_redo()
            )
            for item in history
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")
    finally:
        session.close()


@router.post("/commands", response_model=GraphicsStateHistoryResponse)
async def record_command(
    command_data: GraphicsStateHistoryCreate,
    session = Depends(get_db_session)
):
    """Record a new command in the history."""
    try:
        # Create history entry
        history_entry = GraphicsStateHistory(
            template_id=command_data.template_id,
            command_type=command_data.command_type,
            user_id=command_data.user_id
        )

        # Set state data
        if command_data.state_before:
            history_entry.set_state_before(command_data.state_before)
        if command_data.state_after:
            history_entry.set_state_after(command_data.state_after)
        if command_data.command_data:
            history_entry.set_command_data(command_data.command_data)

        session.add(history_entry)

        # Update or create editing session
        editing_session = session.query(EditingSession).filter(
            EditingSession.user_id == command_data.user_id,
            EditingSession.template_id == command_data.template_id,
            EditingSession.is_active == True
        ).first()

        if not editing_session:
            editing_session = EditingSession(
                user_id=command_data.user_id,
                template_id=command_data.template_id,
                current_position=1
            )
            session.add(editing_session)
        else:
            # Reset position for new commands (clears redo history)
            editing_session.reset_position()
            editing_session.current_position += 1

        session.commit()
        session.refresh(history_entry)

        return GraphicsStateHistoryResponse(
            **history_entry.to_dict(),
            description=history_entry.get_description(),
            can_undo=history_entry.can_undo(),
            can_redo=history_entry.can_redo()
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error recording command: {str(e)}")
    finally:
        session.close()


@router.post("/undo")
async def undo_command(
    undo_request: UndoRedoRequest,
    session = Depends(get_db_session)
):
    """Undo the last command for a user/template."""
    try:
        # Get editing session
        editing_session = session.query(EditingSession).filter(
            EditingSession.user_id == undo_request.user_id,
            EditingSession.template_id == undo_request.template_id,
            EditingSession.is_active == True
        ).first()

        if not editing_session:
            raise HTTPException(status_code=404, detail="No active editing session found")

        if not editing_session.can_undo():
            raise HTTPException(status_code=400, detail="Nothing to undo")

        # Get the command to undo
        history_entries = session.query(GraphicsStateHistory).filter(
            GraphicsStateHistory.template_id == undo_request.template_id,
            GraphicsStateHistory.user_id == undo_request.user_id
        ).order_by(GraphicsStateHistory.timestamp.desc()).limit(editing_session.current_position).all()

        if not history_entries or editing_session.current_position > len(history_entries):
            raise HTTPException(status_code=400, detail="No command to undo")

        # Get the command at current position
        command_to_undo = history_entries[editing_session.current_position - 1]

        if not command_to_undo.can_undo():
            raise HTTPException(status_code=400, detail="Command cannot be undone")

        # Move position back
        editing_session.move_position_back()
        session.commit()

        # Return the state to restore
        return {
            "success": True,
            "state_to_restore": command_to_undo.get_state_before(),
            "command_undone": command_to_undo.get_description(),
            "can_undo": editing_session.can_undo(),
            "can_redo": True  # We can now redo this command
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error undoing command: {str(e)}")
    finally:
        session.close()


@router.post("/redo")
async def redo_command(
    redo_request: UndoRedoRequest,
    session = Depends(get_db_session)
):
    """Redo the next command for a user/template."""
    try:
        # Get editing session
        editing_session = session.query(EditingSession).filter(
            EditingSession.user_id == redo_request.user_id,
            EditingSession.template_id == redo_request.template_id,
            EditingSession.is_active == True
        ).first()

        if not editing_session:
            raise HTTPException(status_code=404, detail="No active editing session found")

        # Get all history entries for this user/template
        history_entries = session.query(GraphicsStateHistory).filter(
            GraphicsStateHistory.template_id == redo_request.template_id,
            GraphicsStateHistory.user_id == redo_request.user_id
        ).order_by(GraphicsStateHistory.timestamp.desc()).all()

        # Check if we can redo (there's a command after current position)
        if editing_session.current_position >= len(history_entries):
            raise HTTPException(status_code=400, detail="Nothing to redo")

        # Get the command to redo (next command after current position)
        command_to_redo = history_entries[editing_session.current_position]

        if not command_to_redo.can_redo():
            raise HTTPException(status_code=400, detail="Command cannot be redone")

        # Move position forward
        editing_session.move_position_forward()
        session.commit()

        # Return the state to restore
        return {
            "success": True,
            "state_to_restore": command_to_redo.get_state_after(),
            "command_redone": command_to_redo.get_description(),
            "can_undo": True,  # We can now undo this command again
            "can_redo": editing_session.current_position < len(history_entries)
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error redoing command: {str(e)}")
    finally:
        session.close()


@router.get("/sessions/{user_id}/{template_id}", response_model=EditingSessionResponse)
async def get_editing_session(
    user_id: str,
    template_id: int,
    session = Depends(get_db_session)
):
    """Get or create an editing session for a user/template."""
    try:
        editing_session = session.query(EditingSession).filter(
            EditingSession.user_id == user_id,
            EditingSession.template_id == template_id,
            EditingSession.is_active == True
        ).first()

        if not editing_session:
            # Create new session
            editing_session = EditingSession(
                user_id=user_id,
                template_id=template_id
            )
            session.add(editing_session)
            session.commit()
            session.refresh(editing_session)

        return EditingSessionResponse(
            **editing_session.to_dict(),
            can_undo=editing_session.can_undo()
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error retrieving session: {str(e)}")
    finally:
        session.close()


@router.delete("/sessions/{user_id}/{template_id}")
async def end_editing_session(
    user_id: str,
    template_id: int,
    session = Depends(get_db_session)
):
    """End an editing session."""
    try:
        editing_session = session.query(EditingSession).filter(
            EditingSession.user_id == user_id,
            EditingSession.template_id == template_id,
            EditingSession.is_active == True
        ).first()

        if editing_session:
            editing_session.deactivate()
            session.commit()

        return {"message": "Editing session ended successfully"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error ending session: {str(e)}")
    finally:
        session.close()


@router.get("/sync-queue", response_model=List[Dict[str, Any]])
async def get_sync_queue(
    limit: int = 100,
    session = Depends(get_db_session)
):
    """Get pending sync queue items."""
    try:
        queue_items = session.query(SyncQueue).order_by(
            SyncQueue.created_at.asc()
        ).limit(limit).all()

        return [item.to_dict() for item in queue_items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sync queue: {str(e)}")
    finally:
        session.close()


@router.post("/sync-queue/process")
async def process_sync_queue(session = Depends(get_db_session)):
    """Process pending sync queue items."""
    try:
        from app import db_manager

        if not db_manager.primary_adapter or db_manager.is_using_fallback():
            raise HTTPException(status_code=503, detail="Primary database not available for sync")

        # Get pending items
        queue_items = session.query(SyncQueue).filter(
            SyncQueue.retry_count < 5
        ).order_by(SyncQueue.created_at.asc()).limit(50).all()

        processed = 0
        failed = 0

        for item in queue_items:
            try:
                # Process sync item (implementation would depend on specific requirements)
                # For now, just mark as processed by removing from queue
                session.delete(item)
                processed += 1
            except Exception as e:
                item.increment_retry(str(e))
                failed += 1

        session.commit()

        return {
            "processed": processed,
            "failed": failed,
            "remaining": session.query(SyncQueue).count()
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing sync queue: {str(e)}")
    finally:
        session.close()