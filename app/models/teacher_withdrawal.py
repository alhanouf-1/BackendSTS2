import uuid
import enum
from sqlalchemy import ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class WithdrawalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class TeacherWithdrawal(BaseModel):
    """
    Registry tracking outbound withdrawal requests and statuses.
    """
    __tablename__ = "teacher_withdrawals"

    teacher_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )
    status: Mapped[WithdrawalStatus] = mapped_column(
        SQLEnum(WithdrawalStatus),
        default=WithdrawalStatus.PENDING,
        nullable=False
    )

    # Relationships
    teacher: Mapped["User"] = relationship("User")
