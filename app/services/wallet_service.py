import httpx
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.redis import redis_client
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.user import User

BALANCE_CACHE_TTL = 60  # seconds


def balance_cache_key(wallet_id: str) -> str:
    return f"wallet:balance:{wallet_id}"


async def get_wallet(user: User, db: AsyncSession):
    result = await db.execute(select(Wallet).where(Wallet.user_id == user.id))
    wallet = result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    return wallet


async def get_wallet_with_cached_balance(user: User, db: AsyncSession):
    wallet = await get_wallet(user, db)

    # check Redis for cached balance first
    cached = await redis_client.get(balance_cache_key(str(wallet.id)))

    if cached is not None:
        wallet.balance = Decimal(cached)
    else:
        # cache miss — store current balance in Redis
        await redis_client.setex(balance_cache_key(str(wallet.id)), BALANCE_CACHE_TTL, str(wallet.balance))

    return wallet


async def invalidate_balance_cache(wallet_id: str):
    await redis_client.delete(balance_cache_key(wallet_id))


async def initialize_funding(amount: Decimal, user: User, db: AsyncSession):
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before making transactions"
        )
    wallet = await get_wallet(user, db)

    if not wallet.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet is not active")

    amount_in_kobo = int(amount * 100)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.paystack.co/transaction/initialize",
            json={
                "email": user.email,
                "amount": amount_in_kobo,
            },
            headers={
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            }
        )

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to initialize payment")

    data = response.json()
    payment_data = data["data"]

    transaction = Transaction(
        reference=payment_data["reference"],
        type=TransactionType.CREDIT,
        status=TransactionStatus.PENDING,
        amount=amount,
        receiver_wallet_id=wallet.id,
        narration="Wallet funding via Paystack",
    )
    db.add(transaction)
    await db.commit()

    return {
        "payment_url": payment_data["authorization_url"],
        "reference": payment_data["reference"],
    }