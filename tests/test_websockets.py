import pytest
import uuid
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app

def setup_test_document(client: TestClient) -> tuple[str, str]:
  test_user = {
    "email": f"ws_{uuid.uuid4().hex[:8]}@example.com",
    "username": f"ws_{uuid.uuid4().hex[:8]}",
    "password": "Secure_WS_Password1!"
  }

  client.post("/auth/register", json=test_user)
  login = client.post("/auth/login", data={
    "username": test_user["email"],
    "password": test_user["password"]
  })

  token = login.json()["access_token"]

  doc_res = client.post(
    "/documents/",
    json={"title": "WS Test Document"},
    headers={"Authorization": f"Bearer {token}"}
  )

  doc_id = doc_res.json()["id"]

  return token, doc_id


def test_the_reaper_timeout():

  with TestClient(app) as client:
    token, doc_id = setup_test_document(client)
    with pytest.raises(WebSocketDisconnect) as exc_info:
      with client.websocket_connect(f"/ws/doc/{doc_id}") as websocket:
        websocket.receive_text()
    assert exc_info.value.code == 1008


def test_authenticated_connection_and_crdt_sync():
  with TestClient(app) as client:
    token, doc_id = setup_test_document(client)

    with client.websocket_connect(f"/ws/doc/{doc_id}") as websocket:
      websocket.send_json({"action": "authenticate", "token": token})

      hydrate_message = websocket.receive_json()
      assert hydrate_message["action"] == "hydrate"
      assert isinstance(hydrate_message["state"], list)

      test_op = {
        "action": "insert",
        "character": {
          "value": "X",
          "position": [{"digit": 50, "site_id": "test_robot"}]
        }
      }

      websocket.send_json(test_op)

      assert True