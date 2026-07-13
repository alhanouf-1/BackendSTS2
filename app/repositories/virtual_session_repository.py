import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.virtual_session import VirtualSession
from app.models.virtual_session_attendee import VirtualSessionAttendee
from app.repositories.base import BaseRepository

class VirtualSessionRepository(BaseRepository[VirtualSession]):
    """Repository managing VirtualSession and VirtualSessionAttendee structures."""
    def __init__(self, db: AsyncSession):
        super().__init__(VirtualSession, db)

    async def get_upcoming_sessions_by_courses(self, course_ids: List[uuid.UUID], start_time: datetime, end_time: datetime) -> List[VirtualSession]:
        """Fetches upcoming virtual live classes scheduled in courses enrolled by the student."""
        if not course_ids:
            return []
        query = select(VirtualSession).where(
            VirtualSession.course_id.in_(course_ids),
            VirtualSession.scheduled_at >= start_time,
            VirtualSession.scheduled_at <= end_time,
            VirtualSession.is_deleted == False
        ).order_by(VirtualSession.scheduled_at.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_attendee(self, session_id: uuid.UUID, student_id: uuid.UUID) -> Optional[VirtualSessionAttendee]:
        """Checks if a student has already reserved a seat in a virtual session."""
        query = select(VirtualSessionAttendee).where(
            VirtualSessionAttendee.session_id == session_id,
            VirtualSessionAttendee.student_id == student_id,
            VirtualSessionAttendee.is_deleted == False
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
