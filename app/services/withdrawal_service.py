import uuid
from decimal import Decimal

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.limits import get_limits
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.schemas.withdrawal import WithdrawalRequest
from app.services.wallet_service import invalidate_balance_cache
from datetime import datetime, timezone, date
from app.services.pin_service import verify_transaction_pin


async def create_transfer_recipient(bank_code: str, account_number: str, name: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.paystack.co/transferrecipient",
            json={
                "type": "nuban",
                "name": name,
                "account_number": account_number,
                "bank_code": bank_code,
                "currency": "NGN",
            },
            headers={
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            }
        )

    if response.status_code != 201:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Could not verify bank account")

    return response.json()["data"]["recipient_code"]


async def initiate_paystack_transfer(amount: Decimal, recipient_code: str, reference: str, narration: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.paystack.co/transfer",
            json={
                "source": "balance",
                "amount": int(amount * 100),  # kobo
                "recipient": recipient_code,
                "reference": reference,
                "reason": narration,
            },
            headers={
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            }
        )

    return response.json()


async def withdraw(data: WithdrawalRequest, idempotency_key: str, current_user: User, db: AsyncSession):
    if not current_user.is_verified:
        raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Please verify your email before making transactions"
    )

    if data.amount <= Decimal("0"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than zero")
    

    # get wallet
    result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = result.scalar_one_or_none()

    if not wallet or not wallet.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet not found or inactive")
    
    # Verify transaction PIN
    await verify_transaction_pin(data.pin, wallet, db)
    
     # check and reset daily limit if needed
    if wallet.last_daily_reset is None or wallet.last_daily_reset.date() < date.today():
       wallet.daily_withdrawal_used = Decimal("0.00")
       wallet.last_daily_reset = datetime.now(timezone.utc)

    limits = get_limits(current_user.tier)

    if data.amount < limits["min_transaction"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Minimum transaction amount is ₦{limits['min_transaction']}")

    if data.amount > limits["max_single_withdrawal"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Maximum single withdrawal for your tier is ₦{limits['max_single_withdrawal']}")

    if wallet.daily_withdrawal_used + data.amount > limits["max_daily_withdrawal"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Daily withdrawal limit of ₦{limits['max_daily_withdrawal']} exceeded")

    if wallet.balance < data.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")

    reference = str(uuid.uuid4()).replace("-", "")[:20]

    # debit wallet immediately and save a pending transaction
    wallet.balance -= data.amount
    wallet.daily_withdrawal_used += data.amount

    transaction = Transaction(
        reference=reference,
        type=TransactionType.DEBIT,
        status=TransactionStatus.PENDING,
        amount=data.amount,
        sender_wallet_id=wallet.id,
        narration=data.narration or f"Withdrawal to {data.account_number}",
        metadata_={
            "bank_code": data.bank_code,
            "account_number": data.account_number,
            "idempotency_key": idempotency_key,
        }
    )
    db.add(transaction)
    await db.commit()
    await invalidate_balance_cache(str(wallet.id))

    # create recipient and initiate transfer with Paystack
    try:
        recipient_code = await create_transfer_recipient(
            data.bank_code, data.account_number, current_user.full_name
        )
        transfer_response = await initiate_paystack_transfer(
            data.amount, recipient_code, reference, transaction.narration
        )

        if transfer_response.get("status") is False:
            raise Exception(transfer_response.get("message", "Transfer initiation failed"))

    except Exception:
        # if Paystack call fails, reverse the debit so user isn't left short
        wallet.balance += data.amount
        transaction.status = TransactionStatus.FAILED
        await db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Withdrawal failed, your balance has been reversed")

    return {
        "reference": reference,
        "amount": data.amount,
        "status": "pending",
        "narration": transaction.narration,
    }