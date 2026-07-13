import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException, status
from app.config.s3 import storage_manager
from app.config.logging import logger
from app.repositories.teacher_verification_repository import TeacherVerificationRepository
from app.repositories.user_repository import UserRepository
from app.models.teacher_verification import TeacherVerification, VerificationStatus
from app.core.utils.exceptions import UserNotFoundException, STSException
from app.services.verification_service import VerificationService

class TeacherRegistrationService:
    """Orchestrates teacher verification document re-upload workflows and active resets."""

    @staticmethod
    async def reupload_verification_letter(
        db: AsyncSession,
        teacher_id: uuid.UUID,
        document: UploadFile
    ) -> dict:
        """
        Replaces a teacher's verification document, wipes the old file,
        resets status to PENDING, and triggers a new AI analysis task.
        """
        user_repo = UserRepository(db)
        verify_repo = TeacherVerificationRepository(db)

        user = await user_repo.get_by_id(teacher_id)
        if not user:
            raise UserNotFoundException("Teacher account not found.")

        # Ensure user role is a teacher type
        if user.role.value not in ["TEACHER", "VERIFIED_TEACHER"]:
            raise STSException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_ROLE",
                message="User is not registered under teacher role guidelines."
            )

        # Retrieve current verification entry
        verification = await verify_repo.get_by_user_id(teacher_id)

        # Upload new recommendation PDF
        filename = f"{uuid.uuid4().hex}_{document.filename}"
        new_url = storage_manager.upload_file(
            file_content=document.file,
            filename=filename,
            folder="recommendation_letters"
        )

        if verification:
            # Wipe older document to conserve space
            storage_manager.delete_file(verification.document_url)
            # Reset verification details
            verification.document_url = new_url
            verification.status = VerificationStatus.PENDING
            db.add(verification)
            logger.info("Teacher document reset and re-uploaded.", user_id=teacher_id)
        else:
            # Create a new verification index if somehow missing
            verification = TeacherVerification(
                user_id=teacher_id,
                document_url=new_url,
                status=VerificationStatus.PENDING
            )
            await verify_repo.create(verification)
            logger.info("New teacher verification record created.", user_id=teacher_id)

        await db.flush()

        # Dispatches async AI verification pipeline
        VerificationService.trigger_verification(str(user.id), verification.document_url)

        return {
            "user_id": str(teacher_id),
            "role": user.role.value,
            "verification_status": verification.status.value
        }
