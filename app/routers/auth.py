import json
import uuid
from typing import Optional
from fastapi import (
    APIRouter, 
    Depends, 
    UploadFile, 
    File, 
    Form, 
    HTTPException, 
    status
)
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.config.database import get_db
from app.config.redis import get_redis
from app.config.s3 import storage_manager
from app.core.auth.dependencies import (
    RateLimiter, 
    get_current_active_user
)
from app.core.utils.responses import BaseResponse, make_response
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from app.services.teacher_registration_service import TeacherRegistrationService
# Delay imports to avoid circular logic
from app.tasks.ai_tasks import process_verification_letter

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Instantiating custom rate limits
login_limiter = RateLimiter(requests=5, window_seconds=60)
otp_limiter = RateLimiter(requests=3, window_seconds=60)
forgot_pw_limiter = RateLimiter(requests=3, window_seconds=60)

# Request schemas
class StudentRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    preferences: Optional[dict] = None

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str
    purpose: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str

class DeleteAccountRequest(BaseModel):
    otp_code: str


@router.post("/register/student", response_model=BaseResponse[dict], status_code=status.HTTP_201_CREATED)
async def register_student(
    payload: StudentRegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Enrolls a student, writes record, and sends OTP email code."""
    prefs = payload.preferences or {}
    prefs["full_name"] = payload.full_name
    student = await AuthService.register_student(
        db=db,
        redis_client=redis_client,
        email=payload.email,
        password=payload.password,
        preferences=prefs
    )
    
    return make_response(
        data={
            "user_id": str(student.id),
            "email": student.email,
            "role": student.role.value
        },
        success=True,
        code="REGISTRATION_SUCCESS",
        message="Student registration initiated. Please verify using OTP sent to your email."
    )


def validate_pdf_file(document: UploadFile) -> None:
    """Enforces size constraint (<=5MB) and validates PDF magic bytes (%PDF)."""
    if not document.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mandatory upload document must be a PDF."
        )

    # Validate size limits (5MB) and signature magic bytes
    max_bytes = 5 * 1024 * 1024
    try:
        header = document.file.read(4)
        document.file.seek(0, 2)
        file_size = document.file.tell()
        document.file.seek(0)  # Reset stream position

        if file_size > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file size exceeds the strict 5MB limit."
            )

        if header != b"%PDF":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Uploaded file does not contain a valid PDF signature."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to read file signature. Error: {str(e)}"
        )

@router.post("/register/teacher", response_model=BaseResponse[dict], status_code=status.HTTP_201_CREATED)
async def register_teacher(
    email: EmailStr = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    preferences: Optional[str] = Form(None),
    document: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Multipart upload form for teacher requests, uploading document PDF for AI queue verification."""
    # Ensure PDF upload constraint is met securely
    validate_pdf_file(document)

    # Parse preferences if provided
    pref_dict = {}
    if preferences:
        try:
            pref_dict = json.loads(preferences)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Preferences must be a valid JSON string."
            )
    pref_dict["full_name"] = full_name

    # Write document to configured storage provider
    document_url = storage_manager.upload_file(
        file_content=document.file,
        filename=f"{uuid.uuid4().hex}_{document.filename}",
        folder="recommendation_letters"
    )

    teacher, verification = await AuthService.register_teacher(
        db=db,
        email=email,
        password=password,
        document_url=document_url,
        preferences=pref_dict
    )

    # Trigger async AI verification task in Celery worker
    process_verification_letter.delay(str(teacher.id), document_url)

    return make_response(
        data={
            "user_id": str(teacher.id),
            "email": teacher.email,
            "role": teacher.role.value,
            "verification_status": verification.status.value
        },
        success=True,
        code="REGISTRATION_SUCCESS",
        message="Teacher registration initiated. Automated AI verification pipeline analysis in progress."
    )


