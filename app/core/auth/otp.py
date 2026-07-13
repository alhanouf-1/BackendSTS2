import random
import redis.asyncio as aioredis
from app.config.logging import logger

OTP_TTL = 300  # 5 minutes in seconds

def generate_otp_code() -> str:
    """Generates a secure 6-digit numeric OTP code."""
    return f"{random.randint(100000, 999999)}"

async def save_otp(redis_client: aioredis.Redis, email: str, code: str, purpose: str) -> None:
    """
    Saves an OTP code to Redis with a 5-minute TTL.
    Key format: otp:{email}:{purpose}
    """
    key = f"otp:{email}:{purpose}"
    await redis_client.set(key, code, ex=OTP_TTL)
    logger.info("OTP saved in Redis", email=email, purpose=purpose, ttl=OTP_TTL)

async def verify_and_delete_otp(redis_client: aioredis.Redis, email: str, code: str, purpose: str) -> bool:
    """
    Atomically retrieves and deletes the OTP code from Redis if the code matches.
    Uses a Redis Lua script to perform atomic verify-and-delete.
    """
    key = f"otp:{email}:{purpose}"
    
    # Lua script: Gets the value, compares it, and deletes the key if correct.
    lua_script = """
    local val = redis.call('get', KEYS[1])
    if val == ARGV[1] then
        redis.call('del', KEYS[1])
        return 1
    else
        return 0
    end
    """
    
    result = await redis_client.eval(lua_script, 1, key, code)
    matched = bool(result)
    logger.info("OTP verification evaluated", email=email, purpose=purpose, matched=matched)
    return matched
