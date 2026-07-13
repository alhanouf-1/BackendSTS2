from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    """Repository managing User database transaction scopes."""
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str, include_deleted: bool = False) -> Optional[User]:
        """Fetches a single active user by their email address."""
        query = select(User).where(User.email == email)
        if not include_deleted:
            query = query.where(User.is_deleted == False)
            
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
