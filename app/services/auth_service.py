import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.core.auth.hashing import PasswordHasher
from app.core.auth.jwt import create_access_token, generate_refresh_token_string
from app.core.auth.otp import generate_otp_code, save_otp, verify_and_delete_otp
from app.core.utils.exceptions import (
    AuthInvalidException, 
    EmailExistsException, 
    OTPInvalidException, 
    TokenInvalidException, 
    UserNotFoundException
)
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken
from app.models.teacher_verification import TeacherVerification, VerificationStatus
from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.teacher_verification_repository import TeacherVerificationRepository
from app.services.email_service import EmailService
from app.config.settings import settings

class AuthService:
    """Core Authentication workflows implementation."""

    @staticmethod
    async def register_student(
        db: AsyncSession, 
        redis_client: aioredis.Redis, 
        email: str, 
        password: str, 
        preferences: Optional[dict] = None
    ) -> User:
        """Registers a new student, saves in inactive state, and triggers verification email."""
        user_repo = UserRepository(db)
        
        # Check if email is unique
        existing_user = await user_repo.get_by_email(email)
        if existing_user:
            raise EmailExistsException()

        # Build preference payload merging custom input with defaults
        pref_payload = {"theme": "light", "lang": settings.DEFAULT_LANG}
        if preferences:
            pref_payload.update(preferences)

        student = User(
            email=email,
            password_hash=PasswordHasher.hash(password),
            role=UserRole.STUDENT,
            is_verified=False,
            preferences=pref_payload
        )
        
        await user_repo.create(student)
        
        # Core OTP setup and dispatch
        otp_code = generate_otp_code()
        await save_otp(redis_client, email, otp_code, "registration")
        EmailService.send_registration_otp(email, otp_code)
        
        return student

    @staticmethod
    async def register_teacher(
        db: AsyncSession,
        email: str,
        password: str,
        document_url: str,
        preferences: Optional[dict] = None
    ) -> Tuple[User, TeacherVerification]:
        """Registers a new teacher, uploads application document and initializes parsing state."""
        user_repo = UserRepository(db)
        verify_repo = TeacherVerificationRepository(db)

        # Check if email is unique
        existing_user = await user_repo.get_by_email(email)
        if existing_user:
            raise EmailExistsException()

        # Build preference payload merging custom input with defaults
        pref_payload = {"theme": "light", "lang": settings.DEFAULT_LANG}
        if preferences:
            pref_payload.update(preferences)

        teacher = User(
            email=email,
            password_hash=PasswordHasher.hash(password),
            role=UserRole.TEACHER,
            is_verified=False,  # Verified only after OTP + AI doc evaluation completes
            preferences=pref_payload
        )
        
        await user_repo.create(teacher)

        # Create Verification transaction tracking
        verification = TeacherVerification(
            user_id=teacher.id,
            document_url=document_url,
            status=VerificationStatus.PENDING
        )
        await verify_repo.create(verification)
        
        return teacher, verification

    @staticmethod
    async def verify_otp(
        db: AsyncSession, 
        redis_client: aioredis.Redis, 
        email: str, 
        otp_code: str, 
        purpose: str
    ) -> User:
        """
        Validates OTP code from Redis cache.
        If valid, activates registration and updates verification states.
        """
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(email)
        if not user:
            raise UserNotFoundException()

        # Atomic verify-and-delete from cache
        is_valid = await verify_and_delete_otp(redis_client, email, otp_code, purpose)
        if not is_valid:
            raise OTPInvalidException("The verification code is invalid or has expired.")

        # Activate user on registration success
        if purpose == "registration":
            user.is_verified = True
            db.add(user)

        return user

    @staticmethod
    async def login(
        db: AsyncSession, 
        email: str, 
        password: str
    ) -> Dict[str, Any]:
        """Authenticates user credentials and generates access/refresh tokens."""
        user_repo = UserRepository(db)
        token_repo = RefreshTokenRepository(db)

        user = await user_repo.get_by_email(email)
        if not user:
            raise AuthInvalidException()

        if not PasswordHasher.verify(password, user.password_hash):
            raise AuthInvalidException()

        if not user.is_verified:
            raise AuthInvalidException("Please verify your account email using OTP before logging in.")

        # Generate tokens
        access_token = create_access_token(subject=str(user.id), role=user.role.value)
        refresh_token_str = generate_refresh_token_string()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Save refresh token in DB ledger
        db_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=expires_at,
            is_revoked=False
        )
        await token_repo.create(db_token)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
            "user": user
        }

    @staticmethod
    async def refresh_tokens(
        db: AsyncSession, 
        refresh_token_str: str
    ) -> Dict[str, Any]:
        """Rotates tokens, validating expiration, and checking for token reuse compromise."""
        token_repo = RefreshTokenRepository(db)

        db_token = await token_repo.get_by_token(refresh_token_str)
        if not db_token:
            raise TokenInvalidException("Provided refresh token is invalid or expired.")

        # Replay Attack Detection: If a token is already marked revoked,
        # it means the client (or a malicious actor) is attempting to reuse an old session.
        if db_token.is_revoked:
            await token_repo.revoke_all_user_tokens(db_token.user_id)
            await db.commit()
            raise TokenInvalidException("Refresh token was previously used. All user sessions have been terminated.")

        # Expiry Check
        if db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise TokenInvalidException("Refresh token has expired.")

        # Load user
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(db_token.user_id)
        if not user or user.is_deleted:
            raise TokenInvalidException("User account is inactive or deleted.")

        # Rotate tokens: mark old token as revoked
        db_token.is_revoked = True
        db.add(db_token)

        # Create new credentials pair
        new_access_token = create_access_token(subject=str(user.id), role=user.role.value)
        new_refresh_token_str = generate_refresh_token_string()
        new_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_db_token = RefreshToken(
            user_id=user.id,
            token=new_refresh_token_str,
            expires_at=new_expires_at,
            is_revoked=False,
            rotated_from_id=db_token.id
        )
        await token_repo.create(new_db_token)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token_str,
            "token_type": "bearer"
        }

    @staticmethod
    async def logout(
        db: AsyncSession, 
        refresh_token_str: str
    ) -> None:
        """Revokes token on account logout."""
        token_repo = RefreshTokenRepository(db)
        db_token = await token_repo.get_by_token(refresh_token_str)
        if db_token:
            db_token.is_revoked = True
            db.add(db_token)

    @staticmethod
    async def forgot_password(
        db: AsyncSession, 
        redis_client: aioredis.Redis, 
        email: str
    ) -> None:
        """Generates recovery token, registers in cache, and mails recovering user."""
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(email)
        if not user:
            raise UserNotFoundException()

        otp_code = generate_otp_code()
        await save_otp(redis_client, email, otp_code, "password_reset")
        EmailService.send_password_reset_otp(email, otp_code)

    @staticmethod
    async def reset_password(
        db: AsyncSession, 
        redis_client: aioredis.Redis, 
        email: str, 
        otp_code: str, 
        new_password: str
    ) -> None:
        """Authenticates password-reset OTP token and mutates target credentials."""
        user_repo = UserRepository(db)
        token_repo = RefreshTokenRepository(db)

        user = await user_repo.get_by_email(email)
        if not user:
            raise UserNotFoundException()

        is_valid = await verify_and_delete_otp(redis_client, email, otp_code, "password_reset")
        if not is_valid:
            raise OTPInvalidException("The reset verification code is invalid or has expired.")

        # Update User Password and drop all current active user sessions for security purposes
        user.password_hash = PasswordHasher.hash(new_password)
        db.add(user)
        
        await token_repo.revoke_all_user_tokens(user.id)

    @staticmethod
    async def delete_account(
        db: AsyncSession, 
        redis_client: aioredis.Redis, 
        current_user: User, 
        otp_code: str
    ) -> None:
        """Validates erasure consent OTP and soft deletes User records."""
        user_repo = UserRepository(db)
        token_repo = RefreshTokenRepository(db)
        verify_repo = TeacherVerificationRepository(db)

        is_valid = await verify_and_delete_otp(redis_client, current_user.email, otp_code, "account_deletion")
        if not is_valid:
            raise OTPInvalidException("The deletion confirmation code is invalid or has expired.")

        # Terminate all active sessions
        await token_repo.revoke_all_user_tokens(current_user.id)
        
        # Soft delete related verification record if teacher
        verification = await verify_repo.get_by_user_id(current_user.id)
        if verification:
            await verify_repo.delete(verification.id, deleter_id=current_user.id)

        # Soft delete user record itself
        await user_repo.delete(current_user.id, deleter_id=current_user.id)
