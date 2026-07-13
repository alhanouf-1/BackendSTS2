import uuid
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class Summary(BaseModel):
    """Course study handouts, notes, and attachment summary metadata."""
    __tablename__ = "summaries"

    course_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    pdf_path: Mapped[str] = mapped_column(String(512), nullable=True)
    file_url: Mapped[str] = mapped_column(String(512), nullable=True)
    description: Mapped[str] = mapped_column(String(1024), nullable=True)

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="summaries")
