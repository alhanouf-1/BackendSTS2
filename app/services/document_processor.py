import io
from typing import List, Dict, Any
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.ai.config import CHUNK_SIZE, CHUNK_OVERLAP

class DocumentProcessor:
    """Extracts layout text streams using pypdf and applies metadata filters."""

    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """Parses layout text from binary PDF data streams."""
        reader = PdfReader(io.BytesIO(pdf_bytes))
        full_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
        return "\n".join(full_text)

    @staticmethod
    def split_and_metadata_bind(
        text: str,
        course_id: str,
        teacher_id: str,
        lesson_id: str = "none",
        summary_id: str = "none",
        source_name: str = "document"
    ) -> List[Dict[str, Any]]:
        """
        Splits text into chunks using recursive splitters and anchors metadata tags.
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        chunks = splitter.split_text(text)
        
        chunk_documents = []
        for i, chunk in enumerate(chunks):
            chunk_documents.append({
                "content": chunk,
                "metadata": {
                    "course_id": course_id,
                    "teacher_id": teacher_id,
                    "lesson_id": lesson_id,
                    "summary_id": summary_id,
                    "source_name": source_name,
                    "chunk_index": i
                }
            })
        return chunk_documents
