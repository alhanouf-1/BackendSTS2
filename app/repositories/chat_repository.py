import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat_message import ChatMessage
from app.repositories.base import BaseRepository

class ChatRepository(BaseRepository[ChatMessage]):
    """Repository managing ChatMessage database transactions and sweeps."""
    def __init__(self, db: AsyncSession):
        super().__init__(ChatMessage, db)

    async def get_course_chat_history(self, course_id: uuid.UUID, limit: int = 50) -> List[ChatMessage]:
        """Fetches active chat logs for a general course channel."""
        query = (
            select(ChatMessage)
            .where(
                ChatMessage.course_id == course_id,
                ChatMessage.session_id == None,
                ChatMessage.is_deleted == False
            )
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_session_chat_history(self, session_id: uuid.UUID, limit: int = 50) -> List[ChatMessage]:
        """Fetches active chat logs for a specific live session room."""
        query = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.is_deleted == False
            )
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
