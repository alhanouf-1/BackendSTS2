import uuid
import asyncio
from celery.utils.log import get_task_logger
from app.config.celery import celery_app
from app.config.database import async_session_maker
from app.services.student_progress_service import StudentProgressService

logger = get_task_logger(__name__)

async def _recalculate_progress_async(student_id: str, course_id: str) -> None:
    """Async engine loading sessions and recalculating enrollments."""
    student_uuid = uuid.UUID(student_id)
    course_uuid = uuid.UUID(course_id)
    async with async_session_maker() as db:
        new_progress = await StudentProgressService.recalculate_course_progress(db, student_uuid, course_uuid)
        await db.commit()
        logger.info(
            f"Successfully recalculated course progress via background Celery task.",
            student_id=student_id,
            course_id=course_id,
            new_progress=new_progress
        )

@celery_app.task(
    name="app.tasks.progress_tasks.recalculate_student_course_progress",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    default_retry_delay=60
)
def recalculate_student_course_progress(self, student_id: str, course_id: str) -> None:
    """Celery background worker task for asynchronous course progress recalculation."""
    logger.info(f"Triggering asynchronous course progress recalculation for student={student_id}, course={course_id}")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_recalculate_progress_async(student_id, course_id))
    except Exception as exc:
        logger.error(f"Course progress recalculation task failed. Retrying. Error: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)
