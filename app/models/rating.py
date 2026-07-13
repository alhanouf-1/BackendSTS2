import uuid
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class Rating(BaseModel):
    """
    Enrolled student review star index (1-5 range) and academic reviews feedback.
    """
    __tablename__ = "ratings"

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
    rating_value: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(String(1024), nullable=False)

    # Relationships
    course: Mapped["Course"] = relationship("Course")
    student: Mapped["User"] = relationship("User")
