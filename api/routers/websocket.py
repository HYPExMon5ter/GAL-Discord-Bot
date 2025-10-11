"""
WebSocket endpoints for real-time updates
"""

import json
import asyncio
from typing import Dict, Set
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from ..dependencies import get_database_session, get_current_authenticated_user
from ..main import TokenData

router = APIRouter()

class ConnectionManager:
    """
    WebSocket connection manager for real-time updates
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str):
        """
        Accept and store WebSocket connection
        """
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        print(f"WebSocket connected: {connection_id} for user {user_id}")
    
    def disconnect(self, connection_id: str, user_id: str):
        """
        Remove WebSocket connection
        """
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        print(f"WebSocket disconnected: {connection_id} for user {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """
        Send message to all connections for a specific user
        """
        if user_id in self.user_connections:
            disconnected_connections = []
            
            for connection_id in self.user_connections[user_id]:
                if connection_id in self.active_connections:
                    websocket = self.active_connections[connection_id]
                    try:
                        await websocket.send_text(json.dumps(message))
                    except Exception as e:
                        print(f"Error sending message to {connection_id}: {e}")
                        disconnected_connections.append(connection_id)
                else:
                    disconnected_connections.append(connection_id)
            
            # Clean up disconnected connections
            for connection_id in disconnected_connections:
                self.disconnect(connection_id, user_id)
    
    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected clients
        """
        disconnected_connections = []
        
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"Error broadcasting to {connection_id}: {e}")
                disconnected_connections.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected_connections:
            # Find user_id for this connection
            for user_id, conn_ids in self.user_connections.items():
                if connection_id in conn_ids:
                    self.disconnect(connection_id, user_id)
                    break
    
    def get_connection_count(self) -> int:
        """
        Get total number of active connections
        """
        return len(self.active_connections)
    
    def get_user_count(self) -> int:
        """
        Get number of unique connected users
        """
        return len(self.user_connections)

# Global connection manager
manager = ConnectionManager()

@router.websocket("/ws/{token}")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str,
    db: Session = Depends(get_database_session)
):
    """
    WebSocket endpoint for real-time updates
    """
    try:
        # Verify JWT token
        from jose import JWTError, jwt
        from ..main import SECRET_KEY, ALGORITHM
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                await websocket.close(code=4001, reason="Invalid token")
                return
        except JWTError:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        # Generate unique connection ID
        connection_id = f"{user_id}_{datetime.utcnow().timestamp()}"
        
        # Connect to WebSocket
        await manager.connect(websocket, connection_id, user_id)
        
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "data": {
                "connection_id": connection_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to GAL Dashboard WebSocket"
            }
        }))
        
        # Keep connection alive and handle incoming messages
        try:
            while True:
                # Wait for message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                message_type = message.get("type", "unknown")
                
                if message_type == "ping":
                    # Respond to ping with pong
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
                elif message_type == "subscribe":
                    # Handle subscription to specific events
                    event_type = message.get("event_type")
                    await websocket.send_text(json.dumps({
                        "type": "subscription_confirmed",
                        "event_type": event_type,
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                
                else:
                    # Echo unknown messages
                    await websocket.send_text(json.dumps({
                        "type": "echo",
                        "original_message": message,
                        "timestamp": datetime.utcnow().isoformat()
                    }))
        
        except WebSocketDisconnect:
            manager.disconnect(connection_id, user_id)
            print(f"User {user_id} disconnected")
        
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close(code=4000, reason="Server error")
        except:
            pass

@router.get("/ws/status")
async def websocket_status(
    current_user: TokenData = Depends(get_current_authenticated_user)
):
    """
    Get WebSocket connection status
    """
    return {
        "active_connections": manager.get_connection_count(),
        "connected_users": manager.get_user_count(),
        "timestamp": datetime.utcnow().isoformat()
    }

# Functions to send real-time updates (can be called from other parts of the application)
async def send_tournament_update(tournament_data: dict):
    """
    Send tournament update to all connected clients
    """
    await manager.broadcast({
        "type": "tournament_update",
        "data": tournament_data,
        "timestamp": datetime.utcnow().isoformat()
    })

async def send_user_update(user_data: dict):
    """
    Send user update to all connected clients
    """
    await manager.broadcast({
        "type": "user_update",
        "data": user_data,
        "timestamp": datetime.utcnow().isoformat()
    })

async def send_configuration_update(config_data: dict):
    """
    Send configuration update to all connected clients
    """
    await manager.broadcast({
        "type": "configuration_update",
        "data": config_data,
        "timestamp": datetime.utcnow().isoformat()
    })

async def send_system_notification(notification: dict):
    """
    Send system notification to all connected clients
    """
    await manager.broadcast({
        "type": "system_notification",
        "data": notification,
        "timestamp": datetime.utcnow().isoformat()
    })

# Export these functions for use by other modules
__all__ = [
    "send_tournament_update",
    "send_user_update", 
    "send_configuration_update",
    "send_system_notification",
    "manager"
]
