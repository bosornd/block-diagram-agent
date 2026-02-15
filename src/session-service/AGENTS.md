# src/session-service — Session Service

Session-only microservice. **Connects only to PostgreSQL** and exposes an ADK-compatible REST API for session CRUD and event append. The UI and agent use this service for session data.

## Tech Stack

- **Language**: Go 1.24+
- **Storage**: `google.golang.org/adk/session/database` + GORM, PostgreSQL
- **API**: Gorilla Mux; same paths and JSON format as ADK REST

## Main Files

| File | Description |
|------|--------------|
| `main.go` | Entry point. DB connection, session/database service setup, HTTP routes (/api/apps/.../sessions, .../events). |
| `handlers.go` | HTTP handlers for session list/create/get/delete and event append. |
| `models.go` | REST request/response models (Session, Event, CreateSessionRequest) and conversion to/from session package types. |
| `Dockerfile` | Multi-stage build; port 8081. |

## API (ADK Compatible)

- `GET  /api/apps/{app_name}/users/{user_id}/sessions` — list
- `POST /api/apps/{app_name}/users/{user_id}/sessions` — create (body: `{ state?, events? }`)
- `POST /api/apps/{app_name}/users/{user_id}/sessions/{session_id}` — create with given ID
- `GET  /api/apps/{app_name}/users/{user_id}/sessions/{session_id}` — get
- `DELETE /api/apps/{app_name}/users/{user_id}/sessions/{session_id}` — delete
- `POST /api/apps/{app_name}/users/{user_id}/sessions/{session_id}/events` — append event (for agent remote client)

## Environment Variables

- **DB**: `SESSION_DATABASE_URL` or `SESSION_DB_HOST`, `SESSION_DB_USER`, `SESSION_DB_PASSWORD`, `SESSION_DB_NAME` (optional: `SESSION_DB_PORT`, `SESSION_DB_SSLMODE`)
- **Server**: `PORT` (default 8081)

## Local Run

```bash
export SESSION_DATABASE_URL="host=localhost user=postgres password=postgres dbname=agent port=5432 sslmode=disable"
cd src/session-service && go run .
# http://localhost:8081
```

## Development Reference

- Point the agent at this service with e.g. `SESSION_SERVICE_URL=http://localhost:8081`.
- UI can send session API traffic here by setting `window.SESSION_API_BASE = 'http://localhost:8081'` (optional).
- For K8s deployment, PostgreSQL is `block-diagram-postgres`, Secret is `block-diagram-secrets`. See `src/k8s/AGENTS.md`.
