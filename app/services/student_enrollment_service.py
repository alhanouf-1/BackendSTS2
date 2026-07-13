import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.enrollment import Enrollment
from app.repositories.enrollment_repository import EnrollmentRepository
from app.repositories.course_repository import CourseRepository
from app.core.utils.exceptions import STSException

class StudentEnrollmentService:
    """Orchestrates mock course purchase transactions and unlocks lessons access."""

    @staticmethod
    async def enroll_in_course(db: AsyncSession, student_id: uuid.UUID, course_id: uuid.UUID) -> Enrollment:
        # Check if course exists and is active
        course_repo = CourseRepository(db)
        course = await course_repo.get_by_id(course_id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target course not found or soft-deleted."
            )

        # Check for existing enrollment
        enroll_repo = EnrollmentRepository(db)
        existing = await enroll_repo.get_by_student_and_course(student_id, course_id)
        if existing:
            if existing.is_paid:
                return existing
            else:
                # Mark existing unpaid record as paid
                existing.is_paid = True
                db.add(existing)
                await db.flush()
                return existing

        # Create paid enrollment record
        enrollment = Enrollment(
            student_id=student_id,
            course_id=course_id,
            progress_percentage=0.00,
            is_paid=True
        )
        await enroll_repo.create(enrollment)
        await db.flush()
        return enrollment
