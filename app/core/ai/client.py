import threading
import chromadb
from app.config.settings import settings

_client = None
_lock = threading.Lock()

def get_chroma_client() -> chromadb.PersistentClient:
    """
    Thread-safe double-checked locking singleton accessor for the
    ChromaDB Persistent Client.
    """
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = chromadb.PersistentClient(path=settings.CHROMA_DB_DIR)
    return _client
