import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.course import Course
from app.models.user import User
from app.repositories.base import BaseRepository

class CourseRepository(BaseRepository[Course]):
    """Repository managing Course database transaction scopes and search compilation."""
    def __init__(self, db: AsyncSession):
        super().__init__(Course, db)

    async def search_courses(
        self,
        q: Optional[str] = None,
        university: Optional[str] = None,
        code: Optional[str] = None,
        major: Optional[str] = None,
        rating_min: Optional[float] = None,
        teacher_name: Optional[str] = None,
        price_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Course], int]:
        """
        Runs composite search filtering queries utilizing MySQL FULLTEXT index matching.
        Returns a tuple of matched course list and total count.
        """
        # Enforce soft-delete filter
        query = select(Course).where(Course.is_deleted == False)

        # Full-text search matching on q (MySQL MATCH AGAINST in BOOLEAN MODE, with LIKE fallback)
        if q:
            dialect_name = "mysql"
            try:
                if self.db.bind:
                    dialect_name = self.db.bind.dialect.name
            except Exception:
                pass

            if dialect_name in ("mysql", "mariadb"):
                # Bind search query parameter to protect against injection
                query = query.where(
                    text("MATCH(title, description) AGAINST(:search_query IN BOOLEAN MODE)")
                ).params(search_query=f"{q}*")
            else:
                query = query.where(
                    Course.title.ilike(f"%{q}%") |
                    Course.description.ilike(f"%{q}%")
                )

        # Join teacher table if filtering by teacher name
        if teacher_name:
            query = query.join(Course.teacher).where(
                User.email.ilike(f"%{teacher_name}%")
            )

        if university:
            # Check university search string in course titles, code, or description fields
            query = query.where(
                Course.title.ilike(f"%{university}%") |
                Course.description.ilike(f"%{university}%") |
                Course.code.ilike(f"%{university}%")
            )

        if code:
            query = query.where(Course.code.ilike(f"%{code}%"))

        if major:
            query = query.where(Course.major.ilike(f"%{major}%"))

        if rating_min is not None:
            query = query.where(Course.rating_avg >= rating_min)

        if price_type:
            if price_type.lower() == "free":
                query = query.where(Course.price == 0.0)
            elif price_type.lower() == "paid":
                query = query.where(Course.price > 0.0)

        # Execute total count subquery
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Pagination & Eager-loading of relationship structures
        query = query.offset(skip).limit(limit).options(selectinload(Course.teacher))
        result = await self.db.execute(query)
        courses = list(result.scalars().all())

        return courses, total

    async def get_course_details(self, course_id: uuid.UUID) -> Optional[Course]:
        """Fetches a single active course details profile with relationship structures loaded."""
        query = (
            select(Course)
            .where(Course.id == course_id, Course.is_deleted == False)
            .options(
                selectinload(Course.teacher),
                selectinload(Course.lessons),
                selectinload(Course.summaries),
                selectinload(Course.virtual_classes)
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
