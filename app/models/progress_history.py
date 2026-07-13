import uuid
from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class ProgressHistory(BaseModel):
    """
    Persistent audit ledger tracking student course progress modifications.
    """
    __tablename__ = "progress_history"

    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False
    )
    old_progress: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False
    )
    new_progress: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False
    )

    # Relationships
    student: Mapped["User"] = relationship("User")
    course: Mapped["Course"] = relationship("Course")
