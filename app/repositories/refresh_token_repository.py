import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository

class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository managing RefreshToken database transaction scopes."""
    def __init__(self, db: AsyncSession):
        super().__init__(RefreshToken, db)

    async def get_by_token(self, token: str) -> Optional[RefreshToken]:
        """Fetches active RefreshToken entity matching token string."""
        query = select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.is_deleted == False
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        """Revokes all active refresh tokens associated with a User (e.g. on compromised rotation detection)."""
        query = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False
            )
            .values(
                is_revoked=True,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await self.db.execute(query)

    async def delete_expired_tokens(self) -> int:
        """Permanently deletes expired refresh tokens from database storage."""
        now = datetime.now(timezone.utc)
        query = delete(RefreshToken).where(RefreshToken.expires_at < now)
        result = await self.db.execute(query)
        return result.rowcount
