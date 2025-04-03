from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import logging
from app.core.config import settings
from sqlalchemy import text

logger = logging.getLogger(__name__)

Base = declarative_base()

try:
    # Используем правильные атрибуты из settings.database
    engine = create_async_engine(
        settings.database.async_url,  # Используем async_url (метод) вместо ASYNC_URL
        pool_size=settings.database.pool_size,  # lowercase согласно классу DatabaseSettings
        max_overflow=settings.database.max_overflow,  # lowercase
        echo=settings.database.echo_sql,  # lowercase
        pool_pre_ping=True,
        future=True
    )
    
    async_session_maker = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    
    # Алиас для обратной совместимости
    AsyncSessionLocal = async_session_maker
    
    logger.info(
        f"Database connection established\n"
        f"URL: {settings.database.async_url}\n"
        f"Pool size: {settings.database.pool_size}, "
        f"Max overflow: {settings.database.max_overflow}"
    )

except Exception as e:
    logger.error(
        f"Database connection error: {e}\n"
        f"Check your database settings in .env file\n"
        f"Attempted connection URL: {settings.database.async_url}"
    )
    raise

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def create_tables():
    try:
        async with engine.begin() as conn:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

__all__ = ['Base', 'async_session_maker', 'AsyncSessionLocal', 'engine', 'create_tables', 'get_async_session']