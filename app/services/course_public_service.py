import uuid
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.course_repository import CourseRepository

class CoursePublicService:
    """Orchestrates course advanced searches, filters, details, and privacy redaction."""

    @staticmethod
    async def search_courses(
        db: AsyncSession,
        q: Optional[str] = None,
        university: Optional[str] = None,
        code: Optional[str] = None,
        major: Optional[str] = None,
        rating_min: Optional[float] = None,
        teacher_name: Optional[str] = None,
        price_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Executes advanced filters, applying teacher anonymity rules dynamically on matches.
        """
        repo = CourseRepository(db)
        courses, total = await repo.search_courses(
            q=q,
            university=university,
            code=code,
            major=major,
            rating_min=rating_min,
            teacher_name=teacher_name,
            price_type=price_type,
            skip=skip,
            limit=limit
        )

        formatted_courses = []
        for course in courses:
            # Privacy rule validation
            t_name = "Anonymous Instructor"
            if course.teacher_profile_visibility and course.teacher:
                if course.teacher.preferences and "full_name" in course.teacher.preferences:
                    t_name = course.teacher.preferences["full_name"]
                else:
                    t_name = course.teacher.email.split("@")[0].title()

            formatted_courses.append({
                "course_id": str(course.id),
                "title": course.title,
                "code": course.code,
                "major": course.major,
                "description": course.description,
                "price": float(course.price),
                "rating_avg": float(course.rating_avg),
                "teacher_name": t_name
            })

        return formatted_courses, total

    @staticmethod
    async def get_course_details(db: AsyncSession, course_id_str: str) -> Optional[Dict[str, Any]]:
        """
        Resolves a deep course layout configuration.
        Aggregates child metadata counts.
        """
        try:
            course_uuid = uuid.UUID(course_id_str)
        except ValueError:
            return None

        repo = CourseRepository(db)
        course = await repo.get_course_details(course_uuid)
        if not course:
            return None

        # Privacy rule validation
        t_name = "Anonymous Instructor"
        if course.teacher_profile_visibility and course.teacher:
            if course.teacher.preferences and "full_name" in course.teacher.preferences:
                t_name = course.teacher.preferences["full_name"]
            else:
                t_name = course.teacher.email.split("@")[0].title()

        # Compiles total child indices
        lessons_count = len(course.lessons)
        summaries_count = len(course.summaries)
        virtual_classes_count = len(course.virtual_classes)

        # Fallback preview url resolution
        preview_video_url = ""
        if course.lessons:
            # Use order index first or first element as default preview URL
            sorted_lessons = sorted(course.lessons, key=lambda x: x.order_index)
            preview_video_url = sorted_lessons[0].video_url

        return {
            "course_id": str(course.id),
            "title": course.title,
            "code": course.code,
            "teacher_name": t_name,
            "description": course.description,
            "preview_video_url": preview_video_url,
            "rating_avg": float(course.rating_avg),
            "price": float(course.price),
            "lessons_count": lessons_count,
            "summaries_count": summaries_count,
            "virtual_classes_count": virtual_classes_count
        }
