import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class SessionStatus(str, enum.Enum):
    UPCOMING = "UPCOMING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"

class VirtualSession(BaseModel):
    """
    Scheduled WebRTC live streaming session scheduling metadata.
    """
    __tablename__ = "virtual_sessions"

    course_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    meeting_room_id: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus),
        default=SessionStatus.UPCOMING,
        nullable=False
    )

    # Relationships
    course: Mapped["Course"] = relationship("Course")
    attendees: Mapped[list["VirtualSessionAttendee"]] = relationship(
        "VirtualSessionAttendee",
        back_populates="session",
        cascade="all, delete-orphan"
    )
