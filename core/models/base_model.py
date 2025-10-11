"""
Base model class for all data entities.

Provides common functionality like serialization, validation, and
audit trail capabilities.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field
import json


@dataclass
class BaseModel(ABC):
    """
    Abstract base class for all data models.
    
    Provides common functionality for serialization, validation,
    and audit trail management.
    """
    
    # Core fields
    id: Optional[str] = None
    created_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    version: int = 1
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        if self.updated_at is None:
            self.updated_at = self.created_at
        self.validate()
    
    @abstractmethod
    def validate(self) -> None:
        """
        Validate the model data.
        
        Raises:
            ValueError: If validation fails
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert model to dictionary representation.
        
        Returns:
            Dictionary representation of the model
        """
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, BaseModel):
                result[key] = value.to_dict()
            elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
                result[key] = [item.to_dict() for item in value]
            else:
                result[key] = value
        return result
    
    def to_json(self) -> str:
        """
        Convert model to JSON string.
        
        Returns:
            JSON representation of the model
        """
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """
        Create model instance from dictionary.
        
        Args:
            data: Dictionary containing model data
            
        Returns:
            Model instance
        """
        # Convert datetime strings back to datetime objects
        for key, value in data.items():
            if key.endswith('_at') and isinstance(value, str):
                try:
                    data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    pass
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseModel':
        """
        Create model instance from JSON string.
        
        Args:
            json_str: JSON string containing model data
            
        Returns:
            Model instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def update_timestamp(self, user_id: Optional[str] = None) -> None:
        """
        Update the updated_at timestamp.
        
        Args:
            user_id: ID of the user making the update
        """
        self.updated_at = datetime.utcnow()
        if user_id:
            self.updated_by = user_id
        self.version += 1
    
    def add_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata to the model.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        self.update_timestamp()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)
    
    def __str__(self) -> str:
        """String representation of the model."""
        return f"{self.__class__.__name__}(id={self.id})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the model."""
        return f"{self.__class__.__name__}({self.to_dict()})"
