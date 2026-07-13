import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException, status
from app.config.s3 import storage_manager
from app.models.summary import Summary
from app.repositories.course_repository import CourseRepository

class TeacherSummaryService:
    """Orchestrates creation and uploads of course summary handout notes."""

    @staticmethod
    async def create_summary(
        db: AsyncSession,
        teacher_id: uuid.UUID,
        course_id: uuid.UUID,
        title: str,
        pdf: UploadFile
    ) -> Summary:
        # Check course ownership
        course_repo = CourseRepository(db)
        course = await course_repo.get_by_id(course_id)
        if not course or course.teacher_id != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course profile not found or ownership validation failed."
            )

        # Upload handout PDF to storage
        pdf_filename = f"{uuid.uuid4().hex}_{pdf.filename}"
        pdf_url = storage_manager.upload_file(
            file_content=pdf.file,
            filename=pdf_filename,
            folder="lessons/handouts"
        )

        summary = Summary(
            course_id=course_id,
            teacher_id=teacher_id,
            title=title,
            pdf_path=pdf_url,
            file_url=pdf_url,
            description=f"Study handouts for course: {course.title}"
        )
        db.add(summary)
        await db.flush()
        return summary
