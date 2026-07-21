"""
Async SQLAlchemy engine + session factory for NeonDB (PostgreSQL serverless).
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

# NeonDB requires SSL — already embedded in the connection string
db_url = settings.NEONDB_URL
connect_args = {}

if db_url.startswith("postgresql://") or db_url.startswith("postgresql+asyncpg://"):
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    parsed = urlparse(db_url)
    query = dict(parse_qsl(parsed.query))
    
    # asyncpg doesn't support these libpq query params, so we remove them
    for param in ["sslmode", "channel_binding", "target_session_attrs", "gssencmode"]:
        if param in query:
            val = query.pop(param)
            if param == "sslmode" and val in ("require", "verify-ca", "verify-full", "prefer"):
                connect_args["ssl"] = "require"
                
    parsed_query = urlencode(query)
    db_url = urlunparse(parsed._replace(query=parsed_query))
    
    if parsed.hostname and "neon.tech" in parsed.hostname:
        connect_args["ssl"] = "require"

engine = create_async_engine(
    db_url,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables if they don't exist (used on startup)."""
    from app.models import all_models  # noqa: F401 — ensures models are registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
