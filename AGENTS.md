# Agentk Block Diagram Service

A service that generates block diagrams using an LLM.

## Architecture

- **UI** → **Agent** (Python + Google ADK) → **LLM** (Google Gemini or local models such as KServe; selected via `LLM_BASE_URL` / `KSERVE_URL`)
- **Sessions**: Both UI and agent use **Session Service** for session data. Only Session Service connects to PostgreSQL; the agent does not connect to the DB.
- The agent takes user descriptions and produces Mermaid code.

## Folder Roles

| Folder | Role |
|--------|------|
| `src/session-service` | Session-only service. PostgreSQL connection, ADK-compatible REST API (session CRUD, event append). Used by UI and agent. |
| `src/agent` | Python + Google ADK agent. Diagram generation logic. Structured output (title / message / mermaid) via Pydantic. Sessions via Session Service HTTP client. |
| `src/ui` | Web UI (chat + Mermaid rendering). Phase 2. Session API can be pointed at Session Service or agent. |
| `src/k8s` | Kubernetes manifests. `block-diagram` namespace (PostgreSQL, Session Service, agent, UI, LLM). For local LLM (Ollama) deployment and agent integration (`LLM_BASE_URL`), see `k8s/llm` and `src/k8s/AGENTS.md`. |
| `scripts` | Local dev (`dev-local.sh`; agent + UI with in-memory sessions, no DB), image build (`build-images.sh`), K8s deploy (`deploy-k8s.sh`, `rebuild-and-deploy.sh`). |

## Development Reference

- Agent changes: see `src/agent/AGENTS.md`.
- UI / frontend: see `src/ui/AGENTS.md`.
- Local LLM (KServe) deployment and agent integration: see `src/k8s/AGENTS.md` (LLM section) and `src/k8s/llm/`.
- Deployment / infrastructure: see `src/k8s/AGENTS.md`.
- Build and deploy scripts: see `scripts/README.md`.
- Keep secrets in `.env`; do not commit (`.gitignore` includes `.env`).
- **Local development**: Run agent (in-memory sessions) + UI with `./scripts/dev-local.sh`. For deployment, run Session Service + PostgreSQL and set the agent’s `SESSION_SERVICE_URL` to Session Service.
- **Deployment**: Session Service talks to the DB; the agent and UI use Session Service (and agent) APIs.
