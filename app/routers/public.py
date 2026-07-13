from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.config.database import get_db
from app.config.redis import get_redis
from app.core.utils.responses import BaseResponse, make_response, current_lang
from app.services.public_service import PublicService
from app.services.course_public_service import CoursePublicService

router = APIRouter(prefix="/public", tags=["Public Data"])

@router.get("/hero", response_model=BaseResponse[dict])
async def get_hero(
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Fetches localized landing page Hero layouts from cache/database."""
    lang = current_lang.get()
    hero_data = await PublicService.get_hero(db, redis_client, lang)
    return make_response(
        data=hero_data,
        success=True,
        code="HERO_LOADED",
        message="Hero segment layout loaded."
    )

@router.get("/why-sts", response_model=BaseResponse[list])
async def get_why_sts(
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Fetches localized value propositions from cache/database."""
    lang = current_lang.get()
    items = await PublicService.get_why_sts(db, redis_client, lang)
    return make_response(
        data=items,
        success=True,
        code="WHY_STS_LOADED",
        message="Why STS value propositions loaded."
    )

@router.get("/faqs", response_model=BaseResponse[list])
async def get_faqs(
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Fetches localized FAQs from cache/database."""
    lang = current_lang.get()
    faqs = await PublicService.get_faqs(db, redis_client, lang)
    return make_response(
        data=faqs,
        success=True,
        code="FAQS_LOADED",
        message="Frequently Asked Questions loaded."
    )

@router.get("/testimonials", response_model=BaseResponse[list])
async def get_testimonials(
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Fetches localized user feedback testimonies from cache/database."""
    lang = current_lang.get()
    testimonials = await PublicService.get_testimonials(db, redis_client, lang)
    return make_response(
        data=testimonials,
        success=True,
        code="TESTIMONIALS_LOADED",
        message="User feedback testimonial layout resolved."
    )

@router.get("/courses", response_model=BaseResponse[dict])
async def search_courses(
    q: Optional[str] = Query(None, description="Free-text search query tokenizing course titles and descriptions"),
    university: Optional[str] = Query(None, description="Saudi University name filter"),
    code: Optional[str] = Query(None, description="Course classification symbol code"),
    major: Optional[str] = Query(None, description="Course major study field"),
    rating_min: Optional[int] = Query(None, ge=1, le=5, description="Minimum star score boundary (1 to 5)"),
    teacher_name: Optional[str] = Query(None, description="Partial/Exact teacher username lookup"),
    price: Optional[str] = Query(None, description="Price filter mapping: 'free' vs 'paid'"),
    skip: int = Query(0, ge=0, description="Offset cursor mapping"),
    limit: int = Query(10, ge=1, le=20, description="Page size limit capped at 20"),
    db: AsyncSession = Depends(get_db)
):
    """Executes advanced course filtering queries, enforcing teacher visibility redaction."""
    courses, total = await CoursePublicService.search_courses(
        db=db,
        q=q,
        university=university,
        code=code,
        major=major,
        rating_min=rating_min,
        teacher_name=teacher_name,
        price_type=price,
        skip=skip,
        limit=limit
    )

    return make_response(
        data={
            "courses": courses,
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total
            }
        },
        success=True,
        code="COURSES_SEARCH_SUCCESS",
        message="Advanced courses query matching complete."
    )

@router.get("/courses/{course_id}", response_model=BaseResponse[dict])
async def get_course_details(
    course_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Resolves detailed course layout parameters including child counts."""
    details = await CoursePublicService.get_course_details(db, course_id)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course does not exist or has been soft-deleted."
        )

    return make_response(
        data=details,
        success=True,
        code="COURSE_DETAILS_SUCCESS",
        message="Deep course analytic metadata resolved successfully."
    )
