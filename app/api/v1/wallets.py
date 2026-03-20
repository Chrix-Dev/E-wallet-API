from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.core.rate_limiter import rate_limit
from app.schemas.wallet import FundWalletRequest, WalletResponse
from app.schemas.transfer import TransferRequest, TransferResponse
from app.schemas.withdrawal import WithdrawalRequest, WithdrawalResponse
from app.services import wallet_service, transfer_service, withdrawal_service
from app.schemas.pin import SetPinRequest, ChangePinRequest
from app.services import pin_service

router = APIRouter(prefix="/wallets", tags=["Wallets"])


@router.get("/me", response_model=WalletResponse)
async def get_my_wallet(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    wallet = await wallet_service.get_wallet_with_cached_balance(current_user, db)
    return wallet

@router.post("/set-pin")
async def set_pin(
    data: SetPinRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await pin_service.set_pin(data, current_user, db)


@router.post("/change-pin")
async def change_pin(
    data: ChangePinRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await pin_service.change_pin(data, current_user, db)


@router.post("/fund")
async def fund_wallet(
    data: FundWalletRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await rate_limit(f"rate:fund:{current_user.id}", max_requests=5, window_seconds=60)
    return await wallet_service.initialize_funding(data.amount, current_user, db)


@router.post("/transfer", response_model=TransferResponse)
async def transfer(
    data: TransferRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await rate_limit(f"rate:transfer:{current_user.id}", max_requests=10, window_seconds=60)
    return await transfer_service.transfer_funds(data, idempotency_key, current_user, db)


@router.post("/withdraw", response_model=WithdrawalResponse)
async def withdraw(
    data: WithdrawalRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await rate_limit(f"rate:withdraw:{current_user.id}", max_requests=3, window_seconds=60)
    return await withdrawal_service.withdraw(data, idempotency_key, current_user, db)