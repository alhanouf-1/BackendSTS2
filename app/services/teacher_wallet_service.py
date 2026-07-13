import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionType
from app.models.teacher_withdrawal import TeacherWithdrawal, WithdrawalStatus
from app.repositories.wallet_repository import WalletRepository
from app.repositories.transaction_repository import TransactionRepository

class TeacherWalletService:
    """Orchestrates secure ledger updates, balance inquiries, and withdrawal processing with database locks."""

    @staticmethod
    async def get_wallet_summary(db: AsyncSession, teacher_id: uuid.UUID) -> Dict[str, Any]:
        wallet_repo = WalletRepository(db)
        tx_repo = TransactionRepository(db)

        wallet = await wallet_repo.get_by_teacher_id(teacher_id)
        if not wallet:
            # Initialize empty wallet for new teachers
            wallet = Wallet(teacher_id=teacher_id, balance=0.00, version_number=1)
            await wallet_repo.create(wallet)
            await db.flush()

        transactions = await tx_repo.get_by_teacher_id(teacher_id)
        tx_list = []
        for tx in transactions:
            tx_list.append({
                "transaction_id": str(tx.id),
                "amount": float(tx.amount),
                "type": tx.type.value,
                "created_at": tx.created_at.isoformat()
            })

        return {
            "balance": float(wallet.balance),
            "transactions": tx_list
        }

    @staticmethod
    async def request_withdrawal(
        db: AsyncSession,
        teacher_id: uuid.UUID,
        amount: float
    ) -> TeacherWithdrawal:
        # 1. Enforce minimum barrier limit (amount >= 50 SAR)
        if amount < 50.00:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Minimum withdrawal amount is 50 SAR."
            )

        wallet_repo = WalletRepository(db)

        # 2. Acquire database-level pessimistic lock to prevent double-spending
        wallet = await wallet_repo.get_by_teacher_id_for_update(teacher_id)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet registry not found for teacher account."
            )

        # 3. Enforce structural solvency
        if amount > float(wallet.balance):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Solvency limit breached. Insufficient wallet balance."
            )

        # 4. Atomically adjust balance
        wallet.balance = float(wallet.balance) - amount
        # Increment version for optimistic checking consistency
        wallet.version_number += 1
        db.add(wallet)

        # 5. Log double-entry transaction record
        transaction = Transaction(
            teacher_id=teacher_id,
            amount=amount,
            type=TransactionType.WITHDRAWAL
        )
        db.add(transaction)

        # 6. Log outbound withdrawal tracking record
        withdrawal = TeacherWithdrawal(
            teacher_id=teacher_id,
            amount=amount,
            status=WithdrawalStatus.PENDING
        )
        db.add(withdrawal)

        await db.flush()
        return withdrawal
