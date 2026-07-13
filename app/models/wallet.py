import uuid
from sqlalchemy import ForeignKey, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class Wallet(BaseModel):
    """
    Teacher balance wallet tracking earnings, withdrawals, and locks.
    Supports Optimistic Locking through version_number.
    """
    __tablename__ = "wallets"

    teacher_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )
    balance: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0.00,
        nullable=False
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    # Relationships
    teacher: Mapped["User"] = relationship("User")
