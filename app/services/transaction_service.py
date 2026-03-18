from datetime import datetime
from sqlalchemy import or_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionType, TransactionStatus


async def get_transactions(
    current_user: User,
    db: AsyncSession,
    tx_type: TransactionType | None,
    tx_status: TransactionStatus | None,
    start_date: datetime | None,
    end_date: datetime | None,
    page: int,
    page_size: int,
):
    # get the user's wallet first
    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    # base query — fetch transactions where user is either sender or receiver
    base_query = select(Transaction).where(
        or_(
            Transaction.sender_wallet_id == wallet.id,
            Transaction.receiver_wallet_id == wallet.id,
        )
    )

    # apply filters only if they were actually passed in
    if tx_type:
        base_query = base_query.where(Transaction.type == tx_type)

    if tx_status:
        base_query = base_query.where(Transaction.status == tx_status)

    if start_date:
        base_query = base_query.where(Transaction.created_at >= start_date)

    if end_date:
        base_query = base_query.where(Transaction.created_at <= end_date)

    # get total count for pagination metadata
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # apply ordering and pagination
    offset = (page - 1) * page_size
    paginated_query = base_query.order_by(Transaction.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(paginated_query)
    transactions = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "transactions": transactions,
    }


async def get_transaction_by_reference(reference: str, current_user: User, db: AsyncSession):
    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    result = await db.execute(
        select(Transaction).where(
            Transaction.reference == reference,
            or_(
                Transaction.sender_wallet_id == wallet.id,
                Transaction.receiver_wallet_id == wallet.id,
            )
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    return transaction