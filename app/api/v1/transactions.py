from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.models.transaction import TransactionType, TransactionStatus
from app.schemas.transaction import TransactionResponse, TransactionListResponse
from app.services import transaction_service, export_service

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/export/pdf")
async def export_transactions_pdf(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pdf_bytes = await export_service.generate_transaction_pdf(current_user, db)
    filename = f"statement_{current_user.full_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    tx_type: TransactionType | None = Query(default=None, alias="type"),
    tx_status: TransactionStatus | None = Query(default=None, alias="status"),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await transaction_service.get_transactions(
        current_user, db, tx_type, tx_status, start_date, end_date, page, page_size
    )


@router.get("/{reference}", response_model=TransactionResponse)
async def get_transaction(
    reference: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await transaction_service.get_transaction_by_reference(reference, current_user, db)