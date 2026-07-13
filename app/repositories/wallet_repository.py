import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.wallet import Wallet
from app.repositories.base import BaseRepository

class WalletRepository(BaseRepository[Wallet]):
    """Repository managing Wallet database states and pessimistic update locks."""
    def __init__(self, db: AsyncSession):
        super().__init__(Wallet, db)

    async def get_by_teacher_id(self, teacher_id: uuid.UUID) -> Optional[Wallet]:
        """Fetches active wallet details associated with a teacher."""
        query = select(Wallet).where(
            Wallet.teacher_id == teacher_id,
            Wallet.is_deleted == False
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_teacher_id_for_update(self, teacher_id: uuid.UUID) -> Optional[Wallet]:
        """Locks and fetches the teacher's wallet record using SELECT FOR UPDATE."""
        query = (
            select(Wallet)
            .where(
                Wallet.teacher_id == teacher_id,
                Wallet.is_deleted == False
            )
            .with_for_update()
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
