from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.hero_content import HeroContent
from app.repositories.base import BaseRepository

class HeroRepository(BaseRepository[HeroContent]):
    """Repository managing Hero layout transaction scopes."""
    def __init__(self, db: AsyncSession):
        super().__init__(HeroContent, db)

    async def get_by_lang(self, lang: str) -> Optional[HeroContent]:
        """Fetches the Hero content configuration matching the language tag."""
        query = select(HeroContent).where(HeroContent.lang == lang, HeroContent.is_deleted == False)
        result = await self.db.execute(query)
        return result.scalars().first()
