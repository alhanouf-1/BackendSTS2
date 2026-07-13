from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import BaseModel

class Testimonial(BaseModel):
    """Public testimonials layout representing localized user review ratings."""
    __tablename__ = "testimonials"

    author: Mapped[str] = mapped_column(String(255), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    comment: Mapped[str] = mapped_column(String(1024), nullable=False)
    lang: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
