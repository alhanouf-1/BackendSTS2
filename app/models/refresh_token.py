import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class RefreshToken(BaseModel):
    """Refresh Tokens Ledger for Rotation support."""
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    token: Mapped[str] = mapped_column(
        String(512), 
        unique=True, 
        index=True, 
        nullable=False
    )
    
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False
    )
    
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False
    )
    
    rotated_from_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
    
    rotated_from: Mapped[Optional["RefreshToken"]] = relationship(
        "RefreshToken",
        remote_side="RefreshToken.id",
        back_populates="rotated_to"
    )
    
    rotated_to: Mapped[Optional["RefreshToken"]] = relationship(
        "RefreshToken",
        remote_side="RefreshToken.rotated_from_id",
        back_populates="rotated_from",
        uselist=False
    )
    
RefreshToken.rotated_to = relationship(
    "RefreshToken",
    remote_side=[RefreshToken.rotated_from_id],
    back_populates="rotated_from",
    uselist=False,
    post_update=True
)
RefreshToken.rotated_from = relationship(
    "RefreshToken",
    remote_side=[RefreshToken.id],
    back_populates="rotated_to"
)
