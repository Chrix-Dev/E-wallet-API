import hashlib
import hmac
import json
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionStatus
from app.services.wallet_service import invalidate_balance_cache
from app.services.email_service import (
    send_funding_email,
    send_withdrawal_success_email,
    send_withdrawal_failed_email,
)


def verify_paystack_signature(payload: bytes, signature: str) -> bool:
    computed = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
        payload,
        hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


async def handle_paystack_event(payload: bytes, signature: str, db: AsyncSession):
    if not verify_paystack_signature(payload, signature):
        return {"status": "invalid signature"}

    event = json.loads(payload)
    event_type = event.get("event")
    data = event["data"]

    if event_type == "charge.success":
        await handle_charge_success(data, db)
    elif event_type == "transfer.success":
        await handle_transfer_success(data, db)
    elif event_type in ("transfer.failed", "transfer.reversed"):
        await handle_transfer_failed(data, db)

    return {"status": "ok"}


async def handle_charge_success(data: dict, db: AsyncSession):
    reference = data["reference"]
    amount_paid = Decimal(data["amount"]) / 100

    result = await db.execute(select(Transaction).where(Transaction.reference == reference))
    transaction = result.scalar_one_or_none()

    if not transaction or transaction.status == TransactionStatus.SUCCESS:
        return

    wallet_result = await db.execute(select(Wallet).where(Wallet.id == transaction.receiver_wallet_id))
    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        return

    wallet.balance += amount_paid
    transaction.status = TransactionStatus.SUCCESS
    transaction.metadata_ = data
    await db.commit()
    await invalidate_balance_cache(str(wallet.id))

    # notify user
    user_result = await db.execute(select(User).where(User.id == wallet.user_id))
    user = user_result.scalar_one_or_none()
    if user:
        await send_funding_email(
            to_email=user.email,
            full_name=user.full_name,
            amount=f"{amount_paid:,.2f}",
            balance=f"{wallet.balance:,.2f}",
            reference=reference,
        )


async def handle_transfer_success(data: dict, db: AsyncSession):
    reference = data["reference"]

    result = await db.execute(select(Transaction).where(Transaction.reference == reference))
    transaction = result.scalar_one_or_none()

    if not transaction:
        return

    wallet_result = await db.execute(select(Wallet).where(Wallet.id == transaction.sender_wallet_id))
    wallet = wallet_result.scalar_one_or_none()

    transaction.status = TransactionStatus.SUCCESS
    transaction.metadata_ = data
    await db.commit()

    # notify user
    if wallet:
        user_result = await db.execute(select(User).where(User.id == wallet.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            await send_withdrawal_success_email(
                to_email=user.email,
                full_name=user.full_name,
                amount=f"{transaction.amount:,.2f}",
                reference=reference,
                balance=f"{wallet.balance:,.2f}",
            )


async def handle_transfer_failed(data: dict, db: AsyncSession):
    reference = data["reference"]

    result = await db.execute(select(Transaction).where(Transaction.reference == reference))
    transaction = result.scalar_one_or_none()

    if not transaction or transaction.status == TransactionStatus.FAILED:
        return

    wallet_result = await db.execute(select(Wallet).where(Wallet.id == transaction.sender_wallet_id))
    wallet = wallet_result.scalar_one_or_none()

    if wallet:
        wallet.balance += transaction.amount

    transaction.status = TransactionStatus.FAILED
    transaction.metadata_ = data
    await db.commit()

    if wallet:
        await invalidate_balance_cache(str(wallet.id))
        user_result = await db.execute(select(User).where(User.id == wallet.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            await send_withdrawal_failed_email(
                to_email=user.email,
                full_name=user.full_name,
                amount=f"{transaction.amount:,.2f}",
                reference=reference,
                balance=f"{wallet.balance:,.2f}",
            )