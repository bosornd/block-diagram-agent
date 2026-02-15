# src/ui — Web UI

Web UI for chatting with the agent and rendering generated Mermaid diagrams.

## Layout

- **Left panel**: Conversation session list + current session chat
  - Create/delete sessions, select from list.
  - Each session corresponds to one diagram.
  - Enter and send messages in the current session; agent responses are shown.
- **Right panel**: Diagram rendered from the current session’s Mermaid code via Mermaid.js.

## Tech Stack

- Plain HTML/CSS/JS. `index.html`, `style.css`, `app.js`.
- [Mermaid.js](https://mermaid.js.org/) via CDN for diagram rendering.
- Session API: list/create/get/delete (`/api/apps/.../sessions`) — if `SESSION_API_BASE` is unset, same URL as agent; if set, can use Session Service or another URL.
- Agent API: run (`/api/run`) — always uses agent URL (`AGENT_API_BASE` or default 8080). The UI parses the response JSON `title` and updates the session title via Session Service `POST .../sessions/{id}/events` with `stateDelta.title`.

## Development Reference

- Agent runs from `src/agent` with `python -m uvicorn run_server:app --port 8080` or in a container on port 8080. API base is `http://localhost:8080` (configurable in header).
- Sessions are stored on the server (PostgreSQL), so the list and conversations persist after refresh.
- How to run: see `src/ui/README.md`.
