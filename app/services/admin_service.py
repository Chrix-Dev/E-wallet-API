from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from fastapi import HTTPException, status

from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionStatus


async def get_all_users(db: AsyncSession, page: int, page_size: int, tier: str | None, is_active: bool | None):
    query = select(User)

    if tier:
        query = query.where(User.tier == tier)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(query.order_by(User.created_at.desc()).offset(offset).limit(page_size))
    users = result.scalars().all()

    return {"total": total, "page": page, "page_size": page_size, "users": users}


async def get_user_detail(user_id: str, db: AsyncSession):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = wallet_result.scalar_one_or_none()

    return {"user": user, "wallet": wallet}


async def toggle_user_status(user_id: str, db: AsyncSession):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.is_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate an admin account")

    user.is_active = not user.is_active
    await db.commit()

    status_str = "activated" if user.is_active else "deactivated"
    return {"message": f"User {status_str} successfully", "is_active": user.is_active}


async def get_all_transactions(
    db: AsyncSession,
    page: int,
    page_size: int,
    tx_type: str | None,
    tx_status: str | None
):
    query = select(Transaction)

    if tx_type:
        query = query.where(Transaction.type == tx_type)

    if tx_status:
        query = query.where(Transaction.status == tx_status)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    offset = (page - 1) * page_size
    result = await db.execute(query.order_by(Transaction.created_at.desc()).offset(offset).limit(page_size))
    transactions = result.scalars().all()

    return {"total": total, "page": page, "page_size": page_size, "transactions": transactions}


async def get_dashboard_stats(db: AsyncSession):
    total_users = await db.execute(select(func.count()).select_from(User))
    total_transactions = await db.execute(select(func.count()).select_from(Transaction))
    successful_transactions = await db.execute(
        select(func.count()).select_from(Transaction).where(Transaction.status == TransactionStatus.SUCCESS)
    )
    total_volume = await db.execute(
        select(func.sum(Transaction.amount)).where(Transaction.status == TransactionStatus.SUCCESS)
    )

    return {
        "total_users": total_users.scalar(),
        "total_transactions": total_transactions.scalar(),
        "successful_transactions": successful_transactions.scalar(),
        "total_volume": str(total_volume.scalar() or 0),
    }

async def unlock_user_pin(user_id: str, db: AsyncSession):
    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == user_id))
    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    wallet.is_pin_locked = False
    wallet.pin_attempts = 0
    await db.commit()

    return {"message": "Wallet PIN unlocked successfully"}