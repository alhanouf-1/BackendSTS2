import uuid
from typing import Dict, Any, List, Optional
import redis.asyncio as aioredis
from app.core.ai.client import get_chroma_client
from app.core.ai.embeddings import embeddings
from app.core.ai.config import CHROMA_COLLECTION_NAME, LLM_MODEL
from app.core.ai.memory import RedisChatMemory
from app.config.settings import settings
from app.config.logging import logger

class RAGOrchestratorService:
    """Orchestrates secure multi-tier document lookups, historical context, and citation outputs."""

    @staticmethod
    async def ask_question(
        redis_client: aioredis.Redis,
        student_id: uuid.UUID,
        course_id: uuid.UUID,
        lesson_id: Optional[uuid.UUID],
        question: str
    ) -> Dict[str, Any]:
        
        # 1. Construct database-level multi-tenant filter boundary
        where_filter = {"course_id": str(course_id)}
        if lesson_id:
            # Narrow lookup context strictly down to a specific target lesson
            where_filter = {
                "$and": [
                    {"course_id": str(course_id)},
                    {"lesson_id": str(lesson_id)}
                ]
            }

        # 2. Retrieve relevant text chunks from ChromaDB
        chroma = get_chroma_client()
        context_texts = []
        sources = []

        try:
            collection = chroma.get_collection(name=CHROMA_COLLECTION_NAME)
            query_vector = embeddings.embed_query(question)
            results = collection.query(
                query_embeddings=[query_vector],
                where=where_filter,
                n_results=3
            )
            
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]

            for doc, meta in zip(documents, metadatas):
                context_texts.append(doc)
                sources.append({
                    "summary_id": meta.get("summary_id", "none"),
                    "lesson_id": meta.get("lesson_id", "none"),
                    "source_name": meta.get("source_name", "Academic Materials"),
                    "snippet": doc[:200] + ("..." if len(doc) > 200 else "")
                })
        except Exception as e:
            logger.warn("ChromaDB retrieval query fallback. Collection may not be initialized yet.", error=str(e))
            context_texts = ["No active course documents or classroom materials found."]

        # 3. Retrieve sliding chat history from Redis memory
        session_id = f"session:{student_id}:{course_id}"
        memory = RedisChatMemory(redis_client, session_id)
        chat_history = await memory.get_messages()

        history_str = ""
        for turn in chat_history:
            history_str += f"{turn['role'].upper()}: {turn['content']}\n"

        # 4. Construct prompt accommodating both Arabic and English academic inquiries
        system_prompt = (
            "You are a helpful academic AI tutor assistant for the Student Tutoring System (STS).\n"
            "Answer the student's question based strictly on the provided context and history.\n"
            "If you do not know or cannot locate the answer, clearly state that the answer is not present in the materials.\n"
            "Support both Arabic and English queries based on the language of the student.\n\n"
            f"Context Materials:\n{chr(10).join(context_texts)}\n\n"
            f"Chat History:\n{history_str}\n"
            f"Student Question: {question}"
        )

        # 5. Call OpenAI Completion (or mock fallback if API key is not present)
        response_text = ""
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "mock":
            logger.warn("OpenAI API Key is missing. Returning Mock RAG completion.")
            response_text = f"[Mock AI response] Academic reply for: '{question[:20]}'. Scoped to course {course_id}."
        else:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                response = await client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a professional academic assistant."},
                        {"role": "user", "content": system_prompt}
                    ],
                    max_tokens=600,
                    temperature=0.3
                )
                response_text = response.choices[0].message.content
            except Exception as ex:
                logger.error("Failed to query OpenAI Chat endpoint", error=str(ex))
                response_text = "Error executing AI RAG pipeline request. (Local Mock response fallback)"

        # 6. Save current turn to sliding memory
        await memory.add_message("user", question)
        await memory.add_message("assistant", response_text)

        return {
            "answer": response_text,
            "sources": sources
        }
