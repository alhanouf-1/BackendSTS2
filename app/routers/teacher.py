import os
import uuid
import json
from typing import Optional, List, Dict, Any
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    Form
)
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.config.database import get_db
from app.config.redis import get_redis
from app.config.logging import logger
from app.core.auth.dependencies import get_current_active_user
from app.core.auth.jwt import decode_access_token
from app.core.utils.responses import BaseResponse, make_response
from app.models.user import User, UserRole
from app.models.chat_message import AttachmentType
from app.services.teacher_course_service import TeacherCourseService, CourseStatus
from app.services.teacher_lesson_service import TeacherLessonService
from app.services.teacher_summary_service import TeacherSummaryService
from app.services.teacher_class_service import TeacherClassService
from app.services.teacher_chat_service import TeacherChatService
from app.services.teacher_analytics_service import TeacherAnalyticsService
from app.services.teacher_wallet_service import TeacherWalletService
from app.services.teacher_verification_service import TeacherVerificationService

router = APIRouter(prefix="/teacher", tags=["Teacher Workspace"])

# Schemas
class CourseCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    major: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., max_length=1024)
    price: float = Field(0.00, ge=0.00)

class CourseStatusUpdateRequest(BaseModel):
    status: CourseStatus

class ClassCreateRequest(BaseModel):
    course_id: uuid.UUID
    title: str = Field(..., min_length=3, max_length=255)
    date: str = Field(..., description="Format: YYYY-MM-DD")
    time: str = Field(..., description="Format: HH:MM")
    duration: int = Field(..., ge=15, le=480, description="Duration in minutes")

class WalletWithdrawRequest(BaseModel):
    amount: float = Field(..., ge=50.00, le=100000.00, description="Amount to withdraw (min 50 SAR)")

class DeleteAccountRequest(BaseModel):
    otp_code: str = Field(..., min_length=4, max_length=10)


# Video magic byte checking helper
def validate_video_file(file: UploadFile) -> None:
    # 1. Size constraint check (500MB)
    MAX_SIZE = 500 * 1024 * 1024
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video size exceeds the 500MB limit."
        )

    # 2. Extension check
    ext = file.filename.split(".")[-1].lower() if file.filename else ""
    if ext not in ("mp4", "mov", "webm"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported video file extension. Only MP4, MOV, and WebM are permitted."
        )

    # 3. Magic bytes validation
    header = file.file.read(12)
    file.file.seek(0)
    if b"ftyp" not in header and not header.startswith(b"\x1a\x45\xdf\xa3"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video file signature header (magic bytes verification failed)."
        )


# Endpoints

