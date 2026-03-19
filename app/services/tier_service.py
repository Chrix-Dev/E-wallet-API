from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.limits import get_limits
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.tier import UpgradeTier2Request, UpgradeTier3Request


async def upgrade_to_tier2(data: UpgradeTier2Request, current_user: User, db: AsyncSession):
    if not current_user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verify your email first")

    if current_user.tier != "tier1":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You are already on tier 2 or higher")

    if len(data.bvn) != 11:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="BVN must be 11 digits")

    current_user.phone_number = data.phone_number
    current_user.date_of_birth = data.date_of_birth
    current_user.bvn = data.bvn
    current_user.tier = "tier2"

    await db.commit()
    return {"message": "Account upgraded to Tier 2 successfully", "tier": "tier2"}


async def upgrade_to_tier3(data: UpgradeTier3Request, current_user: User, db: AsyncSession):
    if current_user.tier != "tier2":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You must be on Tier 2 before upgrading to Tier 3")

    valid_id_types = ["NIN", "passport", "drivers_license"]
    if data.id_type not in valid_id_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"id_type must be one of {valid_id_types}")

    current_user.id_type = data.id_type
    current_user.id_number = data.id_number
    current_user.address = data.address
    current_user.tier = "tier3"

    await db.commit()
    return {"message": "Account upgraded to Tier 3 successfully", "tier": "tier3"}


async def get_user_limits(current_user: User, db: AsyncSession):
    wallet_result = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = wallet_result.scalar_one_or_none()

    limits = get_limits(current_user.tier)

    return {
        "tier": current_user.tier,
        "min_transaction": str(limits["min_transaction"]),
        "max_single_transfer": str(limits["max_single_transfer"]),
        "max_single_withdrawal": str(limits["max_single_withdrawal"]),
        "max_daily_transfer": str(limits["max_daily_transfer"]),
        "max_daily_withdrawal": str(limits["max_daily_withdrawal"]),
        "daily_transfer_used": str(wallet.daily_transfer_used),
        "daily_withdrawal_used": str(wallet.daily_withdrawal_used),
    }