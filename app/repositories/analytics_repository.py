import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.teacher_analytics import TeacherAnalytics, AnalyticsPeriod
from app.repositories.base import BaseRepository

class AnalyticsRepository(BaseRepository[TeacherAnalytics]):
    """Repository managing pre-calculated TeacherAnalytics records."""
    def __init__(self, db: AsyncSession):
        super().__init__(TeacherAnalytics, db)

    async def get_analytics(
        self,
        teacher_id: uuid.UUID,
        course_id: Optional[uuid.UUID] = None,
        period: AnalyticsPeriod = AnalyticsPeriod.DAILY,
        limit: int = 30
    ) -> List[TeacherAnalytics]:
        """Fetches pre-calculated analytics metrics based on periods and filters."""
        query = select(TeacherAnalytics).where(
            TeacherAnalytics.teacher_id == teacher_id,
            TeacherAnalytics.period == period,
            TeacherAnalytics.is_deleted == False
        )
        if course_id:
            query = query.where(TeacherAnalytics.course_id == course_id)
            
        query = query.order_by(TeacherAnalytics.recorded_date.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
