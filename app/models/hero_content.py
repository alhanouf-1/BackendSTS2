from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel

class HeroContent(BaseModel):
    """Marketing landing page localized Hero text content database layout."""
    __tablename__ = "hero_content"

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(1024), nullable=False)
    lang: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
