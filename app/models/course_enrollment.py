import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class CourseEnrollment(BaseModel):
    """Enrolled student course enrollment registration ledger."""
    __tablename__ = "course_enrollments"

    course_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False
    )
    
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime, 
        server_default=func.now(), 
        nullable=False
    )

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="enrollments")
    student: Mapped["User"] = relationship("User")
