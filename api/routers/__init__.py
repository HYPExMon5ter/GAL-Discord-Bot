"""
API routers
"""

from .tournaments import router as tournaments_router
from .users import router as users_router
from .configuration import router as configuration_router
from .websocket import router as websocket_router

__all__ = [
    "tournaments_router", 
    "users_router", 
    "configuration_router",
    "websocket_router"
]
