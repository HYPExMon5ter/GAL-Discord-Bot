"""
Configuration business logic service
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from core.data_access.configuration_repository import ConfigurationRepository
from ..schemas.configuration import ConfigurationUpdate, ConfigurationList
from .errors import ConflictError, NotFoundError

class ConfigurationService:
    """
    Service class for configuration business logic
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.config_repo = ConfigurationRepository(db)
    
    async def get_all_configurations(self, category: Optional[str] = None) -> ConfigurationList:
        """
        Get all configurations with optional category filtering
        """
        configs = await self.config_repo.get_all(category=category)
        return ConfigurationList(configurations=configs, total=len(configs))
    
    async def get_configuration(self, key: str):
        """
        Get a specific configuration by key
        """
        config = await self.config_repo.get_by_key(key)
        if not config:
            raise NotFoundError(f"Configuration with key '{key}' not found")
        return config
    
    async def update_configuration(self, key: str, config_data: ConfigurationUpdate):
        """
        Update a configuration
        """
        # Check if configuration exists
        existing = await self.config_repo.get_by_key(key)
        if not existing:
            raise NotFoundError(f"Configuration with key '{key}' not found")
        
        # Update configuration
        update_data = {
            "value": config_data.value,
            "description": config_data.description
        }
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        return await self.config_repo.update(key, update_data)
    
    async def create_configuration(
        self, 
        key: str, 
        value: Any, 
        description: Optional[str] = None,
        category: Optional[str] = None
    ):
        """
        Create a new configuration
        """
        # Check if configuration already exists
        existing = await self.config_repo.get_by_key(key)
        if existing:
            raise ConflictError(f"Configuration with key '{key}' already exists")
        
        config_data = {
            "key": key,
            "value": value,
            "description": description,
            "category": category
        }
        
        return await self.config_repo.create(config_data)
    
    async def delete_configuration(self, key: str):
        """
        Delete a configuration
        """
        # Check if configuration exists
        existing = await self.config_repo.get_by_key(key)
        if not existing:
            raise NotFoundError(f"Configuration with key '{key}' not found")
        
        return await self.config_repo.delete(key)
    
    async def get_configuration_by_category(self, category: str):
        """
        Get all configurations in a specific category
        """
        return await self.config_repo.get_by_category(category)
    
    async def bulk_update_configurations(self, configs: Dict[str, Any]):
        """
        Update multiple configurations at once
        """
        results = []
        errors = []
        
        for key, value in configs.items():
            try:
                updated = await self.update_configuration(
                    key, 
                    ConfigurationUpdate(value=value)
                )
                results.append({"key": key, "success": True, "data": updated})
            except NotFoundError as e:
                errors.append({"key": key, "success": False, "error": str(e)})
            except ConflictError as e:
                errors.append({"key": key, "success": False, "error": str(e)})
        
        return {
            "updated": results,
            "errors": errors,
            "total_updated": len(results),
            "total_errors": len(errors)
        }
