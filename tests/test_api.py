import pytest
import uuid

pytestmark = pytest.mark.asyncio

test_user = {
  "email": f"robot_{uuid.uuid4().hex[:8]}@example.com",
  "password": "secure_robot_password"
}

state = {}

async def test_full_authentication_flow(async_client):

  reg_response = await async_client.post("/auth/register", json=test_user)
  assert reg_response.status_code == 201

  login_response = await async_client.post("/auth/login", data={
    "username": test_user["email"],
    "password": test_user["password"]
  })
  assert login_response.status_code == 200

  state["token"] = login_response.json()["access_token"]

  profile_response = await async_client.get(
    "/auth/me",
    headers={"Authorization": f"Bearer {state["token"]}"}
  )

  assert profile_response.status_code == 200


async def test_document_creation(async_client):

  doc_response = await async_client.post(
    "/documents/",
    json={"title": "Automated Test Document"},
    headers={"Authorization": f"Bearer {state["token"]}"}
  )

  assert doc_response.status_code == 200


async def test_rate_limiter_active(async_client):
  responses = []
  for _ in range(15):
    res = await async_client.post("/auth/login", data={
      "username": "spam@example.com",
      "password": "wrong"
    })
    responses.append(res.status_code)

  assert 429 in responses