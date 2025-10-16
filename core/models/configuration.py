"""
Configuration data models.

Defines system-wide and bot configuration entities.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field

from .base_model import BaseModel, utcnow


class ConfigurationCategory(Enum):
    """Configuration category enumeration."""
    GENERAL = "general"
    TOURNAMENT = "tournament"
    DISCORD = "discord"
    DATABASE = "database"
    CACHE = "cache"
    LOGGING = "logging"
    SECURITY = "security"
    INTEGRATIONS = "integrations"
    NOTIFICATIONS = "notifications"
    BACKUP = "backup"


class ConfigurationType(Enum):
    """Configuration value type enumeration."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    LIST = "list"
    DATETIME = "datetime"
    ENCRYPTED = "encrypted"


@dataclass
class ConfigurationValue(BaseModel):
    """Represents a single configuration value."""
    
    key: str = ""
    value: Any = None
    category: ConfigurationCategory = ConfigurationCategory.GENERAL
    value_type: ConfigurationType = ConfigurationType.STRING
    description: Optional[str] = None
    default_value: Any = None
    is_required: bool = False
    is_sensitive: bool = False
    validation_regex: Optional[str] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[Any]] = None
    requires_restart: bool = False
    environment_override: Optional[str] = None
    
    def validate(self) -> None:
        """Validate configuration value."""
        if not self.key:
            raise ValueError("Configuration key is required")
        
        # Validate based on type
        if self.value_type == ConfigurationType.INTEGER:
            if not isinstance(self.value, int):
                raise ValueError(f"Value must be an integer for key '{self.key}'")
            if self.min_value is not None and self.value < self.min_value:
                raise ValueError(f"Value below minimum for key '{self.key}'")
            if self.max_value is not None and self.value > self.max_value:
                raise ValueError(f"Value above maximum for key '{self.key}'")
        
        elif self.value_type == ConfigurationType.FLOAT:
            if not isinstance(self.value, (int, float)):
                raise ValueError(f"Value must be a number for key '{self.key}'")
            if self.min_value is not None and self.value < self.min_value:
                raise ValueError(f"Value below minimum for key '{self.key}'")
            if self.max_value is not None and self.value > self.max_value:
                raise ValueError(f"Value above maximum for key '{self.key}'")
        
        elif self.value_type == ConfigurationType.BOOLEAN:
            if not isinstance(self.value, bool):
                raise ValueError(f"Value must be a boolean for key '{self.key}'")
        
        elif self.value_type == ConfigurationType.STRING:
            if not isinstance(self.value, str):
                raise ValueError(f"Value must be a string for key '{self.key}'")
        
        elif self.value_type == ConfigurationType.LIST:
            if not isinstance(self.value, list):
                raise ValueError(f"Value must be a list for key '{self.key}'")
        
        # Check allowed values
        if self.allowed_values is not None and self.value not in self.allowed_values:
            raise ValueError(f"Value not in allowed values for key '{self.key}'")
    
    def set_value(self, new_value: Any, user_id: Optional[str] = None) -> None:
        """
        Set a new value for the configuration.
        
        Args:
            new_value: New value to set
            user_id: ID of user making the change
        """
        old_value = self.value
        self.value = new_value
        
        try:
            self.validate()
            self.update_timestamp(user_id)
        except ValueError:
            # Revert on validation failure
            self.value = old_value
            raise
    
    def reset_to_default(self, user_id: Optional[str] = None) -> None:
        """
        Reset the configuration to its default value.
        
        Args:
            user_id: ID of user making the change
        """
        if self.default_value is not None:
            self.set_value(self.default_value, user_id)
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary, masking sensitive values.
        
        Returns:
            Dictionary representation with sensitive values masked
        """
        result = self.to_dict()
        if self.is_sensitive and self.value:
            result['value'] = "***MASKED***"
        return result


@dataclass
class Configuration(BaseModel):
    """Represents a collection of configuration values."""
    
    name: str = ""
    version: str = "1.0.0"
    description: Optional[str] = None
    is_active: bool = True
    environment: str = "production"
    last_backup: Optional[datetime] = None
    backup_retention_days: int = 30
    auto_backup_enabled: bool = True
    values: Dict[str, ConfigurationValue] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate configuration collection."""
        if not self.name:
            raise ValueError("Configuration name is required")
        if self.backup_retention_days < 1:
            raise ValueError("Backup retention must be at least 1 day")
        
        # Validate all configuration values
        for config_value in self.values.values():
            config_value.validate()
    
    def add_value(self, config_value: ConfigurationValue) -> None:
        """
        Add a configuration value.
        
        Args:
            config_value: Configuration value to add
        """
        self.values[config_value.key] = config_value
        self.update_timestamp()
    
    def remove_value(self, key: str) -> None:
        """
        Remove a configuration value.
        
        Args:
            key: Configuration key to remove
        """
        if key in self.values:
            del self.values[key]
            self.update_timestamp()
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        if key in self.values:
            return self.values[key].value
        return default
    
    def set_value(self, key: str, value: Any, user_id: Optional[str] = None) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
            user_id: ID of user making the change
        """
        if key in self.values:
            self.values[key].set_value(value, user_id)
            self.update_timestamp(user_id)
        else:
            raise ValueError(f"Configuration key '{key}' not found")
    
    def get_category_values(self, category: ConfigurationCategory) -> Dict[str, ConfigurationValue]:
        """
        Get all configuration values for a specific category.
        
        Args:
            category: Configuration category
            
        Returns:
            Dictionary of configuration values for the category
        """
        return {
            key: value for key, value in self.values.items()
            if value.category == category
        }
    
    def get_values_requiring_restart(self) -> Dict[str, ConfigurationValue]:
        """
        Get all configuration values that require a restart.
        
        Returns:
            Dictionary of configuration values requiring restart
        """
        return {
            key: value for key, value in self.values.items()
            if value.requires_restart
        }
    
    def get_sensitive_values(self) -> Dict[str, ConfigurationValue]:
        """
        Get all sensitive configuration values.
        
        Returns:
            Dictionary of sensitive configuration values
        """
        return {
            key: value for key, value in self.values.items()
            if value.is_sensitive
        }
    
    def validate_all(self) -> List[str]:
        """
        Validate all configuration values.
        
        Returns:
            List of validation error messages
        """
        errors = []
        for key, config_value in self.values.items():
            try:
                config_value.validate()
            except ValueError as e:
                errors.append(f"{key}: {str(e)}")
        return errors
    
    def export_safe(self) -> Dict[str, Any]:
        """
        Export configuration with sensitive values masked.
        
        Returns:
            Safe export dictionary
        """
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'environment': self.environment,
            'values': {
                key: value.to_safe_dict()
                for key, value in self.values.items()
            }
        }
    
    def mark_backup(self) -> None:
        """Mark that a backup has been created."""
        self.last_backup = utcnow()
        self.update_timestamp()


@dataclass
class ConfigurationHistory(BaseModel):
    """Represents a change history for configuration values."""
    
    configuration_id: str = ""
    key: str = ""
    old_value: Any = None
    new_value: Any = None
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None
    rollback_available: bool = True
    
    def validate(self) -> None:
        """Validate configuration history entry."""
        if not self.configuration_id:
            raise ValueError("Configuration ID is required")
        if not self.key:
            raise ValueError("Configuration key is required")
    
    def can_rollback(self) -> bool:
        """Check if this change can be rolled back."""
        return self.rollback_available
