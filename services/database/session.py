from __future__ import annotations
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.models import Base
from configs.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _normalise_url(raw: str) -> str:
    """Map plain DB URLs to their async driver variants."""
    replacements = {
        "postgresql://":  "postgresql+asyncpg://",
        "postgres://":    "postgresql+asyncpg://",
        "sqlite:///":     "sqlite+aiosqlite:///",
    }
    for prefix, replacement in replacements.items():
        if raw.startswith(prefix) and "asyncpg" not in raw and "aiosqlite" not in raw:
            return raw.replace(prefix, replacement, 1)
    return raw


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        url = _normalise_url(settings.DATABASE_URL)
        connect_args = {"check_same_thread": False} if "sqlite" in url else {}
        _engine = create_async_engine(
            url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            echo=settings.DEBUG,
            future=True,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a transactional async session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    """Create all ORM-mapped tables if they do not already exist."""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_ready")
