import uuid
from sqlalchemy import ForeignKey, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class Enrollment(BaseModel):
    """
    Enrollment ledger record mapping student course registrations,
    completed progress telemetry, and checkout transactions.
    """
    __tablename__ = "enrollments"

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
    progress_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.00,
        nullable=False
    )
    is_paid: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    # Relationships
    student: Mapped["User"] = relationship("User")
    course: Mapped["Course"] = relationship("Course")
