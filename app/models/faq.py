from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel

class FAQ(BaseModel):
    """Public localized FAQs database layout."""
    __tablename__ = "faqs"

    question: Mapped[str] = mapped_column(String(512), nullable=False)
    answer: Mapped[str] = mapped_column(String(1024), nullable=False)
    lang: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
