"""
Configuration API endpoints.

Routers are intentionally thin and delegate to the ConfigurationService, with
shared dependencies providing authenticated user and service instances.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.auth import TokenData
from api.dependencies import (
    get_active_user,
    get_configuration_service,
    require_write_access,
)
from api.services.configuration_service import ConfigurationService
from api.utils.service_runner import execute_service
from ..schemas.configuration import (
    Configuration,
    ConfigurationList,
    ConfigurationResponse,
    ConfigurationUpdate,
)

router = APIRouter()


@router.get("/", response_model=ConfigurationList)
async def get_configurations(
    category: Optional[str] = Query(None),
    _user: TokenData = Depends(get_active_user),
    service: ConfigurationService = Depends(get_configuration_service),
) -> ConfigurationList:
    return await execute_service(service.get_all_configurations, category=category)


@router.get("/{key}", response_model=Configuration)
async def get_configuration(
    key: str,
    _user: TokenData = Depends(get_active_user),
    service: ConfigurationService = Depends(get_configuration_service),
) -> Configuration:
    return await execute_service(service.get_configuration, key)


@router.put("/{key}", response_model=Configuration)
async def update_configuration(
    key: str,
    config_data: ConfigurationUpdate,
    _user: TokenData = Depends(require_write_access),
    service: ConfigurationService = Depends(get_configuration_service),
) -> Configuration:
    return await execute_service(service.update_configuration, key, config_data)


@router.post("/{key}", response_model=Configuration)
async def create_configuration(
    key: str,
    value: dict,
    description: Optional[str] = None,
    category: Optional[str] = None,
    _user: TokenData = Depends(require_write_access),
    service: ConfigurationService = Depends(get_configuration_service),
) -> Configuration:
    return await execute_service(
        service.create_configuration,
        key=key,
        value=value,
        description=description,
        category=category,
    )


@router.delete("/{key}")
async def delete_configuration(
    key: str,
    _user: TokenData = Depends(require_write_access),
    service: ConfigurationService = Depends(get_configuration_service),
) -> dict:
    await execute_service(service.delete_configuration, key)
    return {"message": f"Configuration '{key}' deleted successfully"}


@router.get("/category/{category}")
async def get_configurations_by_category(
    category: str,
    _user: TokenData = Depends(get_active_user),
    service: ConfigurationService = Depends(get_configuration_service),
) -> list[Configuration]:
    return await execute_service(service.get_configuration_by_category, category)


@router.post("/bulk-update", response_model=ConfigurationResponse)
async def bulk_update_configurations(
    configs: dict,
    _user: TokenData = Depends(require_write_access),
    service: ConfigurationService = Depends(get_configuration_service),
) -> ConfigurationResponse:
    result = await execute_service(service.bulk_update_configurations, configs)

    if result["total_errors"] > 0:
        return ConfigurationResponse(
            success=False,
            message=f"Updated {result['total_updated']} configurations with {result['total_errors']} errors",
            data=result,
        )

    return ConfigurationResponse(
        success=True,
        message=f"Successfully updated {result['total_updated']} configurations",
        data=result,
    )
