import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.teacher_verification import TeacherVerification
from app.repositories.base import BaseRepository

class TeacherVerificationRepository(BaseRepository[TeacherVerification]):
    """Repository managing TeacherVerification database transaction scopes."""
    def __init__(self, db: AsyncSession):
        super().__init__(TeacherVerification, db)

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[TeacherVerification]:
        """Fetches active TeacherVerification record by User ID association."""
        query = select(TeacherVerification).where(
            TeacherVerification.user_id == user_id,
            TeacherVerification.is_deleted == False
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
