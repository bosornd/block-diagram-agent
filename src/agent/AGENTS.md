# src/agent — Block Diagram Agent

Diagram-generation agent using Google ADK (Agent Development Kit). Implemented in **Python**; converts user descriptions into Mermaid block/flowchart code.

## Tech Stack

- **Language**: Python 3.10+
- **Framework**: `google-adk` (ADK Python), **LiteLLM** (for local/OpenAI-compatible endpoints)
- **Structured output**: Pydantic `DiagramResponse` (title, message, mermaid) — used by UI and session with `output_schema` / `output_key="diagram"`
- **LLM**: **Selected via env**. If `LLM_BASE_URL` or `KSERVE_URL` is set, that OpenAI-compatible endpoint (e.g. KServe) is used; otherwise Gemini 2.0 Flash.
- **Runtime**: FastAPI + Uvicorn (`run_server.py`), port 8080

## Main Files

| File | Description |
|------|--------------|
| `run_server.py` | Entry point. Chooses session backend (`SESSION_USE_MEMORY` or `SESSION_SERVICE_URL`), creates Runner, exposes `/run` and session CRUD API. |
| `block_diagram_agent/agent.py` | Agent definition. `output_schema=DiagramResponse`, `output_key="diagram"`. |
| `block_diagram_agent/schema.py` | Pydantic `DiagramResponse`: title (session title), message (description text), mermaid (diagram code). |
| `sessionclient/` | Session Service HTTP client. Session CRUD and AppendEvent via ADK REST–compatible paths. |
| `requirements.txt` | google-adk, litellm, pydantic, httpx, fastapi, uvicorn. |
| `Dockerfile` | Python 3.12-slim, `uvicorn run_server:app`. |
| `.env.example` | Example `GOOGLE_API_KEY`. Put real key in `.env` and do not commit. |

## Behavior Summary

- **Env**: **LLM**: If `LLM_BASE_URL` or `KSERVE_URL` is set, use that local (OpenAI-compatible) model; otherwise use `GOOGLE_API_KEY` for Gemini. **Session**: For local dev use `SESSION_USE_MEMORY=true`; for deployment use `SESSION_SERVICE_URL` (e.g. `http://block-diagram-session-service:8081`). The agent does not connect to the DB.
- **Session storage**: Agent is stateless. Sessions, events, and state are handled by calling Session Service HTTP API via `sessionclient.RemoteSessionService`. Session Service persists to PostgreSQL.
- **Structured output**: `output_schema=DiagramResponse`, `output_key="diagram"` for title / message / mermaid. The UI parses the run response and sets session title via Session Service events API (`stateDelta.title`).
- **Tools**: None at present. Tools can be added to the agent if needed.

## Local Run

**Install dependencies** (once):

```bash
cd src/agent && pip install -r requirements.txt
```

**Without DB (development)** — from project root:

```bash
# For Gemini
export GOOGLE_API_KEY=...
# Or for local LLM (e.g. KServe)
export LLM_BASE_URL=http://localhost:8000/v1   # OpenAI-compatible base URL
export SESSION_USE_MEMORY=true
cd src/agent && python -m uvicorn run_server:app --host 0.0.0.0 --port 8080
# http://localhost:8080
```

Or use `./scripts/dev-local.sh` to run agent + UI with in-memory sessions. For local model only, set `LLM_BASE_URL` (or `KSERVE_URL`) and you can omit `GOOGLE_API_KEY`.

**With Session Service** (after starting Session Service locally):

```bash
export SESSION_SERVICE_URL="http://localhost:8081"
cd src/agent && python -m uvicorn run_server:app --host 0.0.0.0 --port 8080
```

## Container

```bash
docker build -t block-diagram-agent src/agent
docker run --rm -p 8080:8080 \
  -e GOOGLE_API_KEY=... \
  -e SESSION_SERVICE_URL="http://session-service:8081" \
  block-diagram-agent
# For local LLM: -e LLM_BASE_URL="http://llm-service/v1" (GOOGLE_API_KEY can be omitted)
```

## Development Notes

- To change agent behavior or prompts, edit the instruction in `block_diagram_agent/agent.py` and `DiagramResponse` in `schema.py`.
- To add ADK tools, register them in `Agent(..., tools=[...])`.
- Sessions go through Session Service. Use `SESSION_USE_MEMORY=true` for local-only; use `SESSION_SERVICE_URL` for deployment.
- Local LLM (e.g. KServe): set `LLM_BASE_URL` or `KSERVE_URL` to the OpenAI-compatible base URL. See `src/k8s/AGENTS.md` (LLM section) for deployment and integration details.
