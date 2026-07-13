import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.bookmarks import Bookmark
from app.repositories.base import BaseRepository

class BookmarkRepository(BaseRepository[Bookmark]):
    """Repository managing Course/Lesson/Summary Bookmarks database transactions."""
    def __init__(self, db: AsyncSession):
        super().__init__(Bookmark, db)

    async def get_student_bookmarks(self, student_id: uuid.UUID) -> List[Bookmark]:
        """Gets all active bookmarks saved by a student."""
        query = select(Bookmark).where(
            Bookmark.student_id == student_id,
            Bookmark.is_deleted == False
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_student_and_type_ids(
        self,
        student_id: uuid.UUID,
        bookmark_type: str,
        course_id: Optional[uuid.UUID] = None,
        lesson_id: Optional[uuid.UUID] = None,
        summary_id: Optional[uuid.UUID] = None
    ) -> Optional[Bookmark]:
        """Checks if a matching bookmark configuration exists for the user."""
        query = select(Bookmark).where(
            Bookmark.student_id == student_id,
            Bookmark.bookmark_type == bookmark_type,
            Bookmark.is_deleted == False
        )
        if course_id:
            query = query.where(Bookmark.course_id == course_id)
        if lesson_id:
            query = query.where(Bookmark.lesson_id == lesson_id)
        if summary_id:
            query = query.where(Bookmark.summary_id == summary_id)
            
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
