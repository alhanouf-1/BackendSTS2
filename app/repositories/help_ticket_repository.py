import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.help_ticket import HelpTicket
from app.repositories.base import BaseRepository

class HelpTicketRepository(BaseRepository[HelpTicket]):
    """Repository managing HelpTicket database scopes."""
    def __init__(self, db: AsyncSession):
        super().__init__(HelpTicket, db)

    async def get_student_tickets(self, student_id: uuid.UUID) -> List[HelpTicket]:
        """Gets history list of help ticket logs registered by a student."""
        query = select(HelpTicket).where(
            HelpTicket.student_id == student_id,
            HelpTicket.is_deleted == False
        ).order_by(HelpTicket.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
