"""
Archive API endpoints for managing archived events and templates.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from models.events import Event
from models.graphics import GraphicsTemplate, GraphicsInstance
from storage.adapters.base import DatabaseManager


router = APIRouter()


# Pydantic models for request/response
class ArchiveEventResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    status: str
    created_at: datetime
    template_count: int
    instance_count: int

    class Config:
        from_attributes = True


class ArchiveTemplateResponse(BaseModel):
    id: int
    name: str
    type: str
    event_id: Optional[int]
    event_name: Optional[str]
    created_at: datetime
    archived_at: Optional[datetime]
    parent_template_id: Optional[int]

    class Config:
        from_attributes = True


class RestoreRequest(BaseModel):
    new_event_id: Optional[int] = None
    new_name: Optional[str] = None


async def get_db_session():
    """Dependency to get database session."""
    from app import db_manager
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    return await db_manager.get_session()


@router.get("/events", response_model=List[ArchiveEventResponse])
async def get_archived_events(
    session = Depends(get_db_session)
):
    """Get all archived events with their template/instance counts."""
    try:
        # Get archived events
        archived_events = session.query(Event).filter(
            Event.status == "archived"
        ).order_by(Event.created_at.desc()).all()

        result = []
        for event in archived_events:
            # Count templates and instances
            template_count = session.query(GraphicsTemplate).filter(
                GraphicsTemplate.event_id == event.id
            ).count()

            instance_count = session.query(GraphicsInstance).filter(
                GraphicsInstance.event_id == event.id
            ).count()

            result.append(ArchiveEventResponse(
                **event.to_dict(),
                template_count=template_count,
                instance_count=instance_count
            ))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving archived events: {str(e)}")
    finally:
        session.close()


@router.get("/events/{event_id}/templates", response_model=List[ArchiveTemplateResponse])
async def get_archived_event_templates(
    event_id: int,
    session = Depends(get_db_session)
):
    """Get all templates for an archived event."""
    try:
        # Verify event exists and is archived
        event = session.query(Event).filter(
            Event.id == event_id,
            Event.status == "archived"
        ).first()

        if not event:
            raise HTTPException(status_code=404, detail="Archived event not found")

        # Get templates for this event
        templates = session.query(GraphicsTemplate).filter(
            GraphicsTemplate.event_id == event_id
        ).order_by(GraphicsTemplate.created_at.desc()).all()

        return [
            ArchiveTemplateResponse(
                **template.to_dict(),
                event_name=event.name
            )
            for template in templates
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving archived templates: {str(e)}")
    finally:
        session.close()


@router.get("/templates", response_model=List[ArchiveTemplateResponse])
async def get_archived_templates(
    template_type: Optional[str] = None,
    session = Depends(get_db_session)
):
    """Get all archived templates."""
    try:
        query = session.query(GraphicsTemplate).filter(
            GraphicsTemplate.archived_at.isnot(None)
        )

        if template_type:
            query = query.filter(GraphicsTemplate.type == template_type)

        templates = query.order_by(GraphicsTemplate.archived_at.desc()).all()

        result = []
        for template in templates:
            event_name = None
            if template.event_id:
                event = session.query(Event).filter(Event.id == template.event_id).first()
                event_name = event.name if event else None

            result.append(ArchiveTemplateResponse(
                **template.to_dict(),
                event_name=event_name
            ))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving archived templates: {str(e)}")
    finally:
        session.close()


@router.post("/events/{event_id}/restore")
async def restore_archived_event(
    event_id: int,
    session = Depends(get_db_session)
):
    """Restore an archived event to active status."""
    try:
        event = session.query(Event).filter(
            Event.id == event_id,
            Event.status == "archived"
        ).first()

        if not event:
            raise HTTPException(status_code=404, detail="Archived event not found")

        event.status = "active"
        session.commit()

        return {"message": f"Event '{event.name}' restored successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error restoring event: {str(e)}")
    finally:
        session.close()


@router.post("/templates/{template_id}/restore")
async def restore_archived_template(
    template_id: int,
    restore_data: RestoreRequest,
    session = Depends(get_db_session)
):
    """Restore an archived template or create a new template from archived one."""
    try:
        archived_template = session.query(GraphicsTemplate).filter(
            GraphicsTemplate.id == template_id,
            GraphicsTemplate.archived_at.isnot(None)
        ).first()

        if not archived_template:
            raise HTTPException(status_code=404, detail="Archived template not found")

        if restore_data.new_name or restore_data.new_event_id:
            # Create new template from archived one
            new_template = GraphicsTemplate()
            new_template.clone_from_parent(
                archived_template,
                restore_data.new_name or f"{archived_template.name} (Restored)",
                restore_data.new_event_id
            )
            session.add(new_template)
            session.commit()
            session.refresh(new_template)

            return {
                "message": f"New template created from archived template",
                "new_template_id": new_template.id,
                "new_template_name": new_template.name
            }
        else:
            # Restore original template
            archived_template.archived_at = None
            session.commit()

            return {"message": f"Template '{archived_template.name}' restored successfully"}

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error restoring template: {str(e)}")
    finally:
        session.close()


@router.delete("/events/{event_id}")
async def permanently_delete_archived_event(
    event_id: int,
    confirm: bool = False,
    session = Depends(get_db_session)
):
    """Permanently delete an archived event and all its templates/instances."""
    try:
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Confirmation required. Set confirm=true to permanently delete."
            )

        event = session.query(Event).filter(
            Event.id == event_id,
            Event.status == "archived"
        ).first()

        if not event:
            raise HTTPException(status_code=404, detail="Archived event not found")

        # Count related data before deletion
        template_count = session.query(GraphicsTemplate).filter(
            GraphicsTemplate.event_id == event_id
        ).count()

        instance_count = session.query(GraphicsInstance).filter(
            GraphicsInstance.event_id == event_id
        ).count()

        # Delete the event (cascading will handle templates and instances)
        session.delete(event)
        session.commit()

        return {
            "message": f"Event '{event.name}' permanently deleted",
            "deleted_templates": template_count,
            "deleted_instances": instance_count
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting event: {str(e)}")
    finally:
        session.close()


@router.delete("/templates/{template_id}")
async def permanently_delete_archived_template(
    template_id: int,
    confirm: bool = False,
    session = Depends(get_db_session)
):
    """Permanently delete an archived template."""
    try:
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Confirmation required. Set confirm=true to permanently delete."
            )

        template = session.query(GraphicsTemplate).filter(
            GraphicsTemplate.id == template_id,
            GraphicsTemplate.archived_at.isnot(None)
        ).first()

        if not template:
            raise HTTPException(status_code=404, detail="Archived template not found")

        template_name = template.name
        session.delete(template)
        session.commit()

        return {"message": f"Template '{template_name}' permanently deleted"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting template: {str(e)}")
    finally:
        session.close()


@router.get("/stats")
async def get_archive_stats(session = Depends(get_db_session)):
    """Get archive statistics."""
    try:
        archived_events = session.query(Event).filter(Event.status == "archived").count()
        archived_templates = session.query(GraphicsTemplate).filter(
            GraphicsTemplate.archived_at.isnot(None)
        ).count()

        # Get archive by type
        template_types = session.query(
            GraphicsTemplate.type,
            session.query(GraphicsTemplate).filter(
                GraphicsTemplate.archived_at.isnot(None),
                GraphicsTemplate.type == GraphicsTemplate.type
            ).count().label('count')
        ).filter(
            GraphicsTemplate.archived_at.isnot(None)
        ).group_by(GraphicsTemplate.type).all()

        type_counts = {template_type: count for template_type, count in template_types}

        return {
            "archived_events": archived_events,
            "archived_templates": archived_templates,
            "templates_by_type": type_counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving archive stats: {str(e)}")
    finally:
        session.close()


@router.post("/cleanup")
async def cleanup_old_archives(
    days_old: int = 365,
    dry_run: bool = True,
    session = Depends(get_db_session)
):
    """Clean up archives older than specified days."""
    try:
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Find old archived events
        old_events = session.query(Event).filter(
            Event.status == "archived",
            Event.created_at < cutoff_date
        ).all()

        # Find old archived templates
        old_templates = session.query(GraphicsTemplate).filter(
            GraphicsTemplate.archived_at.isnot(None),
            GraphicsTemplate.archived_at < cutoff_date
        ).all()

        if dry_run:
            return {
                "dry_run": True,
                "old_events_found": len(old_events),
                "old_templates_found": len(old_templates),
                "events": [{"id": e.id, "name": e.name, "created_at": e.created_at} for e in old_events],
                "templates": [{"id": t.id, "name": t.name, "archived_at": t.archived_at} for t in old_templates]
            }
        else:
            # Actually delete
            for event in old_events:
                session.delete(event)
            for template in old_templates:
                session.delete(template)

            session.commit()

            return {
                "dry_run": False,
                "deleted_events": len(old_events),
                "deleted_templates": len(old_templates)
            }

    except Exception as e:
        if not dry_run:
            session.rollback()
        raise HTTPException(status_code=500, detail=f"Error cleaning up archives: {str(e)}")
    finally:
        session.close()