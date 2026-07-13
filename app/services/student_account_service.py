import uuid
from datetime import datetime, timedelta, timezone
from typing import List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import redis.asyncio as aioredis
from app.models.user import User
from app.models.enrollment import Enrollment
from app.models.progress_history import ProgressHistory
from app.models.student_video_progress import StudentVideoProgress
from app.models.student_summary_progress import StudentSummaryProgress
from app.models.bookmarks import Bookmark
from app.models.help_ticket import HelpTicket
from app.models.rating import Rating
from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.core.auth.otp import verify_and_delete_otp
from app.config.logging import logger

class StudentAccountService:
    """Manages the lifecycle of user account deletion and 30-day quarantine purges."""

    @staticmethod
    async def soft_delete_student_account(
        db: AsyncSession,
        redis_client: aioredis.Redis,
        student_id: uuid.UUID,
        otp_code: str
    ) -> None:
        user_repo = UserRepository(db)
        token_repo = RefreshTokenRepository(db)

        user = await user_repo.get_by_id(student_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

        # Validate OTP
        is_valid = await verify_and_delete_otp(redis_client, user.email, otp_code, "account_deletion")
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The deletion confirmation code is invalid or has expired."
            )

        # Terminate active JWT session tokens
        await token_repo.revoke_all_user_tokens(student_id)

        # Flag-toggle soft delete
        user.is_deleted = True
        user.deleted_at = datetime.now(timezone.utc)
        db.add(user)
        await db.commit()
        logger.info("Student account soft deleted and placed in quarantine.", user_id=student_id)

    @staticmethod
    async def purge_quarantined_accounts(db: AsyncSession) -> int:
        """Looks up accounts soft-deleted >= 30 days ago and permanently purges them and their dependencies."""
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Select all users soft-deleted 30 or more days ago
        query = select(User).where(
            User.is_deleted == True,
            User.deleted_at <= thirty_days_ago
        )
        result = await db.execute(query)
        users_to_purge = list(result.scalars().all())
        
        purged_count = 0
        for user in users_to_purge:
            logger.info("Purging user account permanently after quarantine.", user_id=user.id)
            
            # Cascade deletions on user-related entities
            await db.execute(select(Enrollment).where(Enrollment.student_id == user.id))
            # Delete references
            # Standard cascades will handle database-level FKey sweeps on commit,
            # but we explicitly delete the user to trigger SQLAlchemy session events
            await db.delete(user)
            purged_count += 1

        if purged_count > 0:
            await db.commit()
            logger.info(f"Account purge job completed. Purged {purged_count} accounts.")
            
        return purged_count
