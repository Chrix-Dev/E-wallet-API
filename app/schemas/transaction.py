from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
from uuid import UUID

from app.models.transaction import TransactionType, TransactionStatus


class TransactionResponse(BaseModel):
    id: UUID
    reference: str
    type: TransactionType
    status: TransactionStatus
    amount: Decimal
    fee: Decimal
    narration: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    transactions: list[TransactionResponse]