@router.post("/courses/create", response_model=BaseResponse[dict])
async def create_course(
    payload: CourseCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Enforces verified role check limits and creates free/paid courses."""
    if current_user.role not in (UserRole.TEACHER, UserRole.VERIFIED_TEACHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to instructor profiles only."
        )

    course = await TeacherCourseService.create_course(
        db=db,
        teacher=current_user,
        title=payload.title,
        code=payload.code,
        major=payload.major,
        description=payload.description,
        price=payload.price
    )
    return make_response(
        data={"course_id": str(course.id), "status": getattr(course, "status", "DRAFT")},
        success=True,
        code="COURSE_CREATED",
        message="Course created successfully in DRAFT state."
    )

@router.post("/courses/{course_id}/status", response_model=BaseResponse[dict])
async def update_course_status(
    course_id: uuid.UUID,
    payload: CourseStatusUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Updates course publishing states between DRAFT, PUBLISHED, and ARCHIVED."""
    course = await TeacherCourseService.update_course_status(
        db=db,
        teacher_id=current_user.id,
        course_id=course_id,
        new_status=payload.status
    )
    return make_response(
        data={"course_id": str(course.id), "status": payload.status.value},
        success=True,
        code="COURSE_STATUS_UPDATED",
        message=f"Course status updated to {payload.status.value}."
    )

@router.post("/lessons/create", response_model=BaseResponse[dict])
async def create_lesson(
    course_id: uuid.UUID = Form(...),
    title: str = Form(...),
    notes: str = Form(...),
    order: int = Form(...),
    video: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Accepts multipart video chunks, validates signatures, and triggers transcoder tasks."""
    validate_video_file(video)
    
    lesson = await TeacherLessonService.create_lesson(
        db=db,
        teacher_id=current_user.id,
        course_id=course_id,
        title=title,
        notes=notes,
        order=order,
        video=video
    )

    return make_response(
        data={"lesson_id": str(lesson.id), "title": lesson.title},
        success=True,
        code="LESSON_CREATED",
        message="Lesson created successfully and video analysis task queued."
    )

@router.post("/summaries/create", response_model=BaseResponse[dict])
async def create_summary(
    course_id: uuid.UUID = Form(...),
    title: str = Form(...),
    pdf: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Registers academic study notes and document summary attachments."""
    if not pdf.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Summary file must be a PDF document."
        )

    summary = await TeacherSummaryService.create_summary(
        db=db,
        teacher_id=current_user.id,
        course_id=course_id,
        title=title,
        pdf=pdf
    )

    return make_response(
        data={"summary_id": str(summary.id), "pdf_path": summary.pdf_path},
        success=True,
        code="SUMMARY_CREATED",
        message="Course summary handouts uploaded successfully."
    )

@router.post("/classes/create", response_model=BaseResponse[dict])
async def schedule_class(
    payload: ClassCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Schedules interactive virtual sessions."""
    session = await TeacherClassService.schedule_session(
        db=db,
        teacher_id=current_user.id,
        course_id=payload.course_id,
        title=payload.title,
        date_str=payload.date,
        time_str=payload.time,
        duration_minutes=payload.duration
    )
    return make_response(
        data={"session_id": str(session.id), "meeting_room_id": session.meeting_room_id},
        success=True,
        code="CLASS_SCHEDULED",
        message="Interactive virtual class scheduled successfully."
    )

@router.delete("/classes/{class_id}", response_model=BaseResponse[dict])
async def cancel_class(
    class_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Deletes virtual session schedules, invalidates caches, and dispatches attendee notifications."""
    await TeacherClassService.cancel_session(db, current_user.id, class_id)
    return make_response(
        data={},
        success=True,
        code="CLASS_CANCELLED",
        message="Live session has been successfully cancelled and students notified."
    )

@router.get("/analytics", response_model=BaseResponse[dict])
async def get_analytics(
    period: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    course_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Resolves teacher workspace analytics using performance Redis caches (15 min TTL)."""
    analytics = await TeacherAnalyticsService.get_analytics(
        db=db,
        redis_client=redis_client,
        teacher_id=current_user.id,
        course_id=course_id,
        period=period
    )
    return make_response(
        data=analytics,
        success=True,
        code="ANALYTICS_RESOLVED",
        message="Analytical statistics compiled."
    )

@router.get("/wallet", response_model=BaseResponse[dict])
async def get_wallet(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Resolves wallet ledger balance metrics and transaction arrays."""
    summary = await TeacherWalletService.get_wallet_summary(db, current_user.id)
    return make_response(
        data=summary,
        success=True,
        code="WALLET_RESOLVED",
        message="Wallet details loaded."
    )

@router.post("/wallet/withdraw", response_model=BaseResponse[dict])
async def withdraw_funds(
    payload: WalletWithdrawRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Deducts balances with Concurrency locks checking solvency boundaries."""
    withdrawal = await TeacherWalletService.request_withdrawal(db, current_user.id, payload.amount)
    
    # Save database transaction block explicitly
    await db.commit()

    return make_response(
        data={"withdrawal_id": str(withdrawal.id), "amount": float(withdrawal.amount), "status": withdrawal.status.value},
        success=True,
        code="WITHDRAWAL_SUBMITTED",
        message="Withdrawal request submitted successfully."
    )

@router.post("/upload-recommendation", response_model=BaseResponse[dict])
async def re_upload_recommendation(
    pdf: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Resets failed verification state walls and registers letter re-uploads."""
    if not pdf.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification document must be a PDF."
        )

    verification = await TeacherVerificationService.re_upload_recommendation(db, current_user.id, pdf)
    await db.commit()

    return make_response(
        data={"verification_id": str(verification.id), "status": verification.status.value},
        success=True,
        code="RECOMMENDATION_REUPLOADED",
        message="Verification document re-uploaded. AI auditing checks triggered."
    )

@router.delete("/delete-account", response_model=BaseResponse[dict])
async def delete_account(
    payload: DeleteAccountRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Student/Teacher account soft-delete deactivations for 30-day quarantines."""
    await StudentAccountService.soft_delete_student_account(
        db=db,
        redis_client=redis_client,
        student_id=current_user.id,
        otp_code=payload.otp_code
    )
    return make_response(
        data={},
        success=True,
        code="ACCOUNT_SOFT_DELETED",
        message="Account has been successfully deactivated and placed in 30-day quarantine."
    )


# WebSocket handlers

@router.websocket_route("/chat/{room_id}")
async def ws_teacher_chat(websocket: WebSocket):
    room_id_str = websocket.path_params.get("room_id")
    token = websocket.query_params.get("token")
    
    if not token or not room_id_str:
        await websocket.close(code=4001)
        return
        
    try:
        room_uuid = uuid.UUID(room_id_str)
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            await websocket.close(code=4001)
            return
        user_uuid = uuid.UUID(user_id_str)
    except Exception:
        await websocket.close(code=4001)
        return

    # Symmetrical chat room entry point
    room_key = f"room_{room_id_str}"
    await TeacherChatService.connect_room(websocket, room_key)

    try:
        while True:
            text_data = await websocket.receive_text()
            data = json.loads(text_data)
            
            msg_text = data.get("message")
            att_url = data.get("attachment_url")
            att_type_str = data.get("attachment_type", "NONE")
            
            att_type = AttachmentType.NONE
            if att_type_str in AttachmentType.__members__:
                att_type = AttachmentType[att_type_str]

            from app.config.database import async_session_maker
            async with async_session_maker() as db:
                msg = await TeacherChatService.save_message(
                    db=db,
                    sender_id=user_uuid,
                    course_id=room_uuid if "course" in room_key else None,
                    message_text=msg_text,
                    attachment_url=att_url,
                    attachment_type=att_type
                )
                
            await TeacherChatService.broadcast_to_room(room_key, {
                "message_id": str(msg.id),
                "sender_id": str(user_uuid),
                "message": msg_text,
                "attachment_url": att_url,
                "attachment_type": att_type.value,
                "created_at": msg.created_at.isoformat()
            })
    except WebSocketDisconnect:
        TeacherChatService.disconnect_room(websocket, room_key)
    except Exception as e:
        logger.error("Error in teacher chat session WebSocket loop", error=str(e))
        TeacherChatService.disconnect_room(websocket, room_key)
