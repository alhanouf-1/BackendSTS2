import uuid
import enum
from datetime import date
from sqlalchemy import ForeignKey, Integer, Numeric, Date, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class AnalyticsPeriod(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"

class TeacherAnalytics(BaseModel):
    """
    Pre-calculated cache performance metrics for teacher dashboard analytics.
    """
    __tablename__ = "teacher_analytics"

    teacher_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True
    )
    total_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_students: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_earnings: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False
    )
    avg_rating: Mapped[float] = mapped_column(
        Numeric(3, 2),
        default=0.00,
        nullable=False
    )
    completion_rate: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.00,
        nullable=False
    )
    period: Mapped[AnalyticsPeriod] = mapped_column(
        SQLEnum(AnalyticsPeriod),
        default=AnalyticsPeriod.DAILY,
        nullable=False
    )
    recorded_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Relationships
    teacher: Mapped["User"] = relationship("User")
    course: Mapped["Course"] = relationship("Course")
