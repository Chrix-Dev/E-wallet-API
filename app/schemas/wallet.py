from decimal import Decimal
from pydantic import BaseModel
from uuid import UUID


class FundWalletRequest(BaseModel):
    amount: Decimal  # amount in naira, we convert to kobo when calling Paystack


class WalletResponse(BaseModel):
    id: UUID
    account_number: str
    balance: Decimal
    currency: str
    is_active: bool

    class Config:
        from_attributes = True