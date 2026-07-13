import uuid
from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class CoursePreview(BaseModel):
    """Course individual free trials preview video authorization links configuration."""
    __tablename__ = "course_previews"

    course_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False
    )
    
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False
    )
    
    is_free_preview: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="previews")
    lesson: Mapped["Lesson"] = relationship("Lesson")
