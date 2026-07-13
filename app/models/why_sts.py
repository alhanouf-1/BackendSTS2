from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel

class WhySTS(BaseModel):
    """Marketing landing page localized value propositions database layout."""
    __tablename__ = "why_sts"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=False)
    lang: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
