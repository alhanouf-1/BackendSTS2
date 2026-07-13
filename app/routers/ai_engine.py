import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.config.database import get_db
from app.config.redis import get_redis
from app.core.auth.dependencies import get_current_active_user
from app.core.utils.responses import BaseResponse, make_response
from app.models.user import User
from app.services.student_ai_service import StudentAIService
from app.services.rag_orchestrator_service import RAGOrchestratorService

router = APIRouter(prefix="/ai-engine", tags=["AI Engine"])

# Schema
class AIQAQueryRequest(BaseModel):
    course_id: uuid.UUID
    lesson_id: Optional[uuid.UUID] = None
    question: str = Field(..., min_length=3, max_length=2000)

def sanitize_user_input(text: str) -> None:
    """Interceptors scan user text inputs checking for prompt injection patterns."""
    lower_text = text.lower()
    override_patterns = [
        "ignore previous instruction",
        "ignore the instructions",
        "system prompt",
        "ignore above",
        "ignore following",
        "you are now a",
        "ignore all rules"
    ]
    for pattern in override_patterns:
        if pattern in lower_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security validation failed. Prompt injection signature detected."
            )

@router.post("/ask", response_model=BaseResponse[dict])
async def ask_ai_question(
    payload: AIQAQueryRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """
    Highly secure endpoint answering academic questions based on course/lesson vectors.
    """
    # 1. Input Sanitization
    sanitize_user_input(payload.question)

    # 2. Redis-backed budget limit checks
    await StudentAIService.enforce_rate_limit(redis_client, str(current_user.id))

    # 3. Call RAG pipeline
    result = await RAGOrchestratorService.ask_question(
        redis_client=redis_client,
        student_id=current_user.id,
        course_id=payload.course_id,
        lesson_id=payload.lesson_id,
        question=payload.question
    )

    return make_response(
        data=result,
        success=True,
        code="AI_ENGINE_RESOLVED",
        message="AI academic tutor response resolved."
    )
