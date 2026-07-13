import enum
from typing import Dict, Any, Optional, List
from sqlalchemy import String, Enum as SQLEnum, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel

class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    TEACHER = "TEACHER"
    VERIFIED_TEACHER = "VERIFIED_TEACHER"
    ADMIN = "ADMIN"

class User(BaseModel):
    """Users Master Table."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True, 
        nullable=False
    )
    
    password_hash: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole), 
        default=UserRole.STUDENT, 
        nullable=False
    )
    
    is_verified: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False
    )

    # Preferences JSON column (e.g., {"theme": "light/dark", "lang": "ar/en"})
    preferences: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, 
        default=lambda: {"theme": "light", "lang": "en"}, 
        nullable=True
    )

    # Relationships
    verification: Mapped[Optional["TeacherVerification"]] = relationship(
        "TeacherVerification",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )
