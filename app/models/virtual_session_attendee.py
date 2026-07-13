import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class VirtualSessionAttendee(BaseModel):
    """
    Registry tracking seat reservations in virtual live sessions.
    """
    __tablename__ = "virtual_session_attendees"

    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("virtual_sessions.id", ondelete="CASCADE"),
        nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    reserved_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    session: Mapped["VirtualSession"] = relationship("VirtualSession", back_populates="attendees")
    student: Mapped["User"] = relationship("User")
