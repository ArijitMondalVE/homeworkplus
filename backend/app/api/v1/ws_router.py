"""
WebSocket endpoints — real-time whiteboard and chat.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.websocket.manager import ws_manager

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/whiteboard/{room_id}")
async def whiteboard_websocket(websocket: WebSocket, room_id: str):
    """
    Real-time collaborative whiteboard.
    Message types: canvas_update, cursor_move, clear, undo
    """
    user_id = websocket.query_params.get("user_id", "anonymous")
    user_name = websocket.query_params.get("user_name", "Anonymous")
    await ws_manager.connect(websocket, f"whiteboard:{room_id}", user_id, user_name)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "unknown")

            if msg_type in ("canvas_update", "cursor_move", "clear", "undo", "add_object", "object_added", "object_modified"):
                # Enforce drawing permissions
                room_key = f"whiteboard:{room_id}"
                admin_id = ws_manager.room_admins.get(room_key)
                allowed_drawers = ws_manager.room_drawers.get(room_key, set())
                
                print(f"DEBUG: msg={msg_type}, sender={user_id}, admin={admin_id}, allowed={allowed_drawers}")
                if user_id != admin_id and user_id not in allowed_drawers:
                    print(f"DEBUG: IGNORING unauthorized draw from {user_id}")
                    # Silently ignore unauthorized drawing commands
                    continue

                print(f"DEBUG: Broadcasting {msg_type} from {user_id} to room {room_key}")

                # Broadcast to all peers in the room
                await ws_manager.broadcast_to_room(
                    room_id=room_key,
                    message={"type": msg_type, "data": data.get("data"), "sender": user_id},
                    exclude=websocket,
                )
            
            elif msg_type == "toggle_access":
                room_key = f"whiteboard:{room_id}"
                if user_id == ws_manager.room_admins.get(room_key):
                    target_id = data.get("target_id")
                    if target_id in ws_manager.room_drawers[room_key]:
                        ws_manager.room_drawers[room_key].discard(target_id)
                    else:
                        ws_manager.room_drawers[room_key].add(target_id)
                    
                    await ws_manager.broadcast_to_room(
                        room_id=room_key,
                        message={"type": "permissions_update", "allowed_drawers": list(ws_manager.room_drawers[room_key])}
                    )
            
            elif msg_type == "promote_admin":
                room_key = f"whiteboard:{room_id}"
                if user_id == ws_manager.room_admins.get(room_key):
                    target_id = data.get("target_id")
                    ws_manager.room_admins[room_key] = target_id
                    ws_manager.room_drawers[room_key].add(target_id)
                    
                    await ws_manager.broadcast_to_room(
                        room_id=room_key,
                        message={"type": "admin_promoted", "admin_id": target_id, "allowed_drawers": list(ws_manager.room_drawers[room_key])}
                    )
            
            elif msg_type == "disband_room":
                room_key = f"whiteboard:{room_id}"
                if user_id == ws_manager.room_admins.get(room_key):
                    await ws_manager.broadcast_to_room(
                        room_id=room_key,
                        message={"type": "room_disbanded"}
                    )
                    # Disconnect all active connections
                    connections = list(ws_manager.active_connections.get(room_key, []))
                    for ws in connections:
                        await ws.close()
                        ws_manager.disconnect(ws, room_key)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, f"whiteboard:{room_id}")
        count = len(ws_manager.active_connections.get(f"whiteboard:{room_id}", []))
        users = ws_manager.get_room_users(f"whiteboard:{room_id}")
        await ws_manager.broadcast_to_room(
            f"whiteboard:{room_id}",
            {"type": "user_left", "user_id": user_id, "user_count": count, "users": users},
        )


@router.websocket("/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """
    Real-time AI chat session.
    Message types: user_message, typing_start, typing_stop
    """
    user_id = websocket.query_params.get("user_id", "anonymous")
    await ws_manager.connect(websocket, f"chat:{session_id}", user_id)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "unknown")

            if msg_type == "user_message":
                # Echo for now — full LLM integration via HTTP /ai/chat endpoint
                await ws_manager.send_personal(websocket, {
                    "type": "ack",
                    "message": "Message received. Use /api/v1/ai/chat for AI responses.",
                })
            elif msg_type in ("typing_start", "typing_stop"):
                await ws_manager.broadcast_to_room(
                    f"chat:{session_id}",
                    {"type": msg_type, "user_id": user_id},
                    exclude=websocket,
                )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, f"chat:{session_id}")
