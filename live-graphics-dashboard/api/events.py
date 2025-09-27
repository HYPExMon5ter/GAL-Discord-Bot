"""
Events API endpoints for managing tournaments and events.
"""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from models.events import Event
from storage.adapters.base import DatabaseManager


router = APIRouter()


# Pydantic models for request/response
class EventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class EventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None


class EventResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    status: str
    created_at: datetime
    can_be_archived: bool

    class Config:
        from_attributes = True


async def get_db_session():
    """Dependency to get database session."""
    from app import db_manager
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    return await db_manager.get_session()


@router.get("/", response_model=List[EventResponse])
async def get_events(
    status: Optional[str] = None,
    session = Depends(get_db_session)
):
    """Get all events, optionally filtered by status."""
    try:
        query = session.query(Event)
        if status:
            query = query.filter(Event.status == status)

        events = query.order_by(Event.created_at.desc()).all()

        # Convert to response format
        return [
            EventResponse(
                **event.to_dict(),
                can_be_archived=event.can_be_archived()
            )
            for event in events
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving events: {str(e)}")
    finally:
        session.close()


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    session = Depends(get_db_session)
):
    """Get a specific event by ID."""
    try:
        event = session.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return EventResponse(
            **event.to_dict(),
            can_be_archived=event.can_be_archived()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving event: {str(e)}")
    finally:
        session.close()


@router.post("/", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    session = Depends(get_db_session)
):
    """Create a new event."""
    try:
        # Create new event
        event = Event(
            name=event_data.name,
            description=event_data.description,
            start_date=event_data.start_date,
            end_date=event_data.end_date,
            status="active"
        )

        session.add(event)
        session.commit()
        session.refresh(event)

        return EventResponse(
            **event.to_dict(),
            can_be_archived=event.can_be_archived()
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating event: {str(e)}")
    finally:
        session.close()


@router.put("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_data: EventUpdate,
    session = Depends(get_db_session)
):
    """Update an existing event."""
    try:
        event = session.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        # Update fields
        for field, value in event_data.dict(exclude_unset=True).items():
            setattr(event, field, value)

        session.commit()
        session.refresh(event)

        return EventResponse(
            **event.to_dict(),
            can_be_archived=event.can_be_archived()
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating event: {str(e)}")
    finally:
        session.close()


@router.delete("/{event_id}")
async def delete_event(
    event_id: int,
    session = Depends(get_db_session)
):
    """Delete an event."""
    try:
        event = session.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        session.delete(event)
        session.commit()

        return {"message": "Event deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting event: {str(e)}")
    finally:
        session.close()


@router.post("/{event_id}/archive")
async def archive_event(
    event_id: int,
    session = Depends(get_db_session)
):
    """Archive an event."""
    try:
        event = session.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        if not event.can_be_archived():
            raise HTTPException(
                status_code=400,
                detail="Event cannot be archived (must be completed or past end date)"
            )

        event.status = "archived"
        session.commit()

        return {"message": "Event archived successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error archiving event: {str(e)}")
    finally:
        session.close()


@router.post("/{event_id}/complete")
async def complete_event(
    event_id: int,
    session = Depends(get_db_session)
):
    """Mark an event as completed."""
    try:
        event = session.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        event.status = "completed"
        session.commit()

        return {"message": "Event marked as completed"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error completing event: {str(e)}")
    finally:
        session.close()