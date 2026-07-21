"""
WebSocket Manager — Real-time connections for chat, whiteboard, and voice.
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """Manages WebSocket connections grouped by room/session."""

    def __init__(self):
        # room_id -> list of connected WebSockets
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)
        # websocket -> user_id
        self.user_map: dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, room_id: str, user_id: str) -> None:
        await websocket.accept()
        self.active_connections[room_id].append(websocket)
        self.user_map[websocket] = user_id
        logger.info(f"[WS] User {user_id} connected to room {room_id}")

        # Notify others
        await self.broadcast_to_room(
            room_id=room_id,
            message={"type": "user_joined", "user_id": user_id},
            exclude=websocket,
        )

    def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        user_id = self.user_map.pop(websocket, "unknown")
        if websocket in self.active_connections[room_id]:
            self.active_connections[room_id].remove(websocket)
        if not self.active_connections[room_id]:
            del self.active_connections[room_id]
        logger.info(f"[WS] User {user_id} disconnected from room {room_id}")

    async def send_personal(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"[WS] Failed to send personal message: {e}")

    async def broadcast_to_room(
        self,
        room_id: str,
        message: dict[str, Any],
        exclude: WebSocket | None = None,
    ) -> None:
        connections = list(self.active_connections.get(room_id, []))
        dead = []
        for ws in connections:
            if ws is exclude:
                continue
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.active_connections[room_id].remove(ws)

    def get_room_users(self, room_id: str) -> list[str]:
        return [
            self.user_map[ws]
            for ws in self.active_connections.get(room_id, [])
            if ws in self.user_map
        ]

    def get_active_rooms(self) -> list[str]:
        return list(self.active_connections.keys())


# Singleton
ws_manager = ConnectionManager()
