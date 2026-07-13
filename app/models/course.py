import uuid
from typing import List, Optional
from sqlalchemy import String, Numeric, Boolean, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel, GUID

class Course(BaseModel):
    """
    Master Course Table.
    Maps courses, instructor visibility, price limits, and average ratings.
    Applies MySQL FULLTEXT indexes on title and description columns.
    """
    __tablename__ = "courses"

    teacher_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    major: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(2048), nullable=False)
    
    # Store price as numeric/decimal
    price: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    
    # Teacher visibility privacy state flag
    teacher_profile_visibility: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    rating_avg: Mapped[float] = mapped_column(Numeric(3, 2), default=0.00, nullable=False)

    # Relationships
    teacher: Mapped["User"] = relationship("User")
    
    lessons: Mapped[List["Lesson"]] = relationship(
        "Lesson", 
        back_populates="course", 
        cascade="all, delete-orphan"
    )
    
    summaries: Mapped[List["Summary"]] = relationship(
        "Summary", 
        back_populates="course", 
        cascade="all, delete-orphan"
    )
    
    virtual_classes: Mapped[List["VirtualClass"]] = relationship(
        "VirtualClass", 
        back_populates="course", 
        cascade="all, delete-orphan"
    )
    
    ratings: Mapped[List["CourseRating"]] = relationship(
        "CourseRating", 
        back_populates="course", 
        cascade="all, delete-orphan"
    )
    
    enrollments: Mapped[List["CourseEnrollment"]] = relationship(
        "CourseEnrollment", 
        back_populates="course", 
        cascade="all, delete-orphan"
    )
    
    previews: Mapped[List["CoursePreview"]] = relationship(
        "CoursePreview", 
        back_populates="course", 
        cascade="all, delete-orphan"
    )

    # Table arguments adding the FULLTEXT indexes
    __table_args__ = (
        Index("idx_course_title_desc_fulltext", "title", "description", mysql_prefix="FULLTEXT"),
    )
v_user_relationship = relationship("Course", backref="courses")
