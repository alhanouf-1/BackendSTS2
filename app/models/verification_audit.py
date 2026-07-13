import uuid
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class VerificationAudit(BaseModel):
    """Persistent AI verification audit trails database logging table."""
    __tablename__ = "verification_audits"

    teacher_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    request_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ai_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    detected_university: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    detected_student: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    detected_faculty: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Stores outcome state: "VERIFIED", "PENDING", "FAILED"
    verification_result: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    teacher: Mapped["User"] = relationship("User")
