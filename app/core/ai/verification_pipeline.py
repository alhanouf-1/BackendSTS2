import os
import re
from typing import Dict, Any, List
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config.settings import settings
from app.config.logging import logger
from app.core.ai.chromadb import get_chroma_client
from app.core.ai.embeddings import embeddings

def run_5_factor_verification(text: str, teacher_name: str) -> Dict[str, Any]:
    """
    Executes a 5-Factor Context Identification Check on recommendation text:
    1. Saudi University identity check
    2. Student name check (match teacher registration metadata)
    3. Faculty member validation
    4. Official seal / signature keywords
    5. Academic recommendation keywords
    """
    text_lower = text.lower()
    
    # 1. Saudi University Identity Validation
    saudi_universities = [
        "king saud university", "ksu", "جامعة الملك سعود",
        "king abdulaziz university", "kau", "جامعة الملك عبدالعزيز",
        "king fahd university", "kfupm", "جامعة الملك فهد",
        "imam mohammad ibn saud islamic university", "imamu", "جامعة الإمام",
        "princess nourah university", "pnu", "جامعة الأميرة نورة",
        "umm al-qura university", "uqu", "جامعة أم القرى",
        "king khalid university", "kku", "جامعة الملك خالد",
        "taibah university", "جامعة طيبة",
        "qassim university", "جامعة القصيم",
        "saudi electronic university", "seu", "الجامعة السعودية الإلكترونية"
    ]
    has_saudi_uni = False
    detected_uni = "Unknown University"
    for uni in saudi_universities:
        if uni in text_lower:
            has_saudi_uni = True
            detected_uni = uni.title()
            break

    # 2. Student Name Verification (requires matching part of teacher_name)
    name_words = re.findall(r"\w+", teacher_name.lower())
    has_name_match = False
    matched_names = []
    if name_words:
        # Ignore short noise terms
        valid_words = [w for w in name_words if len(w) > 2]
        for word in valid_words:
            if word in text_lower:
                matched_names.append(word)
        if len(matched_names) >= 1:
            has_name_match = True
            
    # 3. Faculty Signatory Authority Verification
    faculty_indicators = ["dr", "doctor", "professor", "prof", "dean", "أ.د", "دكتور", "د.", "عميد", "أستاذ"]
    has_faculty_prefix = any(re.search(rf"\b{pref}\b", text_lower) for pref in faculty_indicators) or any(pref in text_lower for pref in ["عميد", "أستاذ", "دكتور"])
    detected_fac = "Professor/Dean Signatory" if has_faculty_prefix else "Unknown"

    # 4. Stamp / Seal / Official Headers Check
    stamp_indicators = ["stamp", "seal", "letterhead", "logo", "official", "signature", "ختم", "توقيع", "رسمي", "شعار"]
    has_stamp = any(kw in text_lower for kw in stamp_indicators)

    # 5. Academic Recommendation Context Keywords
    academic_indicators = ["recommendation", "outstanding", "grade", "certified", "tutor", "academic", "student", "توصية", "جامعة", "أكاديمي", "طالب", "ممتاز"]
    matches_count = sum(1 for kw in academic_indicators if kw in text_lower)
    has_academic_keywords = matches_count >= 2

    # Calculate 5-Factor Score (20 points each, Max 100)
    score = 0
    if has_saudi_uni:
        score += 20
    if has_name_match:
        score += 20
    if has_faculty_prefix:
        score += 20
    if has_stamp:
        score += 20
    if has_academic_keywords:
        score += 20

    # Determine status
    if score >= 80:
        result = "VERIFIED"
    elif score >= 50:
        result = "PENDING"
    else:
        result = "FAILED"

    return {
        "ai_score": score,
        "verification_result": result,
        "detected_university": detected_uni,
        "detected_student": teacher_name if has_name_match else "Unknown",
        "detected_faculty": detected_fac,
        "factors": {
            "saudi_university": has_saudi_uni,
            "name_match": has_name_match,
            "faculty_prefix": has_faculty_prefix,
            "stamp_seal": has_stamp,
            "academic_keywords": has_academic_keywords
        }
    }

async def process_and_embed_document(teacher_id: str, teacher_name: str, file_path: str) -> Dict[str, Any]:
    """
    1. Extracts PDF text.
    2. Chunks the text using LangChain character splitters.
    3. Generates and registers embeddings inside persistent ChromaDB.
    4. Evaluates document factors.
    """
    logger.info("Starting document text extraction", teacher_id=teacher_id, file_path=file_path)
    
    # 1. Text extraction using pypdf
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF file does not exist at local path: {file_path}")
        
    reader = PdfReader(file_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() or ""
        
    # 2. Text splitting using RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_text(full_text)
    logger.info("PDF chunked successfully", chunks_count=len(chunks))

    # 3. Vectorization and persistence in ChromaDB
    chroma = get_chroma_client()
    collection_name = f"teacher_{teacher_id}"
    
    # Wipe old collection if exists to support re-upload flows
    try:
        chroma.delete_collection(name=collection_name)
    except Exception:
        pass
        
    collection = chroma.create_collection(name=collection_name)
    
    if chunks:
        # Retrieve vector values
        chunk_embeddings = embeddings.embed_documents(chunks)
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"teacher_id": teacher_id} for _ in chunks]
        
        collection.add(
            ids=ids,
            embeddings=chunk_embeddings,
            documents=chunks,
            metadatas=metadatas
        )
        logger.info("Document embeddings persisted in ChromaDB", collection_name=collection_name)

    # 4. Context checking analysis
    verification_results = run_5_factor_verification(full_text, teacher_name)
    return verification_results
