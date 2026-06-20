from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
  settings.DATABASE_URL,
  pool_size=20,
  max_overflow=10
)

SessionLocal = async_sessionmaker(
  autocommit=False,
  autoflush=True,
  bind=engine,
  class_=AsyncSession
)

class Base(DeclarativeBase):
  pass

async def get_db():
  async with SessionLocal() as db:
    try:
      yield db
    finally:
      await db.close()