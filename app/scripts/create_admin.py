import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.future import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
import app.models  

ADMIN_EMAIL = settings.ADMIN_EMAIL
ADMIN_PASSWORD = settings.ADMIN_PASSWORD
ADMIN_FULL_NAME = settings.ADMIN_FULL_NAME

async def create_admin():
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"statement_cache_size": 0}
    )
    AsyncSession = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with AsyncSession() as db:
        result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Admin {ADMIN_EMAIL} already exists.")
            return

        admin = User(
            email=ADMIN_EMAIL,
            full_name=ADMIN_FULL_NAME,
            hashed_password=hash_password(ADMIN_PASSWORD),
            is_verified=True,
            is_active=True,
            is_admin=True,
            tier="tier3",
        )
        db.add(admin)
        await db.commit()
        print(f"Admin created successfully: {ADMIN_EMAIL}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_admin())