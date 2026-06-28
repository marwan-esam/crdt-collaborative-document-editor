import pytest
import uuid

pytestmark = pytest.mark.asyncio

test_user = {
  "email": f"robot_{uuid.uuid4().hex[:8]}@example.com",
  "username": f"robot_{uuid.uuid4().hex[:8]}",
  "password": "Secure_R0bot_password1!"
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


async def test_document_analytics(async_client):
  doc_response = await async_client.post(
    "/documents/",
    json={"title": "Analytics Test Document"},
    headers={"Authorization": f"Bearer {state["token"]}"}
  )

  doc_id = doc_response.json()["id"]

  analytics_response = await async_client.get(
    f"/documents/{doc_id}/analytics",
    headers={"Authorization": f"Bearer {state["token"]}"}
  )

  assert analytics_response.status_code == 200

  data = analytics_response.json()

  assert "top_contributors" in data
  assert type(data["top_contributors"]) is list


async def test_document_collobrators(async_client):
  doc_response = await async_client.post(
    "/documents/",
    json={"title": "Collab Test Document"},
    headers={"Authorization": f"Bearer {state["token"]}"}
  )

  doc_id = doc_response.json()["id"]

  collab_response = await async_client.get(
    f"/documents/{doc_id}/collaborators",
    headers={"Authorization": f"Bearer {state["token"]}"}
  )

  assert collab_response.status_code == 200
  data = collab_response.json()

  assert isinstance(data, list)
  assert len(data) >= 1 
  assert "username" in data[0]
  assert data[0]["username"] == test_user["username"]


async def test_document_owner(async_client):

  doc_response = await async_client.post(
    "/documents/",
    json={"title": "Owner Test Document"},
    headers={"Authorization": f"Bearer {state["token"]}"}
  )

  doc_id = doc_response.json()["id"]

  owner_response = await async_client.get(
    f"/documents/{doc_id}/owner",
    headers={"Authorization": f"Bearer {state["token"]}"}
  )

  assert owner_response.status_code == 200
  data = owner_response.json()

  assert "username" in data
  assert data["username"] == test_user["username"]