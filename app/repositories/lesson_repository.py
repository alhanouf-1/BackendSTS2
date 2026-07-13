import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.lesson import Lesson
from app.repositories.base import BaseRepository

class LessonRepository(BaseRepository[Lesson]):
    """Repository managing Lesson database transaction operations."""
    def __init__(self, db: AsyncSession):
        super().__init__(Lesson, db)

    async def get_lessons_by_course(self, course_id: uuid.UUID) -> List[Lesson]:
        """Fetches active lessons ordered by order index for a course."""
        query = select(Lesson).where(
            Lesson.course_id == course_id,
            Lesson.is_deleted == False
        ).order_by(Lesson.order.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
