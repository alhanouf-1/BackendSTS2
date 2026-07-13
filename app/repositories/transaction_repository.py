import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction
from app.repositories.base import BaseRepository

class TransactionRepository(BaseRepository[Transaction]):
    """Repository managing double-entry Transaction database history logs."""
    def __init__(self, db: AsyncSession):
        super().__init__(Transaction, db)

    async def get_by_teacher_id(self, teacher_id: uuid.UUID, limit: int = 50) -> List[Transaction]:
        """Fetches double-entry ledger transactions for a teacher."""
        query = (
            select(Transaction)
            .where(
                Transaction.teacher_id == teacher_id,
                Transaction.is_deleted == False
            )
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
