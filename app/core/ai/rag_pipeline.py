from app.core.ai.chromadb import get_chroma_client
from app.core.ai.embeddings import embeddings

class RAGPipeline:
    """Metadata RAG chain query helpers retrieving context from vectorized document indexes."""
    
    @staticmethod
    def query_document(teacher_id: str, query_text: str) -> str:
        """
        Retrieves relevant text segments for a given teacher's document from ChromaDB.
        """
        client = get_chroma_client()
        collection_name = f"teacher_{teacher_id}"
        
        try:
            collection = client.get_collection(name=collection_name)
            
            # Embed the search query
            query_vector = embeddings.embed_query(query_text)
            
            # Query vector database for matching chunks
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=3
            )
            
            documents = results.get("documents", [[]])[0]
            context = "\n".join(documents)
            return context
        except Exception:
            # Return empty if collection doesn't exist or query fails
            return ""
