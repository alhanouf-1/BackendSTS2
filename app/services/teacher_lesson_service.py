import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException, status
from app.config.s3 import storage_manager
from app.models.lesson import Lesson
from app.models.video_metadata import VideoMetadata, EncodingStatus
from app.repositories.lesson_repository import LessonRepository
from app.repositories.video_metadata_repository import VideoMetadataRepository
from app.repositories.course_repository import CourseRepository

class TeacherLessonService:
    """Orchestrates lesson creation, S3 media uploads, and queues transcoding tasks."""

    @staticmethod
    async def create_lesson(
        db: AsyncSession,
        teacher_id: uuid.UUID,
        course_id: uuid.UUID,
        title: str,
        notes: str,
        order: int,
        video: UploadFile
    ) -> Lesson:
        # Check course ownership
        course_repo = CourseRepository(db)
        course = await course_repo.get_by_id(course_id)
        if not course or course.teacher_id != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course profile not found or ownership validation failed."
            )

        # Upload raw video file to S3 storage
        video_filename = f"{uuid.uuid4().hex}_{video.filename}"
        video_url = storage_manager.upload_file(
            file_content=video.file,
            filename=video_filename,
            folder="lessons/videos"
        )

        # Create Lesson record
        lesson_repo = LessonRepository(db)
        lesson = Lesson(
            course_id=course_id,
            teacher_id=teacher_id,
            title=title,
            notes=notes,
            order=order,
            video_url=video_url
        )
        await lesson_repo.create(lesson)
        await db.flush()

        # Initialize VideoMetadata PENDING shell
        metadata_repo = VideoMetadataRepository(db)
        metadata = VideoMetadata(
            lesson_id=lesson.id,
            duration_seconds=0,
            resolution="Pending...",
            thumbnail_path=None,
            file_size=0,
            encoding_status=EncodingStatus.PENDING
        )
        await metadata_repo.create(metadata)
        await db.flush()

        # Trigger background Celery transcoding task
        from app.tasks.ai_tasks import process_video
        process_video.delay(video_url, str(metadata.id))

        return lesson
