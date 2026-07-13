import redis.asyncio as aioredis
from typing import AsyncGenerator
from app.config.settings import settings

# Create connection pool
redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=50,
    decode_responses=True
)

def get_redis_client() -> aioredis.Redis:
    """Returns an active Redis client from the shared pool."""
    return aioredis.Redis(connection_pool=redis_pool)

async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI Dependency for Redis client injection."""
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.close()
