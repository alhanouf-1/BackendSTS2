import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.virtual_session import VirtualSession
from app.models.virtual_session_attendee import VirtualSessionAttendee
from app.repositories.virtual_session_repository import VirtualSessionRepository

class StudentClassService:
    """Orchestrates virtual classroom reservations and stream session allocations."""

    @staticmethod
    async def reserve_seat(db: AsyncSession, student_id: uuid.UUID, session_id: uuid.UUID) -> VirtualSessionAttendee:
        # Check if virtual session exists
        session_repo = VirtualSessionRepository(db)
        session = await session_repo.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Virtual session not found or soft-deleted."
            )

        # Check if already reserved
        existing = await session_repo.get_attendee(session_id, student_id)
        if existing:
            return existing

        # Create attendee reservation record
        attendee = VirtualSessionAttendee(
            session_id=session_id,
            student_id=student_id
        )
        db.add(attendee)
        await db.flush()
        return attendee
