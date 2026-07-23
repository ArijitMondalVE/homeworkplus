import json
from typing import Any
from loguru import logger

from app.websocket.manager import ws_manager
from app.websocket.redis_pubsub import redis_pubsub

class WhiteboardService:
    @staticmethod
    async def get_room_state(room_id: str) -> dict:
        client = redis_pubsub.redis_client
        if not client:
            return {}
        state_key = f"whiteboard:state:{room_id}"
        state = await client.hgetall(state_key)
        if not state:
            return {}
        return {
            "admin_id": state.get("admin_id", ""),
            "drawers": json.loads(state.get("drawers", "[]")),
            "canvas_state": json.loads(state.get("canvas_state", '{"objects": []}'))
        }

    @staticmethod
    async def enforce_drawing_permissions(room_id: str, user_id: str) -> bool:
        state = await WhiteboardService.get_room_state(room_id)
        if not state:
            return False
            
        if user_id != state["admin_id"] and user_id not in state["drawers"]:
            logger.debug(f"IGNORING unauthorized draw from {user_id}")
            return False
        return True

    @staticmethod
    async def update_server_state(room_id: str, msg_type: str, data: Any) -> None:
        client = redis_pubsub.redis_client
        if not client:
            return
        state_key = f"whiteboard:state:{room_id}"
        
        canvas_json = await client.hget(state_key, "canvas_state")
        if not canvas_json:
            canvas_state = {"version": "6.4.2", "objects": []}
        else:
            try:
                canvas_state = json.loads(canvas_json)
            except Exception:
                canvas_state = {"version": "6.4.2", "objects": []}

        if msg_type == "object_added" and data:
            canvas_state["objects"].append(data)
            
        elif msg_type == "object_modified" and data:
            for idx, obj in enumerate(canvas_state.get("objects", [])):
                if obj.get("id") == data.get("id"):
                    canvas_state["objects"][idx].update(data)
                    break
                    
        elif msg_type == "clear":
            canvas_state["objects"] = []
            
        elif msg_type == "object_removed" and data:
            obj_id = data.get("id")
            if obj_id:
                canvas_state["objects"] = [
                    obj for obj in canvas_state.get("objects", [])
                    if obj.get("id") != obj_id
                ]
            
        elif msg_type == "canvas_update" and data:
            if isinstance(data, str):
                try:
                    canvas_state = json.loads(data)
                except Exception:
                    pass
            else:
                canvas_state = data
                
        await client.hset(state_key, "canvas_state", json.dumps(canvas_state))

    @staticmethod
    async def toggle_access(room_id: str, admin_id: str, target_id: str):
        state = await WhiteboardService.get_room_state(room_id)
        if not state or admin_id != state["admin_id"]:
            return
            
        drawers = set(state["drawers"])
        if target_id in drawers:
            drawers.discard(target_id)
        else:
            drawers.add(target_id)
            
        drawers_list = list(drawers)
        client = redis_pubsub.redis_client
        if client:
            await client.hset(f"whiteboard:state:{room_id}", "drawers", json.dumps(drawers_list))
            
        await ws_manager.broadcast_to_room(
            room_id=room_id,
            message={"type": "permissions_update", "allowed_drawers": drawers_list}
        )

    @staticmethod
    async def kick_user(room_id: str, admin_id: str, target_id: str):
        state = await WhiteboardService.get_room_state(room_id)
        if not state or admin_id != state["admin_id"]:
            return
            
        await ws_manager.broadcast_to_room(
            room_id=room_id,
            message={"type": "kicked", "target_id": target_id}
        )

    @staticmethod
    async def promote_admin(room_id: str, admin_id: str, target_id: str):
        state = await WhiteboardService.get_room_state(room_id)
        if not state or admin_id != state["admin_id"]:
            return
            
        drawers = set(state["drawers"])
        drawers.add(target_id)
        drawers_list = list(drawers)
        
        client = redis_pubsub.redis_client
        if client:
            state_key = f"whiteboard:state:{room_id}"
            await client.hset(state_key, "admin_id", target_id)
            await client.hset(state_key, "drawers", json.dumps(drawers_list))
            
        await ws_manager.broadcast_to_room(
            room_id=room_id,
            message={"type": "admin_promoted", "admin_id": target_id, "allowed_drawers": drawers_list}
        )

    @staticmethod
    async def disband_room(room_id: str, admin_id: str):
        state = await WhiteboardService.get_room_state(room_id)
        if not state or admin_id != state["admin_id"]:
            return
            
        await ws_manager.broadcast_to_room(
            room_id=room_id,
            message={"type": "room_disbanded"}
        )
        connections = list(ws_manager.rooms.get(room_id, set()))
        for ws in connections:
            try:
                await ws.close()
            except Exception:
                pass
            await ws_manager.disconnect(ws, room_id)
