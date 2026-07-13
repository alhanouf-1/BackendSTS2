import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from sqlalchemy import select, and_, not_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.enrollment import Enrollment
from app.models.course import Course
from app.models.virtual_session import VirtualSession
from app.models.student_notification import StudentNotification
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.virtual_session_repository import VirtualSessionRepository

class StudentDashboardService:
    """Orchestrates compilation of student personal core dashboards."""

    @staticmethod
    async def get_dashboard_summary(db: AsyncSession, student_id: uuid.UUID) -> Dict[str, Any]:
        # 1. Fetch active enrollments
        enroll_repo = EnrollmentRepository(db)
        enrollments = await db.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.course))
            .where(Enrollment.student_id == student_id, Enrollment.is_deleted == False)
        )
        enrollment_list = list(enrollments.scalars().all())

        enrollment_summaries = []
        enrolled_course_ids = []
        enrolled_majors = set()

        for enr in enrollment_list:
            enrolled_course_ids.append(enr.course_id)
            if enr.course:
                enrolled_majors.add(enr.course.major)
                enrollment_summaries.append({
                    "course_id": str(enr.course_id),
                    "title": enr.course.title,
                    "progress_percentage": float(enr.progress_percentage),
                    "is_paid": enr.is_paid
                })

        # 2. Compile dynamic suggestions (same major field, excluding already enrolled courses)
        suggestions = []
        if enrolled_majors:
            suggest_query = (
                select(Course)
                .where(
                    Course.major.in_(list(enrolled_majors)),
                    Course.is_deleted == False
                )
            )
            if enrolled_course_ids:
                suggest_query = suggest_query.where(not_(Course.id.in_(enrolled_course_ids)))
            
            suggest_query = suggest_query.order_by(Course.rating_avg.desc()).limit(5)
            suggest_result = await db.execute(suggest_query)
            for c in suggest_result.scalars().all():
                suggestions.append({
                    "course_id": str(c.id),
                    "title": c.title,
                    "major": c.major,
                    "rating_avg": float(c.rating_avg)
                })

        # 3. Fetch upcoming virtual schedules for next 7 days in enrolled courses
        upcoming_classes = []
        if enrolled_course_ids:
            now = datetime.now(timezone.utc)
            future_limit = now + timedelta(days=7)
            session_repo = VirtualSessionRepository(db)
            sessions = await session_repo.get_upcoming_sessions_by_courses(enrolled_course_ids, now, future_limit)
            for s in sessions:
                upcoming_classes.append({
                    "session_id": str(s.id),
                    "title": s.title,
                    "scheduled_at": s.scheduled_at.isoformat(),
                    "duration_minutes": s.duration_minutes,
                    "meeting_room_id": s.meeting_room_id
                })

        # 4. Fetch recent 10 notifications
        notifications = []
        notif_query = (
            select(StudentNotification)
            .where(
                StudentNotification.student_id == student_id,
                StudentNotification.is_deleted == False
            )
            .order_by(StudentNotification.created_at.desc())
            .limit(10)
        )
        notif_result = await db.execute(notif_query)
        for n in notif_result.scalars().all():
            notifications.append({
                "id": str(n.id),
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read
            })

        return {
            "enrollments": enrollment_summaries,
            "recommendations": suggestions,
            "upcoming_classes": upcoming_classes,
            "notifications": notifications
        }
