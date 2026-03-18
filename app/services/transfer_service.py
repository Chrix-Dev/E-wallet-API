import json
import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.models.idempotency import IdempotencyKey
from app.schemas.transfer import TransferRequest
from app.services.wallet_service import invalidate_balance_cache


async def transfer_funds(
    data: TransferRequest,
    idempotency_key: str,
    current_user: User,
    db: AsyncSession
):
    # check if we've seen this idempotency key before
    existing = await db.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.key == idempotency_key,
            IdempotencyKey.user_id == current_user.id
        )
    )
    existing_key = existing.scalar_one_or_none()

    if existing_key:
        # request already processed, return the saved response
        return json.loads(existing_key.response_snapshot)

    # can't transfer to yourself
    if data.receiver_email and data.receiver_email == current_user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't transfer to yourself")

    if not data.receiver_email and not data.receiver_account_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide receiver email or account number")

    if data.amount <= Decimal("0"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be greater than zero")

    # get sender wallet
    sender_result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    sender_wallet = sender_result.scalar_one_or_none()

    if not sender_wallet or not sender_wallet.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sender wallet not found or inactive")

    if sender_wallet.balance < data.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance")

    # look up receiver by account number or email
    if data.receiver_account_number:
        receiver_wallet_result = await db.execute(
            select(Wallet).where(Wallet.account_number == data.receiver_account_number)
        )
        receiver_wallet = receiver_wallet_result.scalar_one_or_none()

        if not receiver_wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account number not found")

        receiver_result = await db.execute(select(User).where(User.id == receiver_wallet.user_id))
        receiver = receiver_result.scalar_one_or_none()
    else:
        receiver_result = await db.execute(select(User).where(User.email == data.receiver_email))
        receiver = receiver_result.scalar_one_or_none()

        if not receiver:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receiver not found")

        receiver_wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == receiver.id))
        receiver_wallet = receiver_wallet_result.scalar_one_or_none()

    # self transfer check for account number path
    if receiver_wallet.id == sender_wallet.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't transfer to yourself")

    if not receiver_wallet or not receiver_wallet.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Receiver wallet not found or inactive")

    # --- atomic transfer ---
    # both balance updates and the transaction record happen together
    # if anything fails after this point, the entire block rolls back
    reference = str(uuid.uuid4()).replace("-", "")[:20]

    sender_wallet.balance -= data.amount
    receiver_wallet.balance += data.amount

    transaction = Transaction(
        reference=reference,
        type=TransactionType.TRANSFER,
        status=TransactionStatus.SUCCESS,
        amount=data.amount,
        sender_wallet_id=sender_wallet.id,
        receiver_wallet_id=receiver_wallet.id,
        narration=data.narration or f"Transfer to {receiver.email}",
    )
    db.add(transaction)

    # build response before committing so we can snapshot it
    response = {
        "reference": reference,
        "amount": str(data.amount),
        "receiver": receiver.email,
        "narration": transaction.narration,
        "status": "success"
    }

    # save idempotency key with the response snapshot
    idem_key = IdempotencyKey(
        key=idempotency_key,
        user_id=current_user.id,
        response_snapshot=json.dumps(response)
    )
    db.add(idem_key)

    await db.commit()
    await invalidate_balance_cache(str(sender_wallet.id))
    await invalidate_balance_cache(str(receiver_wallet.id))
    return response