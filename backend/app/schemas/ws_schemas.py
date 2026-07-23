from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BaseWSMessage(BaseModel):
    type: str
    sender: Optional[str] = None
    client_id: Optional[str] = None


class TargetUserMessage(BaseWSMessage):
    target_id: str


class CanvasUpdateMessage(BaseWSMessage):
    data: Any


class CursorMoveMessage(BaseWSMessage):
    pointer: Dict[str, float]


class GenericRoomMessage(BaseWSMessage):
    pass


class ChatUserMessage(BaseWSMessage):
    pass
