# Real-Time CRDT Document API

A high-performance, real-time collaborative document editor backend. This system uses fractional indexing Conflict-free Replicated Data Types (CRDTs) to ensure deterministic document state across distributed clients. 

## Architecture Stack
* **Framework:** FastAPI (Python 3.12)
* **Process Management:** Gunicorn with Uvicorn async workers (4x)
* **Database:** PostgreSQL 16 (Async SQLAlchemy & Alembic)
* **Real-Time Engine:** WebSockets
* **Message Broker / Caching:** Redis 7 (Pub/Sub & Distributed Locks)
* **Security:** JWT Authentication, slowapi Rate Limiting, bcrypt Hashing
* **Infrastructure:** Fully containerized via Docker Compose

---

## Running the Project Locally

The environment is fully containerized. No local dependencies are required other than Docker.

### Boot the cluster (Postgres, Redis, API Workers)
docker compose up --build -d

### Run the isolated async test suite
docker compose exec api pytest

---

## REST API Documentation
Base URL: `http://localhost:8000`

### Authentication (`/auth`)
* **POST `/auth/register`**
  * Payload: `{"email": "user@example.com", "password": "secure"}`
  * Returns: `201 Created` | `{"id": "uuid", "email": "user@example.com"}`
* **POST `/auth/login`**
  * Format: `application/x-www-form-urlencoded` (OAuth2 Standard)
  * Payload: `username=user@example.com&password=secure`
  * Returns: `200 OK` | `{"access_token": "jwt...", "token_type": "bearer"}`
* **GET `/auth/me`**
  * Headers: `Authorization: Bearer <token>`
  * Returns: `200 OK` | `{"user_id": "uuid"}`

### Documents (`/documents`)
* **POST `/documents/`** (Requires Auth)
  * Headers: `Authorization: Bearer <token>`
  * Payload: `{"title": "My Document"}`
  * Returns: `200 OK` | `{"id": "uuid", "title": "My Document"}`
* **GET `/documents/{document_id}`** (Public)
  * Returns: `200 OK` | `{"id": "uuid", "title": "My Document"}`
* **GET `/documents/{document_id}/analytics`** (Requires Auth)
  * Headers: `Authorization: Bearer <token>`
  * Returns: `200 OK` | Complex SQL aggregations showing top contributors.

---

## WebSocket Protocol (CRDT Engine)
Connection URL: `ws://localhost:8000/ws/doc/{document_id}`

The real-time engine requires strict adherence to the authentication lifecycle and CRDT JSON schemas.

### 1. The Reaper Handshake (Strict 3-Second Timeout)
Upon connecting to the WebSocket, the client has exactly 3.0 seconds to send the authentication payload. If the client fails to do so, the server will drop the connection with `WS_1008_POLICY_VIOLATION`.

**Client -> Server (Auth Payload):**
{"action": "authenticate", "token": "<jwt_access_token>"}

### 2. State Hydration
Once authenticated, the server will immediately respond with the current state of the document from PostgreSQL.

**Server -> Client (Hydrate Payload):**
{"action": "hydrate", "state": [{"value": "H", "position": [{"digit": 50, "site_id": "user_uuid_1"}]}]}

### 3. Remote Operations (CRDT Payloads)
To insert or delete characters, the client must broadcast operations using Base-100 fractional indexing. 

**Client -> Server (Insert Payload):**
{"action": "insert", "character": {"value": "x", "position": [{"digit": 62, "site_id": "current_user_uuid"}]}}

**Client -> Server (Delete Payload):**
(Note: Deletions do not require the value, only the exact position array of the character to be removed).
{"action": "delete", "position": [{"digit": 62, "site_id": "current_user_uuid"}]}