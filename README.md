# Real-Time CRDT Document API

A high-performance, real-time collaborative document editor backend. This system uses fractional indexing Conflict-free Replicated Data Types (CRDTs) to ensure deterministic document state across distributed clients. 

## Architecture Stack
* **Framework:** FastAPI (Python 3.12)
* **Process Management:** Gunicorn with Uvicorn async workers
* **Database:** PostgreSQL 16 (Async SQLAlchemy & Alembic)
* **Real-Time Engine:** WebSockets
* **Message Broker / Caching:** Redis 7 (Pub/Sub & Distributed Locks)
* **Security:** JWT Authentication, slowapi Rate Limiting, bcrypt Hashing, Strict Pydantic Edge Validation, IDOR Mitigation
* **Infrastructure:** Fully containerized via Docker Compose
* **Production Deployment:** Oracle Cloud (Ubuntu), Nginx Reverse Proxy, Let's Encrypt SSL

---

## Live Production Endpoints
The application is actively deployed and secured via SSL/TLS.
* **Frontend Web App:** [https://marwan-docs.vercel.app](https://marwan-docs.vercel.app)
* **REST API Backend:** [https://api.marwan-crdt-docs.duckdns.org](https://api.marwan-crdt-docs.duckdns.org)
* **WebSocket Engine:** `wss://api.marwan-crdt-docs.duckdns.org/ws/doc/{document_id}`

---

## Running the Project Locally

The environment is fully containerized. No local dependencies are required other than Docker.

### Boot the cluster (Postgres, Redis, API Workers)
```bash
docker compose up --build -d
```

### Run the isolated async test suite
```bash
docker compose exec api pytest
```

---

## REST API Documentation

### Authentication (`/auth`)
* **`POST /auth/register`**
  * Payload: `{"email": "user@example.com", "username": "marwan123", "password": "StrictPassword1!"}`
  * *Note: Passwords must be >= 8 chars and contain uppercase, lowercase, numbers, and symbols.*
  * Returns: `201 Created` | `{"id": "uuid", "email": "user@example.com", "username": "marwan123"}`
* **`POST /auth/login`**
  * Format: `application/x-www-form-urlencoded` (OAuth2 Standard)
  * Payload: `username=user@example.com&password=StrictPassword1!`
  * Returns: `200 OK` | `{"access_token": "jwt...", "token_type": "bearer"}`
* **`GET /auth/me`**
  * Headers: `Authorization: Bearer <token>`
  * Returns: `200 OK` | `{"id": "uuid", "email": "user@example.com", "username": "marwan123"}`

### Workspace & Documents (`/documents`)
* **`GET /documents/`** (Requires Auth)
  * Headers: `Authorization: Bearer <token>`
  * Returns: `200 OK` | Lists all documents the user owns or actively collaborates on via Many-to-Many junction.
* **`POST /documents/`** (Requires Auth)
  * Headers: `Authorization: Bearer <token>`
  * Payload: `{"title": "My Document"}`
  * Returns: `200 OK` | `{"id": "uuid", "title": "My Document"}`
* **`GET /documents/{document_id}`** (Requires Auth)
  * Headers: `Authorization: Bearer <token>`
  * Returns: `200 OK` | `{"id": "uuid", "title": "My Document"}`
* **`DELETE /documents/{document_id}`** (Requires Auth)
  * Headers: `Authorization: Bearer <token>`
  * Returns: `204 No Content` | *Dynamic Endpoint: If the user is the owner, the document is permanently deleted. If the user is a collaborator, they are safely removed from the shared workspace.*
* **`GET /documents/{document_id}/owner`** (Requires Auth)
  * Headers: `Authorization: Bearer <token>`
  * Returns: `200 OK` | `{"id": "uuid", "username": "marwan123"}`
* **`GET /documents/{document_id}/collaborators`** (Requires Auth)
  * Headers: `Authorization: Bearer <token>`
  * Returns: `200 OK` | `[{"id": "uuid", "username": "marwan123"}]`
* **`GET /documents/{document_id}/analytics`** (Requires Auth)
  * Headers: `Authorization: Bearer <token>`
  * Returns: `200 OK` | `{"document_id": "uuid", "top_contributors": [{"username": "marwan123", "user_id": "uuid", "total_edits": 7, "rank": 1}]}`

---

## WebSocket Protocol (CRDT Engine)

The real-time engine requires strict adherence to the authentication lifecycle and CRDT JSON schemas.

### 1. The Reaper Handshake (Strict 3-Second Timeout)
Upon connecting to the WebSocket, the client has exactly 3.0 seconds to send the authentication payload. If the client fails to do so, the server will drop the connection with `WS_1008_POLICY_VIOLATION`.

**Client -> Server (Auth Payload):**
```json
{
  "action": "authenticate", 
  "token": "<jwt_access_token>"
}
```

### 2. State Hydration
Once authenticated, the server will immediately respond with the current state of the document from PostgreSQL.

**Server -> Client (Hydrate Payload):**
```json
{
  "action": "hydrate", 
  "state": [
    {"value": "H", "position": [{"digit": 50, "site_id": "user_uuid_1"}]}
  ]
}
```

### 3. Remote Operations (CRDT Payloads)
To insert or delete characters, the client must broadcast operations using Base-100 fractional indexing. 

**Client -> Server (Insert Payload):**
```json
{
  "action": "insert", 
  "character": {
    "value": "x", 
    "position": [{"digit": 62, "site_id": "current_user_uuid"}]
  }
}
```

**Client -> Server (Delete Payload):**
*(Note: Deletions do not require the value, only the exact position array of the character to be removed).*
```json
{
  "action": "delete", 
  "position": [{"digit": 62, "site_id": "current_user_uuid"}]
}
```