import os
import chromadb
from app.config.settings import settings

# Determine persistent path
chroma_path = os.path.join(settings.LOCAL_STORAGE_DIR, "chromadb")
os.makedirs(chroma_path, exist_ok=True)

# Shared persistent ChromaDB client instance
chroma_client = chromadb.PersistentClient(path=chroma_path)

def get_chroma_client() -> chromadb.PersistentClient:
    """Returns the persistent ChromaDB client."""
    return chroma_client
