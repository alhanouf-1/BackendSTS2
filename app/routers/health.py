from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.config.database import get_db
from app.config.redis import get_redis
from app.core.utils.responses import BaseResponse, make_response

router = APIRouter(tags=["Health"])

@router.get("/health/live", response_model=BaseResponse[dict])
async def liveness_check():
    """Liveness check to verify the HTTP server processes requests."""
    return make_response(
        data={"status": "ok"},
        success=True,
        code="LIVENESS_SUCCESS",
        message="Container processes are online."
    )

@router.get("/health/ready", response_model=BaseResponse[dict])
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Readiness check validating active MySQL and Redis socket connections."""
    db_ok = False
    redis_ok = False
    errors = {}

    # Test SQL execution
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        errors["database"] = str(e)

    # Test Redis Ping
    try:
        await redis_client.ping()
        redis_ok = True
    except Exception as e:
        errors["redis"] = str(e)

    success = db_ok and redis_ok
    return make_response(
        data={
            "database": "connected" if db_ok else "offline",
            "redis": "connected" if redis_ok else "offline",
            "errors": errors if errors else None
        },
        success=success,
        code="READY" if success else "INFRASTRUCTURE_ERROR",
        message="Services operational." if success else "Critical infrastructure failures detected."
    )
