import uuid
import enum
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.course import Course
from app.models.user import User, UserRole
from app.repositories.course_repository import CourseRepository

class CourseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

class TeacherCourseService:
    """Orchestrates Course CRUD lifecycles and teacher role validations."""

    @staticmethod
    async def create_course(
        db: AsyncSession,
        teacher: User,
        title: str,
        code: str,
        major: str,
        description: str,
        price: float = 0.00
    ) -> Course:
        # Enforce Verified Teacher Rules
        if price > 0.00 and teacher.role != UserRole.VERIFIED_TEACHER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unverified teachers are restricted to creating free courses only."
            )

        course_repo = CourseRepository(db)
        course = Course(
            teacher_id=teacher.id,
            title=title,
            code=code,
            major=major,
            description=description,
            price=price,
            rating_avg=0.00,
            teacher_profile_visibility=True
        )
        
        # We can dynamically add custom properties like 'status' or keep it mapped
        # In this implementation, let's keep status on the model or as metadata
        setattr(course, "status", CourseStatus.DRAFT.value)

        await course_repo.create(course)
        await db.flush()
        return course

    @staticmethod
    async def update_course_status(
        db: AsyncSession,
        teacher_id: uuid.UUID,
        course_id: uuid.UUID,
        new_status: CourseStatus
    ) -> Course:
        course_repo = CourseRepository(db)
        course = await course_repo.get_by_id(course_id)
        if not course or course.teacher_id != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course profile not found or access denied."
            )

        setattr(course, "status", new_status.value)
        db.add(course)
        await db.flush()
        return course
