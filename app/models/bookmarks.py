import uuid
from typing import Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class Bookmark(BaseModel):
    """
    Normalized bookmark registry linking active courses, lessons, or notes.
    """
    __tablename__ = "bookmarks"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    course_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True
    )
    lesson_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=True
    )
    summary_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("summaries.id", ondelete="CASCADE"),
        nullable=True
    )
    bookmark_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    # Relationships
    student: Mapped["User"] = relationship("User")
    course: Mapped[Optional["Course"]] = relationship("Course")
    lesson: Mapped[Optional["Lesson"]] = relationship("Lesson")
    summary: Mapped[Optional["Summary"]] = relationship("Summary")
