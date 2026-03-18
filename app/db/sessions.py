from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.db.base import Base 


# Async engine — used by the app at runtime
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,   # logs SQL queries when DEBUG=True
    pool_pre_ping=True,    # checks connection health before using it from the pool
    connect_args={
        "statement_cache_size": 0  # required when using Supabase connection pooler
    }
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,  # objects stay usable after commit without re-querying
    class_=AsyncSession,
)
