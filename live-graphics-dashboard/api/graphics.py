"""
Graphics API endpoints for managing templates and instances.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from models.graphics import GraphicsTemplate, GraphicsInstance
from storage.adapters.base import DatabaseManager


router = APIRouter()


# Pydantic models for request/response
class GraphicsTemplateCreate(BaseModel):
    name: str
    type: str
    event_id: Optional[int] = None
    html_content: Optional[str] = None
    css_content: Optional[str] = None
    js_content: Optional[str] = None
    data_bindings: Optional[Dict[str, Any]] = {}
    parent_template_id: Optional[int] = None


class GraphicsTemplateUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    event_id: Optional[int] = None
    html_content: Optional[str] = None
    css_content: Optional[str] = None
    js_content: Optional[str] = None
    data_bindings: Optional[Dict[str, Any]] = None
    parent_template_id: Optional[int] = None


class GraphicsTemplateResponse(BaseModel):
    id: int
    name: str
    type: str
    event_id: Optional[int]
    html_content: Optional[str]
    css_content: Optional[str]
    js_content: Optional[str]
    data_bindings: Dict[str, Any]
    created_at: datetime
    archived_at: Optional[datetime]
    parent_template_id: Optional[int]
    is_archived: bool

    class Config:
        from_attributes = True


class GraphicsInstanceCreate(BaseModel):
    template_id: int
    name: str
    event_id: Optional[int] = None
    config: Optional[Dict[str, Any]] = {}


class GraphicsInstanceUpdate(BaseModel):
    name: Optional[str] = None
    event_id: Optional[int] = None
    config: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None


class GraphicsInstanceResponse(BaseModel):
    id: int
    template_id: int
    name: str
    event_id: Optional[int]
    config: Dict[str, Any]
    active: bool
    last_updated: datetime

    class Config:
        from_attributes = True


async def get_db_session():
    """Dependency to get database session."""
    from app import db_manager
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    return await db_manager.get_session()


# Templates endpoints
@router.get("/templates", response_model=List[GraphicsTemplateResponse])
async def get_templates(
    event_id: Optional[int] = None,
    template_type: Optional[str] = None,
    include_archived: bool = False,
    session = Depends(get_db_session)
):
    """Get all graphics templates with optional filtering."""
    try:
        query = session.query(GraphicsTemplate)

        if event_id:
            query = query.filter(GraphicsTemplate.event_id == event_id)
        if template_type:
            query = query.filter(GraphicsTemplate.type == template_type)
        if not include_archived:
            query = query.filter(GraphicsTemplate.archived_at.is_(None))

        templates = query.order_by(GraphicsTemplate.created_at.desc()).all()

        return [
            GraphicsTemplateResponse(
                **template.to_dict(),
                is_archived=template.is_archived()
            )
            for template in templates
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving templates: {str(e)}")
    finally:
        session.close()


@router.get("/templates/{template_id}", response_model=GraphicsTemplateResponse)
async def get_template(
    template_id: int,
    session = Depends(get_db_session)
):
    """Get a specific graphics template by ID."""
    try:
        template = session.query(GraphicsTemplate).filter(GraphicsTemplate.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        return GraphicsTemplateResponse(
            **template.to_dict(),
            is_archived=template.is_archived()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving template: {str(e)}")
    finally:
        session.close()


@router.post("/templates", response_model=GraphicsTemplateResponse)
async def create_template(
    template_data: GraphicsTemplateCreate,
    session = Depends(get_db_session)
):
    """Create a new graphics template."""
    try:
        # Create new template
        template = GraphicsTemplate(
            name=template_data.name,
            type=template_data.type,
            event_id=template_data.event_id,
            html_content=template_data.html_content,
            css_content=template_data.css_content,
            js_content=template_data.js_content,
            parent_template_id=template_data.parent_template_id
        )

        # Set data bindings
        if template_data.data_bindings:
            template.set_data_bindings(template_data.data_bindings)

        session.add(template)
        session.commit()
        session.refresh(template)

        return GraphicsTemplateResponse(
            **template.to_dict(),
            is_archived=template.is_archived()
        )
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating template: {str(e)}")
    finally:
        session.close()


@router.put("/templates/{template_id}", response_model=GraphicsTemplateResponse)
async def update_template(
    template_id: int,
    template_data: GraphicsTemplateUpdate,
    session = Depends(get_db_session)
):
    """Update an existing graphics template."""
    try:
        template = session.query(GraphicsTemplate).filter(GraphicsTemplate.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Update fields
        update_data = template_data.dict(exclude_unset=True)
        data_bindings = update_data.pop('data_bindings', None)

        for field, value in update_data.items():
            setattr(template, field, value)

        # Update data bindings separately
        if data_bindings is not None:
            template.set_data_bindings(data_bindings)

        session.commit()
        session.refresh(template)

        return GraphicsTemplateResponse(
            **template.to_dict(),
            is_archived=template.is_archived()
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating template: {str(e)}")
    finally:
        session.close()


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    session = Depends(get_db_session)
):
    """Delete a graphics template."""
    try:
        template = session.query(GraphicsTemplate).filter(GraphicsTemplate.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        session.delete(template)
        session.commit()

        return {"message": "Template deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting template: {str(e)}")
    finally:
        session.close()


@router.post("/templates/{template_id}/clone", response_model=GraphicsTemplateResponse)
async def clone_template(
    template_id: int,
    new_name: str,
    new_event_id: Optional[int] = None,
    session = Depends(get_db_session)
):
    """Clone an existing template."""
    try:
        original = session.query(GraphicsTemplate).filter(GraphicsTemplate.id == template_id).first()
        if not original:
            raise HTTPException(status_code=404, detail="Template not found")

        # Create new template from original
        new_template = GraphicsTemplate()
        new_template.clone_from_parent(original, new_name, new_event_id)

        session.add(new_template)
        session.commit()
        session.refresh(new_template)

        return GraphicsTemplateResponse(
            **new_template.to_dict(),
            is_archived=new_template.is_archived()
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error cloning template: {str(e)}")
    finally:
        session.close()


# Instances endpoints
@router.get("/instances", response_model=List[GraphicsInstanceResponse])
async def get_instances(
    event_id: Optional[int] = None,
    template_id: Optional[int] = None,
    active_only: bool = False,
    session = Depends(get_db_session)
):
    """Get all graphics instances with optional filtering."""
    try:
        query = session.query(GraphicsInstance)

        if event_id:
            query = query.filter(GraphicsInstance.event_id == event_id)
        if template_id:
            query = query.filter(GraphicsInstance.template_id == template_id)
        if active_only:
            query = query.filter(GraphicsInstance.active == True)

        instances = query.order_by(GraphicsInstance.last_updated.desc()).all()

        return [
            GraphicsInstanceResponse(**instance.to_dict())
            for instance in instances
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving instances: {str(e)}")
    finally:
        session.close()


@router.post("/instances", response_model=GraphicsInstanceResponse)
async def create_instance(
    instance_data: GraphicsInstanceCreate,
    session = Depends(get_db_session)
):
    """Create a new graphics instance."""
    try:
        # Verify template exists
        template = session.query(GraphicsTemplate).filter(
            GraphicsTemplate.id == instance_data.template_id
        ).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Create new instance
        instance = GraphicsInstance(
            template_id=instance_data.template_id,
            name=instance_data.name,
            event_id=instance_data.event_id
        )

        # Set configuration
        if instance_data.config:
            instance.set_config(instance_data.config)

        session.add(instance)
        session.commit()
        session.refresh(instance)

        return GraphicsInstanceResponse(**instance.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating instance: {str(e)}")
    finally:
        session.close()


@router.put("/instances/{instance_id}", response_model=GraphicsInstanceResponse)
async def update_instance(
    instance_id: int,
    instance_data: GraphicsInstanceUpdate,
    session = Depends(get_db_session)
):
    """Update an existing graphics instance."""
    try:
        instance = session.query(GraphicsInstance).filter(GraphicsInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="Instance not found")

        # Update fields
        update_data = instance_data.dict(exclude_unset=True)
        config = update_data.pop('config', None)

        for field, value in update_data.items():
            setattr(instance, field, value)

        # Update configuration separately
        if config is not None:
            instance.set_config(config)

        instance.last_updated = datetime.utcnow()
        session.commit()
        session.refresh(instance)

        return GraphicsInstanceResponse(**instance.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating instance: {str(e)}")
    finally:
        session.close()


@router.post("/instances/{instance_id}/activate")
async def activate_instance(
    instance_id: int,
    session = Depends(get_db_session)
):
    """Activate a graphics instance."""
    try:
        instance = session.query(GraphicsInstance).filter(GraphicsInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="Instance not found")

        instance.activate()
        session.commit()

        return {"message": "Instance activated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error activating instance: {str(e)}")
    finally:
        session.close()


@router.post("/instances/{instance_id}/deactivate")
async def deactivate_instance(
    instance_id: int,
    session = Depends(get_db_session)
):
    """Deactivate a graphics instance."""
    try:
        instance = session.query(GraphicsInstance).filter(GraphicsInstance.id == instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="Instance not found")

        instance.deactivate()
        session.commit()

        return {"message": "Instance deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error deactivating instance: {str(e)}")
    finally:
        session.close()