import uuid
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class CourseRating(BaseModel):
    """Enrolled student course rating scores and comment reviews."""
    __tablename__ = "course_ratings"

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
    
    rating_value: Mapped[int] = mapped_column(Integer, nullable=False)  # Constraint check 1 to 5 handled in validators
    comment: Mapped[str] = mapped_column(String(1024), nullable=False)

    # Relationships
    course: Mapped["Course"] = relationship("Course", back_populates="ratings")
    student: Mapped["User"] = relationship("User")
