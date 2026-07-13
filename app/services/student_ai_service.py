import uuid
import time
from typing import Dict, Any, Optional
import redis.asyncio as aioredis
from fastapi import HTTPException, status
from app.config.settings import settings
from app.config.logging import logger
from app.core.ai.chromadb import get_chroma_client
from app.core.ai.embeddings import embeddings

class StudentAIService:
    """Orchestrates course-isolated AI assistant conversations with Redis sliding window rate limits."""

    @staticmethod
    async def enforce_rate_limit(redis_client: aioredis.Redis, student_id: str) -> None:
        """Enforces a strict sliding-window rate limit: 30 requests/hour and 100 requests/day per user."""
        now = time.time()
        hourly_key = f"rate:limit:ai:hourly:{student_id}"
        daily_key = f"rate:limit:ai:daily:{student_id}"

        # 1. Hourly check
        await redis_client.zremrangebyscore(hourly_key, 0, now - 3600)
        hourly_count = await redis_client.zcard(hourly_key)
        if hourly_count >= 30:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Maximum 30 AI queries per hour."
            )

        # 2. Daily check
        await redis_client.zremrangebyscore(daily_key, 0, now - 86400)
        daily_count = await redis_client.zcard(daily_key)
        if daily_count >= 100:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Maximum 100 AI queries per day."
            )

        # 3. Increment counters atomically
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.zadd(hourly_key, {str(now): now})
            pipe.expire(hourly_key, 3600)
            pipe.zadd(daily_key, {str(now): now})
            pipe.expire(daily_key, 86400)
            await pipe.execute()

    @staticmethod
    async def ask_question(
        redis_client: aioredis.Redis,
        student_id: uuid.UUID,
        course_id: uuid.UUID,
        question: str
    ) -> str:
        # Enforce rate limits
        await StudentAIService.enforce_rate_limit(redis_client, str(student_id))

        # Retrieve relevant text segments from ChromaDB collection for the course
        chroma = get_chroma_client()
        collection_name = f"course_{course_id}"
        
        context = ""
        try:
            # Query the course vector collection
            collection = chroma.get_collection(name=collection_name)
            query_vector = embeddings.embed_query(question)
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=3
            )
            documents = results.get("documents", [[]])[0]
            context = "\n".join(documents)
        except Exception as e:
            logger.warn("ChromaDB query fallback. Collection may not be initialized yet.", course_id=str(course_id), error=str(e))
            context = "No course-specific context document materials are available currently."

        # Execute OpenAI API RAG completion (or mock fallback if API key is not present)
        system_prompt = (
            "You are a helpful academic AI tutor assistant for the Student Tutoring System (STS).\n"
            "Answer the student's question based strictly on the provided course context materials.\n"
            "If you cannot find the answer in the context, guide them using general scientific principles but state that it is not in the official materials.\n\n"
            f"Course Materials Context:\n{context}\n\n"
            f"Student Question: {question}"
        )

        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "mock":
            logger.warn("OpenAI API Key is missing. Returning RAG Mock reply fallback.")
            return f"[Mock AI RAG Response] (Scoped to Course {course_id})\nBased on the materials: {question[:30]}..."

        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional academic assistant."},
                    {"role": "user", "content": system_prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as ex:
            logger.error("Failed to query OpenAI completion endpoint", error=str(ex))
            return f"Error executing AI RAG pipeline request. (Local Mock response fallback)\nContext found: {context[:50]}"
