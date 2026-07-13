import uuid
from sqlalchemy import ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class StudentSummaryProgress(BaseModel):
    """
    Tracks viewed/accessed study summaries, handouts, and notes.
    """
    __tablename__ = "student_summary_progress"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    summary_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("summaries.id", ondelete="CASCADE"),
        nullable=False
    )
    is_viewed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Relationships
    student: Mapped["User"] = relationship("User")
    summary: Mapped["Summary"] = relationship("Summary")
