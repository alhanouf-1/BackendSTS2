import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.video_metadata import VideoMetadata
from app.repositories.base import BaseRepository

class VideoMetadataRepository(BaseRepository[VideoMetadata]):
    """Repository managing VideoMetadata records."""
    def __init__(self, db: AsyncSession):
        super().__init__(VideoMetadata, db)

    async def get_by_lesson_id(self, lesson_id: uuid.UUID) -> Optional[VideoMetadata]:
        """Fetches active video metadata details mapped to a lesson ID."""
        query = select(VideoMetadata).where(
            VideoMetadata.lesson_id == lesson_id,
            VideoMetadata.is_deleted == False
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
