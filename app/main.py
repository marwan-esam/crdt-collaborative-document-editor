import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from app.api.websockets import router as websocket_router
from app.services.socket_manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
  await manager.start_listening()
  
  yield

  if manager.listener_task:
    manager.listener_task.cancel()
    with suppress(asyncio.CancelledError):
      await manager.listener_task

  await manager.redis_client.close()



app = FastAPI(title="Real-Time Docs API", lifespan=lifespan)

app.include_router(websocket_router)


@app.get("/")
async def health_check():
  return {"status": "Ready"}