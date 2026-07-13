import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.verification_audit import VerificationAudit
from app.config.logging import logger

class VerificationService:
    """Orchestrates AI document analysis pipeline task routing and audit retrieval."""

    @staticmethod
    def trigger_verification(user_id: str, pdf_path: str) -> None:
        """Dispatches the background verification evaluation pipeline Celery task."""
        from app.tasks.ai_tasks import process_verification_letter
        process_verification_letter.delay(user_id, pdf_path)
        logger.info("Celery task process_verification_letter dispatched.", user_id=user_id, pdf_path=pdf_path)

    @staticmethod
    async def get_teacher_audits(db: AsyncSession, teacher_id: uuid.UUID) -> List[VerificationAudit]:
        """Retrieves historical audit entries associated with a teacher."""
        query = (
            select(VerificationAudit)
            .where(VerificationAudit.teacher_id == teacher_id)
            .order_by(VerificationAudit.created_at.desc())
        )
        result = await db.execute(query)
        return list(result.scalars().all())
