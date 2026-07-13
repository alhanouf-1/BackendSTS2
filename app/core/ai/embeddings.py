from typing import List
from langchain_community.embeddings import OpenAIEmbeddings
from app.config.settings import settings
from app.config.logging import logger

class MockEmbeddings:
    """Mock embeddings provider to bypass external API checks during local development."""
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.1] * 1536 for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        return [0.1] * 1536

def get_embeddings():
    """
    Returns OpenAIEmbeddings if API key is present; otherwise returns MockEmbeddings.
    """
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "mock":
        logger.warn("OpenAI API Key is missing. Using MockEmbeddings fallback.")
        return MockEmbeddings()
        
    try:
        return OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            model="text-embedding-3-small"
        )
    except Exception as e:
        logger.error(f"Failed to instantiate OpenAIEmbeddings. Falling back. Error: {str(e)}")
        return MockEmbeddings()
embeddings = get_embeddings()
