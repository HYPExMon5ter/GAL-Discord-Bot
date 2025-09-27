"""
FastAPI backend for Live Graphics Dashboard.
This service provides APIs for managing graphics templates, events, and real-time updates.
"""

import os
import logging
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from storage.adapters.base import DatabaseManager
from services.ign_verification import initialize_verification_service


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global database manager
db_manager: DatabaseManager = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    global db_manager

    # Startup
    logger.info("Starting Live Graphics Dashboard")

    try:
        # Initialize database
        postgresql_url = os.getenv("DATABASE_URL")
        sqlite_path = "data/graphics.db"

        db_manager = DatabaseManager(postgresql_url, sqlite_path)
        await db_manager.initialize()

        # Initialize IGN verification service
        await initialize_verification_service(db_manager)

        logger.info("Database and services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Live Graphics Dashboard")
    if db_manager:
        if db_manager.primary_adapter:
            await db_manager.primary_adapter.disconnect()
        if db_manager.fallback_adapter:
            await db_manager.fallback_adapter.disconnect()


# Create FastAPI app
app = FastAPI(
    title="Live Graphics Dashboard",
    description="API for managing live graphics templates and real-time tournament data",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_status = "healthy" if db_manager and db_manager.current_adapter else "unavailable"
    db_type = db_manager.get_current_adapter_type() if db_manager else "none"

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": {
            "status": db_status,
            "type": db_type,
            "using_fallback": db_manager.is_using_fallback() if db_manager else False
        },
        "version": "1.0.0"
    }


# WebSocket endpoint for real-time updates
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time graphics updates."""
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            logger.info(f"Received from {client_id}: {data}")

            # Echo back for now (can be extended for real-time updates)
            await manager.send_personal_message(f"Echo: {data}", client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        manager.disconnect(client_id)


# API Routes
@app.get("/api/database/status")
async def get_database_status():
    """Get current database status and statistics."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database manager not initialized")

    try:
        # Get verification statistics
        from services.ign_verification import verification_service
        verification_stats = {}
        if verification_service:
            verification_stats = await verification_service.get_verification_stats()

        return {
            "adapter_type": db_manager.get_current_adapter_type(),
            "using_fallback": db_manager.is_using_fallback(),
            "can_switch_to_primary": bool(db_manager.primary_adapter),
            "verification_stats": verification_stats
        }
    except Exception as e:
        logger.error(f"Error getting database status: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving database status")


@app.post("/api/database/switch-primary")
async def switch_to_primary():
    """Try to switch back to primary database."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database manager not initialized")

    try:
        success = await db_manager.try_switch_to_primary()
        return {
            "success": success,
            "current_adapter": db_manager.get_current_adapter_type(),
            "message": "Switched to primary database" if success else "Primary database still unavailable"
        }
    except Exception as e:
        logger.error(f"Error switching to primary database: {e}")
        raise HTTPException(status_code=500, detail="Error switching database")


# Include API routers
from api import events, graphics, history, archive

app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(graphics.router, prefix="/api/graphics", tags=["graphics"])
app.include_router(history.router, prefix="/api/history", tags=["history"])
app.include_router(archive.router, prefix="/api/archive", tags=["archive"])


# Serve static files (React frontend)
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Serve React app
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the React frontend."""
    try:
        index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
        with open(index_path, "r") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            content="""
            <html>
                <head><title>Live Graphics Dashboard</title></head>
                <body>
                    <h1>Live Graphics Dashboard</h1>
                    <p>Frontend not yet built. React app will be served here.</p>
                    <p>API is available at <a href="/docs">/docs</a></p>
                </body>
            </html>
            """,
            status_code=200
        )


# Catch-all route for React Router
@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_frontend_routes(full_path: str):
    """Serve React app for all frontend routes."""
    # Exclude API routes
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("ws/"):
        raise HTTPException(status_code=404, detail="Not found")

    return await serve_frontend()


if __name__ == "__main__":
    # Development server
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )