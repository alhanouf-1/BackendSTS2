import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import redis.asyncio as aioredis
from app.repositories.user_repository import UserRepository
from app.core.auth.hashing import PasswordHasher
from app.core.auth.otp import generate_otp_code
from app.tasks.email_tasks import send_otp_email

class StudentSettingsService:
    """Orchestrates security credentials mutations, profile updates, and preferences updates."""

    @staticmethod
    async def change_password_request(
        db: AsyncSession,
        redis_client: aioredis.Redis,
        student_id: uuid.UUID,
        current_password: str
    ) -> None:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(student_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        # Verify current password
        if not PasswordHasher.verify(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password."
            )

        # Generate 5-minute OTP code
        otp_code = generate_otp_code()
        redis_key = f"otp:change_password:{student_id}"
        
        # Save OTP in Redis (valid for 300 seconds)
        await redis_client.set(redis_key, otp_code, ex=300)

        # Dispatch OTP via Celery task
        send_otp_email.delay(user.email, otp_code, "password_change")

    @staticmethod
    async def confirm_password_change(
        db: AsyncSession,
        redis_client: aioredis.Redis,
        student_id: uuid.UUID,
        otp_code: str,
        new_password: str,
        confirm_password: str
    ) -> None:
        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New passwords do not match."
            )

        # Check OTP in Redis
        redis_key = f"otp:change_password:{student_id}"
        cached_otp = await redis_client.get(redis_key)
        
        if not cached_otp or cached_otp.decode("utf-8") != otp_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification OTP."
            )

        # Invalidate OTP key
        await redis_client.delete(redis_key)

        # Update password hash in database
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(student_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        user.password_hash = PasswordHasher.hash(new_password)
        db.add(user)
        await db.flush()

    @staticmethod
    async def update_notification_preferences(
        db: AsyncSession,
        student_id: uuid.UUID,
        preferences: Dict[str, bool]
    ) -> Dict[str, Any]:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(student_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        # Expose JSON preferences structures maintaining configurations
        current_prefs = user.preferences or {}
        
        # Enforce notification settings updates
        notif_prefs = {
            "email_notifications": preferences.get("email_notifications", True),
            "class_reminders": preferences.get("class_reminders", True),
            "course_updates": preferences.get("course_updates", True),
            "marketing_notifications": preferences.get("marketing_notifications", False)
        }
        current_prefs.update(notif_prefs)
        user.preferences = current_prefs
        db.add(user)
        await db.flush()
        
        return notif_prefs
