"""
WebSocket endpoints — real-time whiteboard and chat.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import ValidationError

from app.websocket.manager import ws_manager
from app.auth.security import verify_access_token
from app.services.whiteboard_service import WhiteboardService
from app.schemas.ws_schemas import BaseWSMessage

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/whiteboard/{room_id}")
async def whiteboard_websocket(websocket: WebSocket, room_id: str):
    """
    Real-time collaborative whiteboard.
    Message types: canvas_update, cursor_move, clear, undo
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return
        
    payload = verify_access_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid token")
        return
        
    user_id = payload.get("sub", "anonymous")
    user_name = websocket.query_params.get("user_name", "Anonymous")
    
    room_key = f"whiteboard:{room_id}"
    await ws_manager.connect(websocket, room_key, user_id, user_name)

    try:
        while True:
            raw_data = await websocket.receive_json()
            try:
                msg = BaseWSMessage(**raw_data)
                msg_type = msg.type
            except ValidationError as e:
                logger.error(f"Invalid WebSocket message: {e}")
                continue
                
            data = raw_data

            if msg_type in ("canvas_update", "cursor_move", "clear", "undo", "add_object", "object_added", "object_modified", "object_removed", "draw_start", "draw_move", "draw_end"):
                
                can_draw = await WhiteboardService.enforce_drawing_permissions(room_key, user_id)
                if not can_draw:
                    continue

                await WhiteboardService.update_server_state(room_key, msg_type, data.get("data"))

                payload_msg = data.copy()
                payload_msg["sender"] = user_id
                await ws_manager.broadcast_to_room(
                    room_id=room_key,
                    message=payload_msg,
                    exclude=websocket,
                )
            
            elif msg_type == "toggle_access":
                await WhiteboardService.toggle_access(room_key, user_id, data.get("target_id"))
            
            elif msg_type == "kick_user":
                await WhiteboardService.kick_user(room_key, user_id, data.get("target_id"))
            
            elif msg_type == "promote_admin":
                await WhiteboardService.promote_admin(room_key, user_id, data.get("target_id"))
            
            elif msg_type == "disband_room":
                await WhiteboardService.disband_room(room_key, user_id)
                        
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, room_key)


@router.websocket("/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    """
    Real-time AI chat session.
    Message types: user_message, typing_start, typing_stop
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return
        
    payload = verify_access_token(token)
    if not payload:
        await websocket.close(code=1008, reason="Invalid token")
        return
        
    user_id = payload.get("sub", "anonymous")
    
    await ws_manager.connect(websocket, f"chat:{session_id}", user_id)

    try:
        while True:
            raw_data = await websocket.receive_json()
            try:
                msg = BaseWSMessage(**raw_data)
                msg_type = msg.type
            except ValidationError as e:
                logger.error(f"Invalid WebSocket message: {e}")
                continue

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
        await ws_manager.disconnect(websocket, f"chat:{session_id}")
