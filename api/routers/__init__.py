"""
API routers
"""

from .tournaments import router as tournaments_router
from .users import router as users_router
from .configuration import router as configuration_router
from .websocket import router as websocket_router
from .standings import router as standings_router
from .placements import router as placements_router

__all__ = [
    "tournaments_router",
    "users_router",
    "configuration_router",
    "websocket_router",
    "standings_router",
    "placements_router"
]
