import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.student_video_progress import StudentVideoProgress
from app.models.progress_history import ProgressHistory
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.repositories.video_progress_repository import VideoProgressRepository
from app.repositories.enrollment_repository import EnrollmentRepository

class StudentProgressService:
    """Orchestrates video telemetry processing and progress logging."""

    @staticmethod
    async def update_video_progress(
        db: AsyncSession,
        student_id: uuid.UUID,
        lesson_id: uuid.UUID,
        watched_seconds: int,
        total_seconds: int,
        last_position: int
    ) -> StudentVideoProgress:
        # Calculate completion percentage
        completion = 0.00
        if total_seconds > 0:
            completion = (watched_seconds / total_seconds) * 100.00
            completion = min(max(completion, 0.00), 100.00)

        # Retrieve lesson details to identify parent course
        lesson_result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
        lesson = lesson_result.scalar_one_or_none()
        if not lesson:
            raise ValueError("Lesson not found.")

        course_id = lesson.course_id

        # Check existing progress
        progress_repo = VideoProgressRepository(db)
        existing = await progress_repo.get_by_student_and_lesson(student_id, lesson_id)
        
        old_val = 0.00
        if existing:
            old_val = float(existing.completion_percentage)
            new_val = max(old_val, completion) # Do not decrease progress

            # Only update if there is improvement
            if new_val > old_val:
                existing.watched_seconds = max(existing.watched_seconds, watched_seconds)
                existing.completion_percentage = new_val
                existing.last_position = last_position
                db.add(existing)
            else:
                existing.last_position = last_position
                db.add(existing)
                new_val = old_val
            progress_record = existing
        else:
            new_val = completion
            progress_record = StudentVideoProgress(
                student_id=student_id,
                lesson_id=lesson_id,
                watched_seconds=watched_seconds,
                total_seconds=total_seconds,
                completion_percentage=new_val,
                last_position=last_position
            )
            await progress_repo.create(progress_record)

        # Trigger audit logging if progress improved
        if new_val > old_val:
            history = ProgressHistory(
                student_id=student_id,
                course_id=course_id,
                old_progress=old_val,
                new_progress=new_val
            )
            db.add(history)
            
            # Flush changes to capture progress record updates
            await db.flush()

            # Recalculate parent enrollment progress percentage
            await StudentProgressService.recalculate_course_progress(db, student_id, course_id)

        return progress_record

    @staticmethod
    async def recalculate_course_progress(db: AsyncSession, student_id: uuid.UUID, course_id: uuid.UUID) -> float:
        # Get total number of lessons in the course
        lessons_query = select(func.count(Lesson.id)).where(Lesson.course_id == course_id, Lesson.is_deleted == False)
        lessons_result = await db.execute(lessons_query)
        total_lessons = lessons_result.scalar() or 0
        if total_lessons == 0:
            return 0.00

        # Sum completion percentages for student's progresses in this course
        progress_query = (
            select(func.sum(StudentVideoProgress.completion_percentage))
            .join(Lesson, StudentVideoProgress.lesson_id == Lesson.id)
            .where(
                StudentVideoProgress.student_id == student_id,
                Lesson.course_id == course_id,
                StudentVideoProgress.is_deleted == False
            )
        )
        progress_result = await db.execute(progress_query)
        total_completed_percentage = progress_result.scalar() or 0.00

        # Enrollment progress = total completion percentages / total lessons
        progress_percentage = float(total_completed_percentage) / total_lessons
        progress_percentage = min(max(progress_percentage, 0.00), 100.00)

        # Update enrollment record
        enroll_repo = EnrollmentRepository(db)
        enrollment = await enroll_repo.get_by_student_and_course(student_id, course_id)
        if enrollment:
            enrollment.progress_percentage = progress_percentage
            db.add(enrollment)
            await db.flush()

        return progress_percentage
