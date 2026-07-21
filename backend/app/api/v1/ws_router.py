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
    await ws_manager.connect(websocket, f"whiteboard:{room_id}", user_id)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "unknown")

            if msg_type in ("canvas_update", "cursor_move", "clear", "undo", "add_object"):
                # Broadcast to all peers in the room
                await ws_manager.broadcast_to_room(
                    room_id=f"whiteboard:{room_id}",
                    message={"type": msg_type, "data": data.get("data"), "sender": user_id},
                    exclude=websocket,
                )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, f"whiteboard:{room_id}")
        await ws_manager.broadcast_to_room(
            f"whiteboard:{room_id}",
            {"type": "user_left", "user_id": user_id},
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
