from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.base import Base
from app.db.sessions import engine
from app.api.v1 import auth, wallets, webhooks, transactions, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(wallets.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")



@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}