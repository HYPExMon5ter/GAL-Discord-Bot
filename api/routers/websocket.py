"""
WebSocket endpoints for real-time updates with backpressure handling.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from api.auth import ALGORITHM, SECRET_KEY, TokenData

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_QUEUE_SIZE = 50
CLIENT_TIMEOUT = timedelta(seconds=45)


def utcnow() -> datetime:
    """Timezone-aware wrapper used throughout the WebSocket manager."""
    return datetime.now(UTC)


@dataclass
class ConnectionContext:
    websocket: WebSocket
    connection_id: str
    user_id: str
    queue: asyncio.Queue[str] = field(default_factory=lambda: asyncio.Queue(MAX_QUEUE_SIZE))
    sender_task: Optional[asyncio.Task] = None
    created_at: datetime = field(default_factory=utcnow)
    last_seen: datetime = field(default_factory=utcnow)


class ConnectionManager:
    """
    Manages active WebSocket connections with bounded queues to avoid head-of-line
    blocking and implements graceful teardown on errors or backpressure.
    """

    def __init__(self) -> None:
        self._connections: Dict[str, ConnectionContext] = {}
        self._user_connections: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str) -> ConnectionContext:
        await websocket.accept()
        connection_id = f"{user_id}:{uuid.uuid4().hex}"
        context = ConnectionContext(websocket=websocket, user_id=user_id, connection_id=connection_id)

        async with self._lock:
            self._connections[connection_id] = context
            self._user_connections.setdefault(user_id, set()).add(connection_id)

        context.sender_task = asyncio.create_task(self._sender_loop(context))
        logger.info("WebSocket connected: %s for user %s", connection_id, user_id)
        return context

    async def close(self, context: ConnectionContext, reason: str) -> None:
        async with self._lock:
            if context.connection_id not in self._connections:
                return
            self._connections.pop(context.connection_id, None)
            user_set = self._user_connections.get(context.user_id)
            if user_set:
                user_set.discard(context.connection_id)
                if not user_set:
                    self._user_connections.pop(context.user_id, None)

        if context.sender_task and context.sender_task is not asyncio.current_task():
            context.sender_task.cancel()
            with suppress(asyncio.CancelledError):
                await context.sender_task

        with suppress(Exception):
            await context.websocket.close(code=4000, reason=reason)

        logger.info("WebSocket disconnected: %s reason=%s", context.connection_id, reason)

    async def _sender_loop(self, context: ConnectionContext) -> None:
        try:
            while True:
                payload = await context.queue.get()
                await context.websocket.send_text(payload)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning(
                "Sender loop error for %s (%s): %s", context.connection_id, context.user_id, exc
            )
        finally:
            await self.close(context, "sender loop terminated")

    async def enqueue(self, context: ConnectionContext, message: Dict[str, Any]) -> None:
        payload = json.dumps(message)
        try:
            context.queue.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning(
                "Backpressure threshold exceeded for %s (%s); closing connection.",
                context.connection_id,
                context.user_id,
            )
            await self.close(context, "backpressure exceeded")

    async def send_personal_message(self, message: Dict[str, Any], user_id: str) -> None:
        contexts = await self._get_user_contexts(user_id)
        for context in contexts:
            await self.enqueue(context, message)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        contexts = await self._get_all_contexts()
        for context in contexts:
            await self.enqueue(context, message)

    async def _get_user_contexts(self, user_id: str) -> List[ConnectionContext]:
        async with self._lock:
            connection_ids = list(self._user_connections.get(user_id, set()))
            return [
                self._connections[cid]
                for cid in connection_ids
                if cid in self._connections
            ]

    async def _get_all_contexts(self) -> List[ConnectionContext]:
        async with self._lock:
            return list(self._connections.values())

    def get_connection_count(self) -> int:
        return len(self._connections)

    def get_user_count(self) -> int:
        return len(self._user_connections)


manager = ConnectionManager()


def _decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        logger.warning("Failed to decode websocket token: %s", exc)
        return None

    username = payload.get("sub")
    if not username:
        return None

    roles = payload.get("roles") or []
    scopes = payload.get("scopes") or []
    read_only = bool(payload.get("read_only", False))

    if not isinstance(roles, list):
        roles = [str(roles)]
    if not isinstance(scopes, list):
        scopes = [str(scopes)]

    return TokenData(
        username=str(username),
        roles=[str(role) for role in roles],
        scopes=[str(scope) for scope in scopes],
        read_only=read_only,
    )


@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    WebSocket endpoint for real-time updates.
    """
    context: Optional[ConnectionContext] = None
    token_data = _decode_token(token)
    if not token_data or not token_data.username:
        await websocket.close(code=4001, reason="Invalid token")
        return

    try:
        context = await manager.connect(websocket, token_data.username)
        await manager.enqueue(
            context,
            {
                "type": "connection_established",
                "data": {
                    "connection_id": context.connection_id,
                    "user_id": token_data.username,
                    "timestamp": utcnow().isoformat(),
                },
            },
        )

        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=CLIENT_TIMEOUT.total_seconds())
            except asyncio.TimeoutError:
                await manager.enqueue(
                    context,
                    {
                        "type": "disconnecting",
                        "reason": "idle_timeout",
                        "timestamp": utcnow().isoformat(),
                    },
                )
                break

            context.last_seen = utcnow()

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await manager.enqueue(
                    context,
                    {
                        "type": "error",
                        "message": "Invalid JSON payload",
                        "timestamp": utcnow().isoformat(),
                    },
                )
                continue

            message_type = message.get("type", "unknown")

            if message_type == "ping":
                await manager.enqueue(
                    context,
                    {"type": "pong", "timestamp": utcnow().isoformat()},
                )

            elif message_type == "subscribe":
                event_type = message.get("event_type")
                await manager.enqueue(
                    context,
                    {
                        "type": "subscription_confirmed",
                        "event_type": event_type,
                        "timestamp": utcnow().isoformat(),
                    },
                )

            else:
                await manager.enqueue(
                    context,
                    {
                        "type": "echo",
                        "original_message": message,
                        "timestamp": utcnow().isoformat(),
                    },
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnect received for user %s", token_data.username)
    except Exception as exc:
        logger.exception("WebSocket error for user %s: %s", token_data.username, exc)
    finally:
        if context:
            await manager.close(context, "client disconnect")


@router.get("/ws/status")
async def websocket_status():
    """
    Get WebSocket connection status.
    """
    return {
        "active_connections": manager.get_connection_count(),
        "connected_users": manager.get_user_count(),
        "timestamp": utcnow().isoformat(),
    }


# Functions to send real-time updates (can be called from other parts of the application)
async def send_tournament_update(tournament_data: dict):
    await manager.broadcast(
        {
            "type": "tournament_update",
            "data": tournament_data,
            "timestamp": utcnow().isoformat(),
        }
    )


async def send_user_update(user_data: dict):
    await manager.broadcast(
        {
            "type": "user_update",
            "data": user_data,
            "timestamp": utcnow().isoformat(),
        }
    )


async def send_configuration_update(config_data: dict):
    await manager.broadcast(
        {
            "type": "configuration_update",
            "data": config_data,
            "timestamp": utcnow().isoformat(),
        }
    )


async def send_system_notification(notification: dict):
    await manager.broadcast(
        {
            "type": "system_notification",
            "data": notification,
            "timestamp": utcnow().isoformat(),
        }
    )


async def send_placement_update(round_name: str, lobby_updates: List[dict]):
    """
    Notify dashboard clients that placements were updated.
    Dashboard should refresh standings data.
    
    Args:
        round_name: Name of the round that was updated
        lobby_updates: List of placement updates with lobby, player, placement info
    """
    await manager.broadcast({
        "type": "placement_update",
        "data": {
            "round": round_name,
            "lobby_updates": lobby_updates,
            "action": "refresh",
            "timestamp": utcnow().isoformat(),
        }
    })


__all__ = [
    "send_tournament_update",
    "send_user_update",
    "send_configuration_update",
    "send_system_notification",
    "manager",
]
