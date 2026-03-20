from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import hash_pin, verify_pin
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.pin import SetPinRequest, ChangePinRequest

MAX_PIN_ATTEMPTS = 3


async def set_pin(data: SetPinRequest, current_user: User, db: AsyncSession):
    result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    if wallet.transaction_pin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PIN already set. Use change PIN instead")

    wallet.transaction_pin = hash_pin(data.pin)
    wallet.pin_attempts = 0
    wallet.is_pin_locked = False
    await db.commit()

    return {"message": "Transaction PIN set successfully"}


async def change_pin(data: ChangePinRequest, current_user: User, db: AsyncSession):
    result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    if not wallet.transaction_pin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No PIN set. Use set PIN first")

    if wallet.is_pin_locked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wallet is locked due to too many wrong PIN attempts. Contact support")

    if not verify_pin(data.old_pin, wallet.transaction_pin):
        wallet.pin_attempts += 1
        if wallet.pin_attempts >= MAX_PIN_ATTEMPTS:
            wallet.is_pin_locked = True
            await db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Too many wrong attempts. Wallet has been locked")
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Wrong PIN. {MAX_PIN_ATTEMPTS - wallet.pin_attempts} attempts remaining")

    wallet.transaction_pin = hash_pin(data.new_pin)
    wallet.pin_attempts = 0
    await db.commit()

    return {"message": "PIN changed successfully"}


async def verify_transaction_pin(pin: str, wallet: Wallet, db: AsyncSession):
    if not wallet.transaction_pin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction PIN not set. Please set your PIN first")

    if wallet.is_pin_locked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wallet is locked due to too many wrong PIN attempts. Contact support")

    if not verify_pin(pin, wallet.transaction_pin):
        wallet.pin_attempts += 1
        if wallet.pin_attempts >= MAX_PIN_ATTEMPTS:
            wallet.is_pin_locked = True
            await db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Too many wrong attempts. Wallet has been locked")
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Wrong PIN. {MAX_PIN_ATTEMPTS - wallet.pin_attempts} attempts remaining"
        )

    # reset attempts if successful
    wallet.pin_attempts = 0
    await db.commit()