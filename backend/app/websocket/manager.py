import json
import asyncio
from typing import Any
from fastapi import WebSocket
from loguru import logger
from app.websocket.redis_pubsub import redis_pubsub

class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, set[WebSocket]] = {}
        self.user_map: dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, room_id: str, user_id: str, user_name: str = "Anonymous") -> None:
        await websocket.accept()
        
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            await redis_pubsub.subscribe(room_id, self.make_callback(room_id))
            
        self.rooms[room_id].add(websocket)
        self.user_map[websocket] = {"id": user_id, "name": user_name}
        
        client = redis_pubsub.redis_client
        state_key = f"whiteboard:state:{room_id}"
        users_key = f"whiteboard:users:{room_id}"
        conn_key = f"whiteboard:conns:{room_id}:{user_id}"
        
        await client.incr(conn_key)
        await client.hset(users_key, user_id, user_name)
        
        user_count = await client.hlen(users_key)
        is_first = (user_count == 1)
        
        if is_first:
            await client.hset(state_key, "admin_id", user_id)
            await client.hset(state_key, "drawers", json.dumps([user_id]))
            await client.hset(state_key, "canvas_state", json.dumps({"objects": []}))
            
        admin_id = await client.hget(state_key, "admin_id") or ""
        drawers_json = await client.hget(state_key, "drawers")
        drawers = json.loads(drawers_json) if drawers_json else []
        canvas_json = await client.hget(state_key, "canvas_state")
        
        all_users_raw = await client.hgetall(users_key)
        all_users = [{"id": k, "name": v} for k, v in all_users_raw.items()]
        
        logger.info(f"[WS] User {user_name} ({user_id}) connected to room {room_id}")

        await self.send_personal(
            websocket,
            {"type": "room_info", "user_count": len(all_users), "users": all_users, "admin_id": admin_id, "allowed_drawers": drawers}
        )
        
        if canvas_json:
            await self.send_personal(websocket, {"type": "canvas_update", "data": canvas_json})

        await self.broadcast_to_room(
            room_id,
            {"type": "user_joined", "user_id": user_id, "user_name": user_name, "user_count": len(all_users), "users": all_users, "admin_id": admin_id, "allowed_drawers": drawers},
            exclude=websocket
        )

    def make_callback(self, room_id: str):
        async def callback(data: dict):
            connections = list(self.rooms.get(room_id, []))
            exclude_id = data.pop("_exclude_ws_id", None)
            
            async def _send(ws: WebSocket):
                if exclude_id and id(ws) == exclude_id:
                    return None
                try:
                    await ws.send_text(json.dumps(data))
                    return None
                except Exception:
                    return ws
                    
            results = await asyncio.gather(*[_send(ws) for ws in connections], return_exceptions=True)
            dead = [ws for ws in results if ws is not None and isinstance(ws, WebSocket)]
            for ws in dead:
                if room_id in self.rooms and ws in self.rooms[room_id]:
                    self.rooms[room_id].remove(ws)
                    
        return callback

    async def disconnect(self, websocket: WebSocket, room_id: str) -> None:
        user_info = self.user_map.pop(websocket, {"id": "unknown", "name": "unknown"})
        user_id = user_info["id"]
        
        if room_id in self.rooms and websocket in self.rooms[room_id]:
            self.rooms[room_id].remove(websocket)
            if not self.rooms[room_id]:
                del self.rooms[room_id]
                await redis_pubsub.unsubscribe(room_id)
                
        client = redis_pubsub.redis_client
        if not client:
            return
            
        users_key = f"whiteboard:users:{room_id}"
        state_key = f"whiteboard:state:{room_id}"
        conn_key = f"whiteboard:conns:{room_id}:{user_id}"
        
        conn_count = await client.decr(conn_key)
        
        if conn_count <= 0:
            await client.hdel(users_key, user_id)
            await client.delete(conn_key)
            
        user_count = await client.hlen(users_key)
        
        if user_count == 0:
            await client.delete(state_key)
            await client.delete(users_key)
        else:
            admin_id = await client.hget(state_key, "admin_id")
            if admin_id == user_id:
                remaining_users = await client.hkeys(users_key)
                if remaining_users:
                    new_admin_id = remaining_users[0]
                    await client.hset(state_key, "admin_id", new_admin_id)
                    drawers_json = await client.hget(state_key, "drawers")
                    drawers = json.loads(drawers_json) if drawers_json else []
                    if new_admin_id not in drawers:
                        drawers.append(new_admin_id)
                        await client.hset(state_key, "drawers", json.dumps(drawers))
                        
                    logger.info(f"[WS] Admin {user_id} left. Promoted {new_admin_id} to admin.")
                    await self.broadcast_to_room(room_id, {
                        "type": "admin_promoted",
                        "admin_id": new_admin_id,
                        "allowed_drawers": drawers
                    })
                    
            all_users_raw = await client.hgetall(users_key)
            all_users = [{"id": k, "name": v} for k, v in all_users_raw.items()]
            await self.broadcast_to_room(room_id, {
                "type": "user_left",
                "user_id": user_id,
                "user_count": user_count,
                "users": all_users
            })

    async def send_personal(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"[WS] Failed to send personal message: {e}")

    async def broadcast_to_room(self, room_id: str, message: dict[str, Any], exclude: WebSocket | None = None) -> None:
        if exclude:
            message["_exclude_ws_id"] = id(exclude)
        await redis_pubsub.publish(room_id, message)

ws_manager = ConnectionManager()
