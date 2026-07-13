import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.virtual_session import VirtualSession, SessionStatus
from app.models.virtual_session_attendee import VirtualSessionAttendee
from app.repositories.virtual_session_repository import VirtualSessionRepository
from app.repositories.course_repository import CourseRepository
from app.tasks.email_tasks import send_email

class TeacherClassService:
    """Orchestrates scheduling and cancellations of virtual live sessions."""

    @staticmethod
    async def schedule_session(
        db: AsyncSession,
        teacher_id: uuid.UUID,
        course_id: uuid.UUID,
        title: str,
        date_str: str,
        time_str: str,
        duration_minutes: int
    ) -> VirtualSession:
        # Check course ownership
        course_repo = CourseRepository(db)
        course = await course_repo.get_by_id(course_id)
        if not course or course.teacher_id != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course profile not found or ownership validation failed."
            )

        # Parse schedule date and time
        try:
            dt_str = f"{date_str} {time_str}"
            scheduled_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date or time parameters. Formats must be YYYY-MM-DD and HH:MM."
            )

        session = VirtualSession(
            course_id=course_id,
            title=title,
            meeting_room_id=f"room_{uuid.uuid4().hex[:12]}",
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            status=SessionStatus.UPCOMING
        )
        db.add(session)
        await db.flush()
        return session

    @staticmethod
    async def cancel_session(
        db: AsyncSession,
        teacher_id: uuid.UUID,
        session_id: uuid.UUID
    ) -> None:
        session_repo = VirtualSessionRepository(db)
        session = await session_repo.get_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Virtual session not found."
            )

        # Check course ownership
        course_repo = CourseRepository(db)
        course = await course_repo.get_by_id(session.course_id)
        if not course or course.teacher_id != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Ownership validation failed."
            )

        # Find all registered attendees to notify
        attendee_query = select(VirtualSessionAttendee).where(
            VirtualSessionAttendee.session_id == session_id
        )
        attendees_result = await db.execute(attendee_query)
        attendees = list(attendees_result.scalars().all())

        # Email notification triggers
        for attendee in attendees:
            # Load student email details
            from app.models.user import User
            student_res = await db.execute(select(User).where(User.id == attendee.student_id))
            student = student_res.scalar_one_or_none()
            if student:
                email_body = (
                    f"Hello,\n\nPlease be notified that your scheduled live class session "
                    f"'{session.title}' for course '{course.title}' has been cancelled by the instructor.\n\n"
                    f"Sincerely,\nThe STS Team"
                )
                send_email.delay(student.email, "Virtual Class Cancellation", email_body)

        # Wipe virtual session row
        await db.delete(session)
        await db.commit()
