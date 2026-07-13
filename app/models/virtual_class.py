import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class VirtualClass(BaseModel):
    """Virtual live sessions scheduling metadata setup."""
    __tablename__ = "virtual_classes"

    course_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False
    )
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    join_url: Mapped[str] = mapped_column(String(512), nullable=False)

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="virtual_classes")
