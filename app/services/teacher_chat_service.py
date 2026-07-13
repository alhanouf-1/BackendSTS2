import uuid
from typing import Dict, Set, Optional
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat_message import ChatMessage, AttachmentType
from app.repositories.chat_repository import ChatRepository
from app.config.logging import logger

class TeacherChatService:
    """Manages active WebSockets channels and message routing for teachers."""
    
    # Active local room registry mapping room keys (e.g., 'course_{uuid}', 'session_{uuid}') to WebSocket sets
    active_rooms: Dict[str, Set[WebSocket]] = {}

    @classmethod
    async def connect_room(cls, websocket: WebSocket, room_key: str) -> None:
        """Registers a teacher client connection to a specific channel room."""
        await websocket.accept()
        if room_key not in cls.active_rooms:
            cls.active_rooms[room_key] = set()
        cls.active_rooms[room_key].add(websocket)
        logger.info(f"Teacher registered to channel {room_key}", count=len(cls.active_rooms[room_key]))

    @classmethod
    def disconnect_room(cls, websocket: WebSocket, room_key: str) -> None:
        """Removes a teacher client connection from a specific channel room."""
        if room_key in cls.active_rooms:
            cls.active_rooms[room_key].discard(websocket)
            if not cls.active_rooms[room_key]:
                del cls.active_rooms[room_key]
        logger.info(f"Teacher unregistered from channel {room_key}")

    @classmethod
    async def broadcast_to_room(cls, room_key: str, payload: dict) -> None:
        """Broadcasts a JSON message payload to all active local room connections."""
        if room_key in cls.active_rooms:
            for connection in list(cls.active_rooms[room_key]):
                try:
                    await connection.send_json(payload)
                except Exception as e:
                    logger.error(f"Failed to deliver room broadcast to websocket client in {room_key}", error=str(e))
                    cls.disconnect_room(connection, room_key)

    @classmethod
    async def save_message(
        cls,
        db: AsyncSession,
        sender_id: uuid.UUID,
        course_id: Optional[uuid.UUID] = None,
        session_id: Optional[uuid.UUID] = None,
        message_text: Optional[str] = None,
        attachment_url: Optional[str] = None,
        attachment_type: AttachmentType = AttachmentType.NONE
    ) -> ChatMessage:
        """Persists a new chat message record inside the database."""
        chat_repo = ChatRepository(db)
        message = ChatMessage(
            sender_id=sender_id,
            course_id=course_id,
            session_id=session_id,
            message_text=message_text,
            attachment_url=attachment_url,
            attachment_type=attachment_type
        )
        await chat_repo.create(message)
        await db.commit()
        return message
