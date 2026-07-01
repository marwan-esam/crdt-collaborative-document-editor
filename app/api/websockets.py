import asyncio
import json
import jwt
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.services.socket_manager import manager
from app.core.config import settings
from app.db.database import SessionLocal
from app.domain.models import Document, ActivityLog, User

router = APIRouter()


@router.websocket("/ws/doc/{document_id}")
async def document_websocket(websocket: WebSocket, document_id: str):

  try:
    valid_uuid = UUID(document_id)
  except ValueError:
    await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
    return
  try:
    async with SessionLocal() as db:
      result = await db.execute(select(Document).where(Document.id == valid_uuid))
  except Exception as e:
    print(f"Database session error: {e}")
    return
  
  if not result.scalar_one_or_none():
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return

  await websocket.accept()

  has_edited = False

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
    user_id: str = payload.get("sub") or payload.get("id")

    if not user_id:
      await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
      return
    
    join_log = ActivityLog(
      user_id=UUID(user_id),
      document_id=valid_uuid,
      action="join"
    )
    async with SessionLocal() as db:
      db.add(join_log)
      doc_result = await db.execute(
        select(Document).options(
          selectinload(Document.collaborators)
        ).where(Document.id == valid_uuid)
      )
      doc_record = doc_result.scalar_one_or_none()

      if doc_record and doc_record.owner_id != UUID(user_id):
        if not any(c.id == UUID(user_id) for c in doc_record.collaborators):
          user_result = await db.execute(select(User).where(User.id == UUID(user_id)))
          user_record = user_result.scalar_one_or_none()
          if user_record:
            doc_record.collaborators.append(user_record)

      await db.commit()
    
  except asyncio.TimeoutError:
    print(f"[Security] Terminating idle connection on {document_id}")
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return
  
  except (json.JSONDecodeError, jwt.PyJWTError):
    print(f"[Security] Terminating invalid auth attempt on {document_id}")
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return
  
  except Exception as e:
    print(f"Database commit error during logging join activity: {e}")
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return
  
  await manager.connect(websocket, document_id, user_id)

  try:
    while True:
      data = await websocket.receive_text()

      if len(data) > 1024 * 10:
        print(f"[Security] Payload too large from {user_id}. Terminating...")
        await websocket.close(code=status.WS_1009_MESSAGE_TOO_BIG)
        return
      
      if not has_edited:
        has_edited = True
        try:
          edit_log = ActivityLog(
            user_id=UUID(user_id),
            document_id=valid_uuid,
            action="edit"
          )
          async with SessionLocal() as db:
            db.add(edit_log)
            await db.commit()
        except Exception as e:
          print(f"Failed to log the edit activity: {e}")


      await manager.publish_to_redis(document_id, user_id, data)


  except WebSocketDisconnect:
    pass
  finally:
    await manager.disconnect(websocket, document_id, user_id)

    leave_payload = json.dumps({"action": "leave", "site_id": user_id})
    await manager.publish_to_redis(document_id, user_id, leave_payload)
    try:
      async with SessionLocal() as disconnect_db:
        leave_log = ActivityLog(
          user_id=UUID(user_id),
          document_id=valid_uuid,
          action="leave"
        )
        disconnect_db.add(leave_log)
        await disconnect_db.commit()
    except Exception as e:
      print(f"Database commit error during logging leave activity: {e}")