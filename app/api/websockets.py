from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.socket_manager import manager

router = APIRouter()


@router.websocket("/ws/doc/{document_id}")
async def document_websocket(websocket: WebSocket, document_id: str, client_id: str):
  await manager.connect(websocket, document_id, client_id)

  try:
    while True:
      data = await websocket.receive_text()

      await manager.publish_to_redis(document_id, client_id, data)

  except WebSocketDisconnect:
    pass
  finally:
    manager.disconnect(websocket, document_id, client_id)