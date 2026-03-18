from fastapi import APIRouter, Request, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.services import webhook_service

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/paystack")
async def paystack_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    # process the webhook in the background so we return 200 to Paystack immediately
    # Paystack will retry if it doesn't get a 200 fast enough
    background_tasks.add_task(webhook_service.handle_paystack_event, payload, signature, db)

    return {"status": "received"}