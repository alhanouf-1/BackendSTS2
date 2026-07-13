import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.enrollment import Enrollment
from app.repositories.base import BaseRepository

class EnrollmentRepository(BaseRepository[Enrollment]):
    """Repository managing Enrollment database transactions and queries."""
    def __init__(self, db: AsyncSession):
        super().__init__(Enrollment, db)

    async def get_by_student_and_course(self, student_id: uuid.UUID, course_id: uuid.UUID) -> Optional[Enrollment]:
        """Fetches enrollment record by student and course ID association."""
        query = select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.course_id == course_id,
            Enrollment.is_deleted == False
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_student_enrollments(self, student_id: uuid.UUID) -> List[Enrollment]:
        """Fetches all active enrollments for a given student ID."""
        query = select(Enrollment).where(
            Enrollment.student_id == student_id,
            Enrollment.is_deleted == False
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
