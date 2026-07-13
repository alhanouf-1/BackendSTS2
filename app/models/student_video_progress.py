import uuid
from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class StudentVideoProgress(BaseModel):
    """
    Tracks telemetry and duration logs for lesson videos.
    Used to calculate overall progress and enforce review permissions.
    """
    __tablename__ = "student_video_progress"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False
    )
    watched_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    total_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    completion_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.00,
        nullable=False
    )
    last_position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Relationships
    student: Mapped["User"] = relationship("User")
    lesson: Mapped["Lesson"] = relationship("Lesson")
