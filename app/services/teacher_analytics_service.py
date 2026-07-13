import uuid
import json
from typing import Dict, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.enrollment import Enrollment
from app.models.student_video_progress import StudentVideoProgress
from app.models.transaction import Transaction, TransactionType
from app.models.rating import Rating

class TeacherAnalyticsService:
    """Orchestrates dynamic SQL metric evaluations and manages 15-minute caching rules."""

    @staticmethod
    async def get_analytics(
        db: AsyncSession,
        redis_client: aioredis.Redis,
        teacher_id: uuid.UUID,
        course_id: Optional[uuid.UUID] = None,
        period: str = "daily"
    ) -> Dict[str, Any]:
        
        # 1. Inspect Redis Cache first
        cache_key = f"analytics:teacher:{teacher_id}:course:{course_id or 'all'}:period:{period}"
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data.decode("utf-8"))

        # 2. Database Analytics calculations
        # total_views (Total video progress events recorded)
        views_query = (
            select(func.count(StudentVideoProgress.id))
            .join(Lesson, StudentVideoProgress.lesson_id == Lesson.id)
            .where(Lesson.teacher_id == teacher_id, StudentVideoProgress.is_deleted == False)
        )
        if course_id:
            views_query = views_query.where(Lesson.course_id == course_id)
        views_result = await db.execute(views_query)
        total_views = views_result.scalar() or 0

        # total_students (Distinct active student enrollments)
        students_query = (
            select(func.count(func.distinct(Enrollment.student_id)))
            .join(Course, Enrollment.course_id == Course.id)
            .where(Course.teacher_id == teacher_id, Enrollment.is_deleted == False)
        )
        if course_id:
            students_query = students_query.where(Enrollment.course_id == course_id)
        students_result = await db.execute(students_query)
        total_students = students_result.scalar() or 0

        # total_earnings (Sum of deposit transactions)
        earnings_query = select(func.sum(Transaction.amount)).where(
            Transaction.teacher_id == teacher_id,
            Transaction.type == TransactionType.DEPOSIT,
            Transaction.is_deleted == False
        )
        if course_id:
            earnings_query = earnings_query.where(Transaction.course_id == course_id)
        earnings_result = await db.execute(earnings_query)
        total_earnings = float(earnings_result.scalar() or 0.00)

        # avg_rating (Average course score)
        rating_query = (
            select(func.avg(Rating.rating_value))
            .join(Course, Rating.course_id == Course.id)
            .where(Course.teacher_id == teacher_id, Rating.is_deleted == False)
        )
        if course_id:
            rating_query = rating_query.where(Rating.course_id == course_id)
        rating_result = await db.execute(rating_query)
        val = rating_result.scalar()
        avg_rating = float(val) if val is not None else 0.00

        # completion_rate (Average video completion percentage)
        completion_query = (
            select(func.avg(StudentVideoProgress.completion_percentage))
            .join(Lesson, StudentVideoProgress.lesson_id == Lesson.id)
            .where(Lesson.teacher_id == teacher_id, StudentVideoProgress.is_deleted == False)
        )
        if course_id:
            completion_query = completion_query.where(Lesson.course_id == course_id)
        completion_result = await db.execute(completion_query)
        comp_val = completion_result.scalar()
        completion_rate = float(comp_val) if comp_val is not None else 0.00

        # 3. Assemble Response
        analytics_data = {
            "total_views": total_views,
            "total_students": total_students,
            "total_earnings": total_earnings,
            "avg_rating": avg_rating,
            "completion_rate": completion_rate
        }

        # 4. Cache compiled response in Redis for 15 minutes (900 seconds)
        await redis_client.set(cache_key, json.dumps(analytics_data), ex=900)

        return analytics_data
