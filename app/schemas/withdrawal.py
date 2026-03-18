from decimal import Decimal
from pydantic import BaseModel


class WithdrawalRequest(BaseModel):
    amount: Decimal
    bank_code: str      # e.g "058" for GTB — Paystack uses these codes
    account_number: str # user's actual bank account number
    narration: str | None = None


class WithdrawalResponse(BaseModel):
    reference: str
    amount: Decimal
    status: str
    narration: str | None