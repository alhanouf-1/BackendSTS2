from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.faq import FAQ
from app.repositories.base import BaseRepository

class FAQRepository(BaseRepository[FAQ]):
    """Repository managing FAQ layout transaction scopes."""
    def __init__(self, db: AsyncSession):
        super().__init__(FAQ, db)

    async def get_by_lang(self, lang: str) -> List[FAQ]:
        """Fetches all active FAQ records matching language preferences."""
        query = select(FAQ).where(FAQ.lang == lang, FAQ.is_deleted == False)
        result = await self.db.execute(query)
        return list(result.scalars().all())
