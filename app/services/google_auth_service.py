import random
import httpx

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.models.user import User
from app.models.wallet import Wallet
from app.models.refresh_token import RefreshToken
from datetime import datetime, timedelta, timezone


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def get_google_auth_url() -> str:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_code_for_token(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            }
        )

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to exchange code for token")

    return response.json()


async def get_google_user_info(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to fetch Google user info")

    return response.json()


async def google_login(code: str, db: AsyncSession):
    # exchange the code Google gives for an actual access token
    token_data = await exchange_code_for_token(code)
    google_access_token = token_data.get("access_token")

    # use that token to get the user's profile from Google
    user_info = await get_google_user_info(google_access_token)

    google_id = user_info.get("sub")
    email = user_info.get("email")
    full_name = user_info.get("name", "")

    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not get email from Google")

    # check if user already exists by google_id or email
    result = await db.execute(
        select(User).where(
            (User.google_id == google_id) | (User.email == email)
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        # new user — create account and wallet
        user = User(
            email=email,
            full_name=full_name,
            google_id=google_id,
            is_verified=True, 
        )
        db.add(user)
        await db.flush()

        while True:
            account_number = str(random.randint(1000000000, 9999999999))
            existing_acc = await db.execute(select(Wallet).where(Wallet.account_number == account_number))
            if not existing_acc.scalar_one_or_none():
                break

        wallet = Wallet(user_id=user.id, account_number=account_number)
        db.add(wallet)
    else:
        # existing user — update google_id if they registered with email before
        if not user.google_id:
            user.google_id = google_id

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(token_record)
    await db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token}