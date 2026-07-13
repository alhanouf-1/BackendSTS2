import uuid
from typing import List, Dict, Any
from app.core.ai.client import get_chroma_client
from app.core.ai.embeddings import embeddings
from app.core.ai.config import CHROMA_COLLECTION_NAME
from app.config.logging import logger

class VectorIndexService:
    """Manages vector persistence operations and database-level metadata purges inside ChromaDB."""

    @staticmethod
    async def inject_chunks(chunks: List[Dict[str, Any]]) -> None:
        """Embeds text chunks and commits them to the global vector space."""
        if not chunks:
            return

        chroma = get_chroma_client()
        collection = chroma.get_or_create_collection(name=CHROMA_COLLECTION_NAME)

        texts = [chunk["content"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        ids = [f"chk_{uuid.uuid4().hex}" for _ in chunks]

        # Generate embeddings asynchronously
        # For LangChain embeddings, embed_documents is synchronous or asynchronous.
        # We wrap it or call it directly.
        try:
            embedded_vectors = embeddings.embed_documents(texts)
        except Exception as e:
            logger.error("Failed to generate embeddings via provider API. Indexing failed.", error=str(e))
            raise e

        # Commit to vector index
        collection.add(
            ids=ids,
            embeddings=embedded_vectors,
            metadatas=metadatas,
            documents=texts
        )
        logger.info(f"Successfully injected {len(chunks)} text chunks into ChromaDB.")

    @staticmethod
    def purge_by_filter(where_filter: Dict[str, Any]) -> None:
        """
        Hard-deletes all vector indexes satisfying the metadata criteria.
        E.g. where_filter = {"summary_id": "uuid"}
        """
        chroma = get_chroma_client()
        try:
            collection = chroma.get_collection(name=CHROMA_COLLECTION_NAME)
            collection.delete(where=where_filter)
            logger.info("ChromaDB index purged successfully.", filter=where_filter)
        except Exception as e:
            logger.warn("ChromaDB index purge fallback. Collection may not be initialized yet.", error=str(e))
