from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def connect(self) -> None:
        if self._engine is not None:
            return

        self._engine = create_async_engine(
            str(settings.DATABASE_URL),
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
            pool_pre_ping=True,
            echo=settings.DB_ECHO,
            poolclass=NullPool if settings.ENVIRONMENT == 'test' else None,
        )

        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    def disconnect(self) -> None:
        if self._engine is not None:
            import asyncio

            asyncio.run(self._engine.dispose())
            self._engine = None
            self._session_factory = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            self.connect()
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self.connect()
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_all(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_all(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


database = Database()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with database.session() as session:
        yield session


async def init_db() -> None:
    database.connect()
    if settings.ENVIRONMENT == 'development':
        await database.create_all()


async def close_db() -> None:
    database.disconnect()
