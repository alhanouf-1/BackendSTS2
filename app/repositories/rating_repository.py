import uuid
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.rating import Rating
from app.repositories.base import BaseRepository

class RatingRepository(BaseRepository[Rating]):
    """Repository managing Rating (1-5 review scale) database operations."""
    def __init__(self, db: AsyncSession):
        super().__init__(Rating, db)

    async def get_by_student_and_course(self, student_id: uuid.UUID, course_id: uuid.UUID) -> Optional[Rating]:
        """Checks if a student has already review-rated a course."""
        query = select(Rating).where(
            Rating.student_id == student_id,
            Rating.course_id == course_id,
            Rating.is_deleted == False
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_average_course_rating(self, course_id: uuid.UUID) -> float:
        """Calculates rating average across all active feedback logs."""
        query = select(func.avg(Rating.rating_value)).where(
            Rating.course_id == course_id,
            Rating.is_deleted == False
        )
        result = await self.db.execute(query)
        val = result.scalar()
        return float(val) if val is not None else 0.0
