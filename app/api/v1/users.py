from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.schemas.tier import UpgradeTier2Request, UpgradeTier3Request, LimitsResponse
from app.services import tier_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/upgrade-tier2")
async def upgrade_tier2(
    data: UpgradeTier2Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await tier_service.upgrade_to_tier2(data, current_user, db)


@router.post("/upgrade-tier3")
async def upgrade_tier3(
    data: UpgradeTier3Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await tier_service.upgrade_to_tier3(data, current_user, db)


@router.get("/me/limits", response_model=LimitsResponse)
async def get_limits(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await tier_service.get_user_limits(current_user, db)