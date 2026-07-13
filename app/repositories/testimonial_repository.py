from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.testimonial import Testimonial
from app.repositories.base import BaseRepository

class TestimonialRepository(BaseRepository[Testimonial]):
    """Repository managing Testimonial layout transaction scopes."""
    def __init__(self, db: AsyncSession):
        super().__init__(Testimonial, db)

    async def get_by_lang(self, lang: str) -> List[Testimonial]:
        """Fetches testimonials matching user language preferences."""
        query = select(Testimonial).where(Testimonial.lang == lang, Testimonial.is_deleted == False)
        result = await self.db.execute(query)
        return list(result.scalars().all())
