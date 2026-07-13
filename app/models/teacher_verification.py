import enum
import uuid
from typing import Dict, Any, Optional
from sqlalchemy import String, Enum as SQLEnum, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class VerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"

class TeacherVerification(BaseModel):
    """Teacher Verification Ledger mapping processed documents & AI parsing states."""
    __tablename__ = "teacher_verifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    
    document_url: Mapped[str] = mapped_column(
        String(512), 
        nullable=False
    )
    
    status: Mapped[VerificationStatus] = mapped_column(
        SQLEnum(VerificationStatus), 
        default=VerificationStatus.PENDING, 
        nullable=False
    )
    
    # Store extraction map: {"university_name": str, "student_name": str, "faculty_name": str, "has_stamp_header": bool, "keywords_found": list}
    ai_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, 
        default=lambda: {
            "university_name": None,
            "student_name": None,
            "faculty_name": None,
            "has_stamp_header": False,
            "keywords_found": []
        },
        nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="verification")
