import hashlib
import hmac
import json
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionStatus
from app.services.wallet_service import invalidate_balance_cache


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

    elif event_type == "transfer.failed" or event_type == "transfer.reversed":
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


async def handle_transfer_success(data: dict, db: AsyncSession):
    reference = data["reference"]

    result = await db.execute(select(Transaction).where(Transaction.reference == reference))
    transaction = result.scalar_one_or_none()

    if not transaction:
        return

    transaction.status = TransactionStatus.SUCCESS
    transaction.metadata_ = data
    await db.commit()


async def handle_transfer_failed(data: dict, db: AsyncSession):
    reference = data["reference"]

    result = await db.execute(select(Transaction).where(Transaction.reference == reference))
    transaction = result.scalar_one_or_none()

    if not transaction or transaction.status == TransactionStatus.FAILED:
        return

    # reverse the debit — give the user their money back
    wallet_result = await db.execute(select(Wallet).where(Wallet.id == transaction.sender_wallet_id))
    wallet = wallet_result.scalar_one_or_none()

    if wallet:
        wallet.balance += transaction.amount

    transaction.status = TransactionStatus.FAILED
    transaction.metadata_ = data
    await db.commit()
    if wallet:
        await invalidate_balance_cache(str(wallet.id))