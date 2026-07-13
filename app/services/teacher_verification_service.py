import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException, status
from app.config.s3 import storage_manager
from app.models.teacher_verification import TeacherVerification, VerificationStatus
from app.repositories.teacher_verification_repository import TeacherVerificationRepository
from app.tasks.ai_tasks import process_verification_letter

class TeacherVerificationService:
    """Orchestrates failed verification letter re-uploads and re-triggers LangChain parsers."""

    @staticmethod
    async def re_upload_recommendation(
        db: AsyncSession,
        user_id: uuid.UUID,
        pdf: UploadFile
    ) -> TeacherVerification:
        # Save pdf file to S3
        pdf_filename = f"reupload_verification_{user_id.hex}_{pdf.filename}"
        pdf_path = storage_manager.upload_file(
            file_content=pdf.file,
            filename=pdf_filename,
            folder="verifications"
        )

        verify_repo = TeacherVerificationRepository(db)
        verification = await verify_repo.get_by_user_id(user_id)

        if verification:
            # Overwrite prior path and reset fields
            verification.document_url = pdf_path
            verification.status = VerificationStatus.PENDING
            verification.verification_score = 0.00
            verification.criteria_met = {}
            db.add(verification)
        else:
            verification = TeacherVerification(
                user_id=user_id,
                document_url=pdf_path,
                status=VerificationStatus.PENDING,
                verification_score=0.00,
                criteria_met={}
            )
            await verify_repo.create(verification)

        await db.flush()

        # Re-trigger LangChain 5-Factor analysis workflow
        process_verification_letter.delay(str(user_id), pdf_path)

        return verification
