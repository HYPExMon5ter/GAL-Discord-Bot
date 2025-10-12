"""
Configuration schemas
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class Configuration(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None
    category: Optional[str] = None
    
    class Config:
        from_attributes = True

class ConfigurationUpdate(BaseModel):
    value: Any
    description: Optional[str] = None

class ConfigurationList(BaseModel):
    configurations: List[Configuration]
    total: int

class ConfigurationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
