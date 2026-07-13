import uuid
import enum
from sqlalchemy import String, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class AttachmentType(str, enum.Enum):
    IMAGE = "IMAGE"
    PDF = "PDF"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    NONE = "NONE"

class ChatMessage(BaseModel):
    """
    Historical logs for course/session chat messages, supporting text and attachment streams.
    """
    __tablename__ = "chat_messages"

    sender_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("virtual_sessions.id", ondelete="CASCADE"),
        nullable=True
    )
    message_text: Mapped[str] = mapped_column(String(2048), nullable=True)
    attachment_url: Mapped[str] = mapped_column(String(512), nullable=True)
    attachment_type: Mapped[AttachmentType] = mapped_column(
        SQLEnum(AttachmentType),
        default=AttachmentType.NONE,
        nullable=False
    )

    # Relationships
    sender: Mapped["User"] = relationship("User")
    course: Mapped["Course"] = relationship("Course")
    session: Mapped["VirtualSession"] = relationship("VirtualSession")
