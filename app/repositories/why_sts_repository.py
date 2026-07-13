from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.why_sts import WhySTS
from app.repositories.base import BaseRepository

class WhySTSRepository(BaseRepository[WhySTS]):
    """Repository managing WhySTS layout transaction scopes."""
    def __init__(self, db: AsyncSession):
        super().__init__(WhySTS, db)

    async def get_by_lang(self, lang: str) -> List[WhySTS]:
        """Fetches WhySTS value propositions matching the language tag."""
        query = select(WhySTS).where(WhySTS.lang == lang, WhySTS.is_deleted == False)
        result = await self.db.execute(query)
        return list(result.scalars().all())
