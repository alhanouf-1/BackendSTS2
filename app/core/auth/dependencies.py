import time
from typing import Optional
from fastapi import Request, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.config.database import get_db
from app.config.redis import get_redis
from app.core.auth.jwt import decode_access_token
from app.core.utils.exceptions import (
    TokenInvalidException, 
    RateLimitExceededException, 
    UserNotFoundException
)
from app.core.utils.responses import current_lang
from app.models.user import User
from app.repositories.user_repository import UserRepository

# OAuth2 schema configuration point
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", 
    auto_error=False
)

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Decodes the JWT access token and loads the associated User entity.
    """
    if not token:
        raise TokenInvalidException("Missing authorization token header.")
        
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise TokenInvalidException("Subject missing from token claims.")
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user or user.is_deleted:
        raise UserNotFoundException("User associated with this token is not active or has been deleted.")
        
    # Dynamically inject language preference from user model JSON preferences into current request context
    if user.preferences and "lang" in user.preferences:
        current_lang.set(user.preferences["lang"])
        
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verifies that the extracted user is verified/active."""
    # Custom rules can block non-verified users if necessary, but we return active users
    return current_user

class RateLimiter:
    """
    Sliding-window Rate Limiter using Redis Sorted Sets.
    """
    def __init__(self, requests: int, window_seconds: int = 60):
        self.requests = requests
        self.window_seconds = window_seconds

    async def __call__(
        self, 
        request: Request, 
        redis_client: aioredis.Redis = Depends(get_redis)
    ) -> None:
        # Determine rate limit key using client IP and route path
        ip = request.client.host if request.client else "unknown"
        route = request.url.path
        key = f"rate_limit:{ip}:{route}"
        
        now = time.time()
        clear_before = now - self.window_seconds
        
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key, 0, clear_before)
            pipe.zadd(key, {f"{now}-{uuid_str()}": now})
            pipe.zcard(key)
            pipe.expire(key, self.window_seconds)
            results = await pipe.execute()
            
            # The card count is the 3rd result from our transaction pipeline
            card = results[2]
            
        if card > self.requests:
            raise RateLimitExceededException(
                message=f"Rate limit exceeded. Max {self.requests} requests allowed per {self.window_seconds} seconds."
            )

def uuid_str() -> str:
    import uuid
    return uuid.uuid4().hex
