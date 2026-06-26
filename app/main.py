import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from app.api.websockets import router as websocket_router
from app.api.documents import router as documents_router
from app.api.auth import router as auth_router
from app.services.socket_manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
  await manager.start_listening()
  
  yield

  if manager.listener_task:
    manager.listener_task.cancel()
    with suppress(asyncio.CancelledError):
      await manager.listener_task

  await manager.redis_client.aclose()



app = FastAPI(title="Real-Time Docs API", lifespan=lifespan)

origins = [
  "*",
]

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(websocket_router)
app.include_router(documents_router)
app.include_router(auth_router)

@app.get("/")
async def health_check():
  return {"status": "Ready"}