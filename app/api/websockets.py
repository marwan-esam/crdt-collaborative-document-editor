import asyncio
import json
import jwt
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.socket_manager import manager
from app.core.config import settings
from app.db.database import get_db
from app.domain.models import Document

router = APIRouter()


@router.websocket("/ws/doc/{document_id}")
async def document_websocket(websocket: WebSocket, document_id: str, db: AsyncSession = Depends(get_db)):

  try:
    valid_uuid = UUID(document_id)
  except ValueError:
    await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
    return
  
  result = await db.execute(select(Document).where(Document.id == valid_uuid))

  if not result.scalar_one_or_none():
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return

  await websocket.accept()

  try:

    auth_message_raw = await asyncio.wait_for(
      websocket.receive_text(),
      timeout=3.0
    )

    auth_data = json.loads(auth_message_raw)
    token = auth_data.get("token")

    if not token:
      await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
      return
    
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    user_id: str = payload.get("sub")

    if not user_id:
      await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
      return
    
  except asyncio.TimeoutError:
    print(f"[Security] Terminating idle connection on {document_id}")
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return
  
  except (json.JSONDecodeError, jwt.PyJWTError):
    print(f"[Security] Terminating invalid auth attempt on {document_id}")
    websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return
  
  await manager.connect(websocket, document_id, user_id)

  try:
    while True:
      data = await websocket.receive_text()

      if len(data) > 1024 * 10:
        print(f"[Security] Payload too large from {user_id}. Terminating...")
        await websocket.close(code=status.WS_1009_MESSAGE_TOO_BIG)
        return

      await manager.publish_to_redis(document_id, user_id, data)

  except WebSocketDisconnect:
    pass
  finally:
    await manager.disconnect(websocket, document_id, user_id)