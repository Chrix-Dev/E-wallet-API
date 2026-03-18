from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, UserResponse
from app.services import auth_service
from app.services.google_auth_service import get_google_auth_url, google_login

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register_user(data, db)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    tokens = await auth_service.login_user(data, db)
    return {**tokens, "token_type": "bearer"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    tokens = await auth_service.refresh_access_token(data.refresh_token, db)
    return {**tokens, "token_type": "bearer"}


@router.post("/logout")
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.logout_user(data.refresh_token, db)


@router.get("/google")
async def google_auth():
    url = get_google_auth_url()
    return RedirectResponse(url)


@router.get("/google/callback", response_model=TokenResponse)
async def google_callback(code: str = Query(...), db: AsyncSession = Depends(get_db)):
    tokens = await google_login(code, db)
    return {**tokens, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_user)):
    return current_user