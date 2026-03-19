from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "E-Wallet API"
    DEBUG: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str        # async (asyncpg) — used by the app
    SYNC_DATABASE_URL: str   # sync (psycopg2) — used by Alembic

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # Paystack
    PAYSTACK_SECRET_KEY: str

    # SendGrid
    SENDGRID_API_KEY: str
    SENDGRID_SENDER_EMAIL: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Single instance imported everywhere
settings = Settings()