from decimal import Decimal
from pydantic import BaseModel


class TransferRequest(BaseModel):
    # user can pass either email or account number, but at least one is required
    receiver_email: str | None = None
    receiver_account_number: str | None = None
    amount: Decimal
    narration: str | None = None
    pin: str


class TransferResponse(BaseModel):
    reference: str
    amount: Decimal
    receiver: str
    narration: str | None
    status: str