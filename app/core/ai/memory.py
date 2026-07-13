import json
from typing import List, Dict, Any
import redis.asyncio as aioredis

class RedisChatMemory:
    """
    High-performance Redis-backed chat memory registry.
    Saves dialog sequences as JSON and maintains sliding windows to protect token budgets.
    """
    def __init__(self, redis_client: aioredis.Redis, session_id: str, ttl: int = 3600):
        self.redis = redis_client
        self.key = f"chat:history:{session_id}"
        self.ttl = ttl

    async def get_messages(self) -> List[Dict[str, str]]:
        """Loads conversation logs for the session."""
        data = await self.redis.get(self.key)
        if not data:
            return []
        try:
            return json.loads(data.decode("utf-8"))
        except Exception:
            return []

    async def add_message(self, role: str, content: str) -> None:
        """Appends a dialogue turn and slides the index frame limit."""
        messages = await self.get_messages()
        messages.append({"role": role, "content": content})
        # Keep last 10 turns to avoid token inflation
        messages = messages[-10:]
        await self.redis.set(self.key, json.dumps(messages), ex=self.ttl)

    async def clear(self) -> None:
        """Cleans memory keys from Redis."""
        await self.redis.delete(self.key)