@router.post("/verify-otp", response_model=BaseResponse[dict], dependencies=[Depends(otp_limiter)])
async def verify_otp(
    payload: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Performs single-use verification verification against Redis OTP tokens."""
    user = await AuthService.verify_otp(
        db=db,
        redis_client=redis_client,
        email=payload.email,
        otp_code=payload.otp_code,
        purpose=payload.purpose
    )
    
    return make_response(
        data={
            "user_id": str(user.id),
            "is_verified": user.is_verified
        },
        success=True,
        code="VERIFICATION_SUCCESS",
        message="Verification completed successfully."
    )


@router.post("/login", response_model=BaseResponse[dict], dependencies=[Depends(login_limiter)])
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Standard credential login issuing access/refresh tokens."""
    login_data = await AuthService.login(
        db=db,
        email=payload.email,
        password=payload.password
    )
    
    user = login_data["user"]
    return make_response(
        data={
            "access_token": login_data["access_token"],
            "refresh_token": login_data["refresh_token"],
            "token_type": login_data["token_type"],
            "user": {
                "user_id": str(user.id),
                "email": user.email,
                "role": user.role.value,
                "preferences": user.preferences
            }
        },
        success=True,
        code="LOGIN_SUCCESS",
        message="Login verification complete."
    )


@router.post("/refresh", response_model=BaseResponse[dict])
async def refresh_token(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """Enforces token rotation and invalidation checks on refresh actions."""
    refresh_data = await AuthService.refresh_tokens(
        db=db,
        refresh_token_str=payload.refresh_token
    )
    
    return make_response(
        data={
            "access_token": refresh_data["access_token"],
            "refresh_token": refresh_data["refresh_token"],
            "token_type": refresh_data["token_type"]
        },
        success=True,
        code="TOKEN_REFRESHED",
        message="Authorization credentials rotated."
    )


@router.post("/logout", response_model=BaseResponse[dict])
async def logout(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db)
):
    """Revokes refresh tokens on user logouts."""
    await AuthService.logout(db=db, refresh_token_str=payload.refresh_token)
    return make_response(
        data={},
        success=True,
        code="LOGOUT_SUCCESS",
        message="Logout successful."
    )


@router.post("/forgot-password", response_model=BaseResponse[dict], dependencies=[Depends(forgot_pw_limiter)])
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Issues verification ticket to restore access."""
    await AuthService.forgot_password(
        db=db,
        redis_client=redis_client,
        email=payload.email
    )
    return make_response(
        data={},
        success=True,
        code="OTP_DISPATCHED",
        message="OTP sent to email. Please verify to reset your password."
    )


@router.post("/reset-password", response_model=BaseResponse[dict])
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Validates verification OTP and overrides password hashes."""
    await AuthService.reset_password(
        db=db,
        redis_client=redis_client,
        email=payload.email,
        otp_code=payload.otp_code,
        new_password=payload.new_password
    )
    return make_response(
        data={},
        success=True,
        code="PASSWORD_RESET_SUCCESS",
        message="Password has been successfully updated."
    )


@router.delete("/delete-account", response_model=BaseResponse[dict])
async def delete_account(
    payload: DeleteAccountRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Authorizes deletions using OTP verification, applying soft deletes across tables."""
    await AuthService.delete_account(
        db=db,
        redis_client=redis_client,
        current_user=current_user,
        otp_code=payload.otp_code
    )
    return make_response(
        data={},
        success=True,
        code="ACCOUNT_DELETED",
        message="Your account has been deleted."
    )


@router.post("/verification/reupload", response_model=BaseResponse[dict])
async def reupload_verification_letter(
    document: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Re-uploads teacher recommendation document, resetting verification states and scheduling AI queue analysis."""
    # Ensure PDF upload constraint is met securely
    validate_pdf_file(document)

    result = await TeacherRegistrationService.reupload_verification_letter(
        db=db,
        teacher_id=current_user.id,
        document=document
    )

    return make_response(
        data=result,
        success=True,
        code="REUPLOAD_SUCCESS",
        message="Recommendation letter re-uploaded successfully. AI analysis scheduled."
    )
