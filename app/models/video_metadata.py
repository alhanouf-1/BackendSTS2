import uuid
import enum
from sqlalchemy import String, Integer, BigInteger, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class EncodingStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class VideoMetadata(BaseModel):
    """
    Detailed video properties parsed from media uploads.
    """
    __tablename__ = "video_metadata"

    lesson_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolution: Mapped[str] = mapped_column(String(50), default="Unknown", nullable=False)
    thumbnail_path: Mapped[str] = mapped_column(String(512), nullable=True)
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    encoding_status: Mapped[EncodingStatus] = mapped_column(
        SQLEnum(EncodingStatus),
        default=EncodingStatus.PENDING,
        nullable=False
    )

    # Relationships
    lesson: Mapped["Lesson"] = relationship("Lesson")
