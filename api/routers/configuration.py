"""
Configuration API endpoints
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..dependencies import get_database_session
from ..auth import get_current_authenticated_user, TokenData
from ..services.configuration_service import ConfigurationService
from ..schemas.configuration import (
    Configuration, 
    ConfigurationUpdate, 
    ConfigurationList,
    ConfigurationResponse
)


router = APIRouter()

@router.get("/", response_model=ConfigurationList)
async def get_configurations(
    category: Optional[str] = Query(None),
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get all configurations with optional category filtering
    """
    try:
        service = ConfigurationService(db)
        return await service.get_all_configurations(category=category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{key}", response_model=Configuration)
async def get_configuration(
    key: str,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get a specific configuration by key
    """
    try:
        service = ConfigurationService(db)
        return await service.get_configuration(key)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{key}", response_model=Configuration)
async def update_configuration(
    key: str,
    config_data: ConfigurationUpdate,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Update a configuration
    """
    try:
        service = ConfigurationService(db)
        return await service.update_configuration(key, config_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{key}", response_model=Configuration)
async def create_configuration(
    key: str,
    value: dict,
    description: Optional[str] = None,
    category: Optional[str] = None,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Create a new configuration
    """
    try:
        service = ConfigurationService(db)
        return await service.create_configuration(
            key=key,
            value=value,
            description=description,
            category=category
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{key}")
async def delete_configuration(
    key: str,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Delete a configuration
    """
    try:
        service = ConfigurationService(db)
        await service.delete_configuration(key)
        return {"message": f"Configuration '{key}' deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/category/{category}")
async def get_configurations_by_category(
    category: str,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Get all configurations in a specific category
    """
    try:
        service = ConfigurationService(db)
        return await service.get_configuration_by_category(category)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-update", response_model=ConfigurationResponse)
async def bulk_update_configurations(
    configs: dict,
    current_user: TokenData = Depends(get_current_authenticated_user),
    db: Session = Depends(get_database_session)
):
    """
    Update multiple configurations at once
    """
    try:
        service = ConfigurationService(db)
        result = await service.bulk_update_configurations(configs)
        
        if result["total_errors"] > 0:
            return ConfigurationResponse(
                success=False,
                message=f"Updated {result['total_updated']} configurations with {result['total_errors']} errors",
                data=result
            )
        else:
            return ConfigurationResponse(
                success=True,
                message=f"Successfully updated {result['total_updated']} configurations",
                data=result
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
