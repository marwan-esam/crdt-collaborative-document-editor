import asyncio
import json
import redis.asyncio as redis
from fastapi import WebSocket
from sqlalchemy import select
from pydantic import TypeAdapter
from app.core.config import settings
from app.schemas.crdt import PositionIdentifier, Character, find_insert_index
from app.domain.models import Document
from app.db.database import SessionLocal

class ConnectionManager:
  def __init__(self):
    self.active_connections: dict[str, dict[str, WebSocket]] = {}
    self.document_state: dict[str, list[Character]] = {}

    self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    self.pubsub = self.redis_client.pubsub()
    self.listener_task: asyncio.Task | None = None
    self.autosave_task: asyncio.Task | None = None


  async def start_listening(self):
    await self.pubsub.subscribe("system_channel")
    self.listener_task = asyncio.create_task(self._listen_to_redis())
    self.autosave_task = asyncio.create_task(self._autosave_loop())

  async def connect(self, websocket: WebSocket, document_id: str, client_id: str):

    if document_id not in self.active_connections:
      self.active_connections[document_id] = {}

      async with SessionLocal() as db:
        result = await db.execute(select(Document).where(str(Document.id) == document_id))
        doc_record = result.scalar_one_or_none()

        if doc_record and doc_record.crdt_state:
          self.document_state[document_id] = TypeAdapter(list[Character]).validate_python(doc_record.crdt_state)
        else:
          self.document_state[document_id] = []

      await self.pubsub.subscribe(f"doc_channel:{document_id}")

    self.active_connections[document_id][client_id] = websocket

    state_payload = json.dumps({
      "action": "hydrate",
      "state": [char.model_dump() for char in self.document_state[document_id]]
    })

    await websocket.send_text(state_payload)

  
  async def disconnect(self, websocket: WebSocket, document_id: str, client_id: str):
    if document_id in self.active_connections:
      if client_id in self.active_connections[document_id]:
        del self.active_connections[document_id][client_id]


      if not self.active_connections[document_id]:

        async with SessionLocal() as db:
          result = await db.execute(select(Document).where(str(Document.id) == document_id))
          doc_record = result.scalar_one_or_none()

          if doc_record:
            doc_record.crdt_state = [char.model_dump() for char in self.document_state[document_id]]
            await db.commit()

        del self.active_connections[document_id]
        if document_id in self.document_state:
          del self.document_state[document_id]
        asyncio.create_task(self.pubsub.unsubscribe(f"doc_channel:{document_id}"))


  async def broadcast_local(self, document_id: str, sender_id: str, message: str):
    if document_id in self.active_connections:
      for client_id, connection in list(self.active_connections[document_id].items()):
        if client_id != sender_id:
          await connection.send_text(message)

  async def publish_to_redis(self, document_id: str, sender_id: str, message: str):
    channel = f"doc_channel:{document_id}"
    payload = json.dumps({"sender_id": sender_id, "data": message})
    await self.redis_client.publish(channel, payload)

  
  def apply_remote_operation(self, document_id: str, operation_data: dict):
    action = operation_data.get("action")
    doc_state = self.document_state[document_id]

    if action == "insert":
      char_obj = Character(**operation_data["character"])
      insert_idx = find_insert_index(doc_state, char_obj)

      doc_state.insert(insert_idx, char_obj)

    elif action == "delete":
      target_pos = [PositionIdentifier(**p) for p in operation_data["position"]]
      dummy_char = Character(value="", position=target_pos)

      idx = find_insert_index(doc_state, dummy_char)
      if idx < len(doc_state) and doc_state[idx].position == target_pos:
        doc_state.pop(idx)

  
  async def _listen_to_redis(self):
    while True:
      try:
        message = await self.pubsub.get_message(ignore_subscribe_messages=True)

        if message is not None:
          if message["type"] == "message":
            channel = message["channel"]
            doc_id = channel.split(":")[1]
            payload = json.loads(message["data"])
            sender_id = payload["sender_id"]
            raw_data_string = payload["data"]
            operation_data = json.loads(raw_data_string)

            if doc_id in self.document_state:
              self.apply_remote_operation(doc_id, operation_data)

            await self.broadcast_local(doc_id, sender_id, raw_data_string)

        await asyncio.sleep(0.01)
      except redis.RedisError as e:
        print(f"CRITICAL ERROR in Redis Listener {e}")
        print("Attempting to reconnect in 5 seconds...")
        await asyncio.sleep(5)
      except Exception as e:
        print(f"Error: {e}")

  async def _autosave_loop(self):
    while True:
      await asyncio.sleep(10)

      if not self.document_state:
        continue

      active_docs = list(self.document_state.items())

      async with SessionLocal() as db:
        for doc_id, crdt_array in active_docs:
          try:
            result = await db.execute(select(Document).where(str(Document.id) == doc_id))
            doc_record = result.scalar_one_or_none()

            if doc_record:
              doc_record.crdt_state = [char.model_dump() for char in crdt_array]
          
          except Exception as e:
            print(f"Autosave error for document {doc_id}: {e}")

        try:
          await db.commit()
        except Exception as e:
          print(f"Database commit error during autosave: {e}")



manager = ConnectionManager()