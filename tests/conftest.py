import pytest
import pytest_asyncio
import app.services.socket_manager as manager
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.main import app
from app.db.database import get_db, Base

TEST_DATABASE_URL = "postgresql+asyncpg://doc_user:strictpassword@postgres-test:5432/docs_test_db"
manager.settings.REDIS_URL = "redis://redis-test:6379"

engine_test = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=True, bind=engine_test)
manager.SessionLocal = TestingSessionLocal

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():

  async with engine_test.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

  yield

  async with engine_test.begin() as conn:
    await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
  async with TestingSessionLocal() as db:
    yield db


app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(scope="function")
async def async_client():
  async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
    yield client
