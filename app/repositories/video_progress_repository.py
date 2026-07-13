import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.student_video_progress import StudentVideoProgress
from app.models.lesson import Lesson
from app.repositories.base import BaseRepository

class VideoProgressRepository(BaseRepository[StudentVideoProgress]):
    """Repository managing StudentVideoProgress database operations."""
    def __init__(self, db: AsyncSession):
        super().__init__(StudentVideoProgress, db)

    async def get_by_student_and_lesson(self, student_id: uuid.UUID, lesson_id: uuid.UUID) -> Optional[StudentVideoProgress]:
        """Fetches video progress record by student and lesson association."""
        query = select(StudentVideoProgress).where(
            StudentVideoProgress.student_id == student_id,
            StudentVideoProgress.lesson_id == lesson_id,
            StudentVideoProgress.is_deleted == False
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_course_video_progresses(self, student_id: uuid.UUID, course_id: uuid.UUID) -> List[StudentVideoProgress]:
        """Fetches video progresses across all lessons in a course."""
        query = (
            select(StudentVideoProgress)
            .join(StudentVideoProgress.lesson)
            .where(
                StudentVideoProgress.student_id == student_id,
                Lesson.course_id == course_id,
                StudentVideoProgress.is_deleted == False
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
