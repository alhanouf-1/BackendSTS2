import re
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.ai.config import CHUNK_SIZE, CHUNK_OVERLAP

class VideoTranscriptService:
    """Parses caption transcripts and maps timestamp segments into metadata anchors."""

    @staticmethod
    def parse_vtt_transcript(vtt_content: str) -> List[Dict[str, Any]]:
        """
        Parses VTT styled blocks mapping timestamps to speech content.
        E.g. 00:01:20.000 --> 00:01:23.000
        """
        lines = vtt_content.splitlines()
        segments = []
        
        current_time = "00:00:00"
        time_pattern = re.compile(r"(\d{2}:\d{2}:\d{2})")
        
        for line in lines:
            line = line.strip()
            if not line or line.upper() == "WEBVTT":
                continue
            
            # Match timestamp line
            match = time_pattern.search(line)
            if match:
                current_time = match.group(1)
            elif not line.isdigit():
                segments.append({
                    "timestamp": current_time,
                    "text": line
                })
        return segments

    @staticmethod
    def chunk_transcript(
        segments: List[Dict[str, Any]],
        course_id: str,
        teacher_id: str,
        lesson_id: str
    ) -> List[Dict[str, Any]]:
        """
        Splits parsed segments into text chunks while preserving the start timestamp.
        """
        full_text = " ".join([f"[{seg['timestamp']}] {seg['text']}" for seg in segments])
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        chunks = splitter.split_text(full_text)
        
        time_pattern = re.compile(r"\[(\d{2}:\d{2}:\d{2})\]")
        chunk_documents = []
        for i, chunk in enumerate(chunks):
            # Locate first timestamp in chunk or fallback to start
            match = time_pattern.search(chunk)
            timestamp = match.group(1) if match else "00:00:00"
            
            # Clean timestamp brackets for readability
            clean_chunk = time_pattern.sub("", chunk).strip()

            chunk_documents.append({
                "content": clean_chunk,
                "metadata": {
                    "course_id": course_id,
                    "teacher_id": teacher_id,
                    "lesson_id": lesson_id,
                    "source_name": f"video_transcript_at_{timestamp}",
                    "timestamp": timestamp,
                    "chunk_index": i
                }
            })
        return chunk_documents
