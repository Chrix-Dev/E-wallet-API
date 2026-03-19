import random
import secrets

from app.models.verification_token import VerificationToken
from app.services.email_service import send_verification_email
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, hash_token
)
from app.core.config import settings
from app.models.user import User
from app.models.wallet import Wallet
from app.models.refresh_token import RefreshToken
from app.schemas.auth import RegisterRequest, LoginRequest


async def register_user(data: RegisterRequest, db: AsyncSession):
    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
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

    # generate verification token
    token = secrets.token_urlsafe(32)
    verification = VerificationToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    db.add(verification)
    await db.commit()
    await db.refresh(user)

    # send verification email in background
    await send_verification_email(user.email, user.full_name, token)
    return user


async def login_user(data: LoginRequest, db: AsyncSession):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    # save hashed refresh token to DB
    token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(token_record)
    await db.commit()

    return {"access_token": access_token, "refresh_token": refresh_token}


async def refresh_access_token(refresh_token: str, db: AsyncSession):
    payload = decode_token(refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    token_hash = hash_token(refresh_token)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
        )
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found or revoked")

    if token_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    new_access_token = create_access_token(user_id)
    return {"access_token": new_access_token, "refresh_token": refresh_token}


async def logout_user(refresh_token: str, db: AsyncSession):
    token_hash = hash_token(refresh_token)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    token_record = result.scalar_one_or_none()

    if token_record:
        token_record.is_revoked = True
        await db.commit()

    return {"message": "Logged out successfully"}