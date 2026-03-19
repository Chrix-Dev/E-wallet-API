from pydantic import BaseModel


class UpgradeTier2Request(BaseModel):
    phone_number: str
    date_of_birth: str   # format: YYYY-MM-DD
    bvn: str


class UpgradeTier3Request(BaseModel):
    id_type: str         # NIN, passport, drivers_license
    id_number: str
    address: str


class LimitsResponse(BaseModel):
    tier: str
    min_transaction: str
    max_single_transfer: str
    max_single_withdrawal: str
    max_daily_transfer: str
    max_daily_withdrawal: str
    daily_transfer_used: str
    daily_withdrawal_used: str