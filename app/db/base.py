"""Database connection and SQLAlchemy ORM setup."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy Declarative Base class."""
    pass


# Use SQLite in-memory fallback for local test/dev environment if postgres driver is not connected
db_url = settings.DATABASE_URL
if "postgresql" in db_url and "asyncpg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(db_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session():
    """Dependency injection for async DB session."""
    async with AsyncSessionLocal() as session:
        yield session
