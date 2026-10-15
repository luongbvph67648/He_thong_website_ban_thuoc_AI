from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)


def get_engine() -> AsyncEngine:
    return engine
