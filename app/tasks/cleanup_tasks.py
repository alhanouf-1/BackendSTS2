import asyncio
import os
import uuid
from celery.utils.log import get_task_logger
from app.config.celery import celery_app
from app.config.database import async_session_maker
from app.config.settings import settings
from app.models.teacher_verification import VerificationStatus
from app.models.user import UserRole
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.teacher_verification_repository import TeacherVerificationRepository
from app.repositories.user_repository import UserRepository

logger = get_task_logger(__name__)

async def _cleanup_expired_tokens_async() -> int:
    """Async wrapper executing the repository deletion transaction."""
    async with async_session_maker() as db:
        repo = RefreshTokenRepository(db)
        deleted_count = await repo.delete_expired_tokens()
        await db.commit()
        return deleted_count

@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_expired_tokens")
def cleanup_expired_tokens() -> int:
    """
    Scheduled cron job triggered by Celery Beat.
    Wipes expired authorization tokens to preserve database size.
    """
    logger.info("Executing database sweep for expired refresh tokens.")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        deleted_count = loop.run_until_complete(_cleanup_expired_tokens_async())
        logger.info(f"Database sweep complete. Purged {deleted_count} expired token records.")
        return deleted_count
    except Exception as e:
        logger.error(f"Database sweep failed with exception: {str(e)}")
        raise e


async def _analyze_teacher_document_async(verification_id: str) -> None:
    """Performs extraction and status update for Teacher recommendation letter."""
    verification_uuid = uuid.UUID(verification_id)
    async with async_session_maker() as db:
        verify_repo = TeacherVerificationRepository(db)
        user_repo = UserRepository(db)
        
        verification = await verify_repo.get_by_id(verification_uuid)
        if not verification:
            logger.error(f"TeacherVerification record {verification_id} not found.")
            return
            
        user = await user_repo.get_by_id(verification.user_id)
        if not user:
            logger.error(f"User associated with verification {verification_id} not found.")
            return

        doc_url = verification.document_url
        keywords_found = []
        university_name = "Unknown University"
        student_name = "Unknown Name"
        faculty_name = "Unknown Faculty"
        has_stamp_header = False

        if doc_url.startswith("/static/"):
            relative_path = doc_url.replace("/static/", "", 1)
            physical_path = os.path.join(settings.LOCAL_STORAGE_DIR, relative_path)
            
            if os.path.exists(physical_path):
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(physical_path)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() or ""
                    
                    text_lower = text.lower()
                    keywords = ["recommendation", "university", "faculty", "dean", "professor", "certify", "stamp", "signature"]
                    keywords_found = [kw for kw in keywords if kw in text_lower]
                    
                    if "stamp" in text_lower or "signature" in text_lower or "dean" in text_lower:
                        has_stamp_header = True
                        
                    # Extract rudimentary fields if found
                    for line in text.split("\n"):
                        line_clean = line.strip()
                        if "university" in line_clean.lower() and university_name == "Unknown University":
                            university_name = line_clean
                        if "faculty" in line_clean.lower() and faculty_name == "Unknown Faculty":
                            faculty_name = line_clean
                except Exception as ex:
                    logger.error(f"Error parsing PDF document details: {str(ex)}")
            else:
                logger.warn(f"Physical PDF file does not exist at local storage path: {physical_path}")

        # Basic verification heuristics: needs at least 2 relevant academic keywords
        if len(keywords_found) >= 2:
            verification.status = VerificationStatus.VERIFIED
            user.role = UserRole.VERIFIED_TEACHER
            logger.info(f"Verification ID {verification_id} verified successfully. User role elevated.")
        else:
            verification.status = VerificationStatus.FAILED
            logger.info(f"Verification ID {verification_id} failed verification validation check.")
            
        verification.ai_result = {
            "university_name": university_name,
            "student_name": student_name,
            "faculty_name": faculty_name,
            "has_stamp_header": has_stamp_header,
            "keywords_found": keywords_found
        }
        
        db.add(verification)
        db.add(user)
        await db.commit()

@celery_app.task(name="app.tasks.cleanup_tasks.analyze_teacher_document")
def analyze_teacher_document(verification_id: str) -> None:
    """Asynchronous background worker task validating PDF verification files."""
    logger.info(f"Booting verification analyzer task for ID: {verification_id}")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        loop.run_until_complete(_analyze_teacher_document_async(verification_id))
    except Exception as e:
        logger.error(f"Automated verification parser run failed: {str(e)}")
        raise e

async def _cleanup_expired_chats_async() -> int:
    from datetime import datetime, timezone, timedelta
    from app.models.chat_message import ChatMessage
    from app.models.virtual_session import VirtualSession
    from sqlalchemy import select, delete
    
    now = datetime.now(timezone.utc)
    async with async_session_maker() as db:
        sessions_query = select(VirtualSession)
        result = await db.execute(sessions_query)
        sessions = result.scalars().all()
        
        deleted_messages_count = 0
        for session in sessions:
            sess_time = session.scheduled_at
            if sess_time.tzinfo is None:
                compare_now = datetime.now()
            else:
                compare_now = datetime.now(timezone.utc)
                
            end_threshold = sess_time + timedelta(minutes=session.duration_minutes) + timedelta(hours=24)
            if compare_now > end_threshold:
                del_query = delete(ChatMessage).where(ChatMessage.session_id == session.id)
                del_result = await db.execute(del_query)
                deleted_messages_count += del_result.rowcount
                
        await db.commit()
        return deleted_messages_count

@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_expired_class_chats")
def cleanup_expired_class_chats() -> int:
    """Scheduled hourly cron garbage collector for expired live class chats."""
    logger.info("Starting garbage collection sweep for expired class chats.")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        count = loop.run_until_complete(_cleanup_expired_chats_async())
        logger.info(f"Class chats sweep complete. Purged {count} chat messages.")
        return count
    except Exception as e:
        logger.error(f"Class chats sweep failed: {str(e)}")
        raise e

async def _process_account_purging_async() -> int:
    from app.services.student_account_service import StudentAccountService
    async with async_session_maker() as db:
        purged = await StudentAccountService.purge_quarantined_accounts(db)
        return purged

@celery_app.task(name="app.tasks.cleanup_tasks.process_account_purging")
def process_account_purging() -> int:
    """Daily cron purging soft-deleted user records past the 30-day quarantine barrier."""
    logger.info("Executing account purging cron for quarantined soft-deleted users.")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        count = loop.run_until_complete(_process_account_purging_async())
        logger.info(f"Account purging complete. Hard-deleted {count} accounts.")
        return count
    except Exception as e:
        logger.error(f"Account purging cron failed: {str(e)}")
        raise e

