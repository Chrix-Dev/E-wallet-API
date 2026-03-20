from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.dependencies import get_db, get_current_admin
from app.models.transaction import Transaction, TransactionType, TransactionStatus
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    return await admin_service.get_dashboard_stats(db)


@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tier: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    return await admin_service.get_all_users(db, page, page_size, tier, is_active)


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    return await admin_service.get_user_detail(user_id, db)


@router.patch("/users/{user_id}/toggle")
async def toggle_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    return await admin_service.toggle_user_status(user_id, db)


@router.get("/transactions")
async def list_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    tx_type: TransactionType | None = Query(default=None, alias="type"),
    tx_status: TransactionStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    return await admin_service.get_all_transactions(db, page, page_size, tx_type, tx_status)


@router.get("/transactions/{reference}")
async def get_transaction(
    reference: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    result = await db.execute(select(Transaction).where(Transaction.reference == reference))
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    return transaction

@router.patch("/users/{user_id}/unlock-pin")
async def unlock_pin(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_admin)
):
    return await admin_service.unlock_user_pin(user_id, db)