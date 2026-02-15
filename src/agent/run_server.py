#!/usr/bin/env python3
"""에이전트 API 서버 (Session Service: in-memory 또는 SESSION_SERVICE_URL 원격).
로컬: SESSION_USE_MEMORY=true → in-memory 세션 + 세션 CRUD 노출.
배포: SESSION_SERVICE_URL 설정 → 원격 세션 사용, /run 만 노출 (세션 CRUD는 Session Service).
"""
import asyncio
import os
import logging
import time
import uuid
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from block_diagram_agent import get_llm_info, root_agent
from google.adk.runners import Runner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _session_service():
    """에이전트 및 세션 서비스 결정 (env 기반)."""
    if os.getenv("SESSION_USE_MEMORY", "").lower() in ("true", "1"):
        logger.info("Using in-memory session (SESSION_USE_MEMORY). Suitable for local dev only.")
        from google.adk.sessions import InMemorySessionService
        return InMemorySessionService()
    url = os.getenv("SESSION_SERVICE_URL", "").strip()
    if url:
        logger.info("Using remote session service: %s", url)
        from sessionclient import RemoteSessionService
        return RemoteSessionService(url)
    raise SystemExit(
        "session backend required: set SESSION_USE_MEMORY=true for local dev, "
        "or SESSION_SERVICE_URL for session service (e.g. http://localhost:8081)"
    )


# 앱 이름 (UI app.js와 동일). Runner에는 app 또는 (app_name + agent) 필수.
APP_NAME = "diagram_agent"

# 앱 생성 시점에 runner/session_service 고정 (env 기반)
_session_svc = _session_service()
_runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=_session_svc)
_use_in_memory = os.getenv("SESSION_USE_MEMORY", "").lower() in ("true", "1")

# 기동 시 사용 중인 LLM 로그
_llm_info = get_llm_info()
logger.info("LLM: %s", _llm_info)

app = FastAPI(title="Block Diagram Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _content_from_parts(parts: list) -> Any:
    """newMessage.parts -> ADK Content (또는 호환 구조)."""
    try:
        from google.genai import types
        return types.Content(role="user", parts=[types.Part(text=p.get("text", "")) for p in parts if "text" in p])
    except Exception:
        return {"role": "user", "parts": parts}


def _make_user_message_event(content: Any) -> Any:
    """Minimal event for the current user message (author=user). Used to pre-append when using RemoteSessionService."""
    return SimpleNamespace(
        id=uuid.uuid4().hex[:12],
        timestamp=time.time(),
        invocation_id="",
        branch="",
        author="user",
        content=content,
        actions={},
        partial=False,
        turn_complete=False,
        interrupted=False,
        long_running_tool_ids=[],
        error_code="",
        error_message="",
        grounding_metadata=None,
    )


@app.post("/run")
@app.post("/api/run")
async def run(req: dict) -> list:
    """POST /run 또는 /api/run — 에이전트 실행, 이벤트 목록 반환."""
    user_id = req.get("userId", "default")
    session_id = req.get("sessionId", "default")
    new_message = req.get("newMessage") or {}
    parts = new_message.get("parts") or [{"text": ""}]
    content = _content_from_parts(parts)
    try:
        # RemoteSessionService: Runner가 대화를 session.events만으로 구성하는 경우 첫 턴에 사용자 메시지가
        # 비어 있어 LLM에 전달되지 않는 문제를 피하기 위해, run 전에 사용자 메시지를 세션에 이벤트로 추가.
        if not _use_in_memory:
            session = await _session_svc.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
            user_event = _make_user_message_event(content)
            await _session_svc.append_event(session, user_event)
        run_fn = getattr(_runner, "run_async", None) or getattr(_runner, "run", None)
        result = run_fn(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        )
        if asyncio.iscoroutine(result):
            events = await result
        elif hasattr(result, "__anext__"):
            # async generator
            events = []
            async for ev in result:
                events.append(ev)
        else:
            events = result if isinstance(result, list) else list(result)
    except Exception as e:
        logger.exception("run failed")
        raise HTTPException(status_code=500, detail=str(e))
    # 이벤트를 REST 형식(camelCase 등)으로 직렬화
    out = []
    for ev in events:
        if hasattr(ev, "model_dump"):
            out.append(ev.model_dump())
        elif hasattr(ev, "__dict__"):
            out.append(_event_to_dict(ev))
        else:
            out.append(ev)
    return out


def _event_to_dict(ev: Any) -> dict:
    d = {}
    for k in ("id", "timestamp", "invocation_id", "branch", "author", "content", "actions", "partial", "turn_complete"):
        v = getattr(ev, k, None)
        if v is not None:
            key = "invocationId" if k == "invocation_id" else k
            d[key] = v
    return d


# ----- In-memory 일 때만 세션 CRUD 노출 (UI가 같은 origin 사용). 경로: /api/apps/... -----
@app.get("/api/apps/{app_name}/users/{user_id}/sessions")
@app.get("/apps/{app_name}/users/{user_id}/sessions")
async def list_sessions(app_name: str, user_id: str):
    if not _use_in_memory:
        raise HTTPException(status_code=404, detail="Session API is on Session Service")
    sessions = await _session_svc.list_sessions(app_name=app_name, user_id=user_id)
    return [_session_to_rest(s) for s in sessions]


@app.post("/api/apps/{app_name}/users/{user_id}/sessions")
@app.post("/apps/{app_name}/users/{user_id}/sessions")
async def create_session(app_name: str, user_id: str, body: dict | None = None):
    if not _use_in_memory:
        raise HTTPException(status_code=404, detail="Session API is on Session Service")
    body = body or {}
    state = body.get("state") or {}
    sess = await _session_svc.create_session(app_name=app_name, user_id=user_id, state=state, session_id=None)
    return _session_to_rest(sess)


@app.post("/api/apps/{app_name}/users/{user_id}/sessions/{session_id}")
@app.post("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def create_session_with_id(app_name: str, user_id: str, session_id: str, body: dict | None = None):
    if not _use_in_memory:
        raise HTTPException(status_code=404, detail="Session API is on Session Service")
    body = body or {}
    state = body.get("state") or {}
    sess = await _session_svc.create_session(
        app_name=app_name, user_id=user_id, state=state, session_id=session_id
    )
    return _session_to_rest(sess)


@app.get("/api/apps/{app_name}/users/{user_id}/sessions/{session_id}")
@app.get("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def get_session(app_name: str, user_id: str, session_id: str):
    if not _use_in_memory:
        raise HTTPException(status_code=404, detail="Session API is on Session Service")
    sess = await _session_svc.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    return _session_to_rest(sess)


@app.delete("/api/apps/{app_name}/users/{user_id}/sessions/{session_id}")
@app.delete("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def delete_session(app_name: str, user_id: str, session_id: str):
    if not _use_in_memory:
        raise HTTPException(status_code=404, detail="Session API is on Session Service")
    await _session_svc.delete_session(app_name=app_name, user_id=user_id, session_id=session_id)
    return None


@app.post("/api/apps/{app_name}/users/{user_id}/sessions/{session_id}/events")
@app.post("/apps/{app_name}/users/{user_id}/sessions/{session_id}/events")
async def append_event(app_name: str, user_id: str, session_id: str, body: dict):
    if not _use_in_memory:
        raise HTTPException(status_code=404, detail="Session API is on Session Service")
    sess = await _session_svc.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    # REST Event -> ADK Event 변환 필요; 여기서는 최소 구현 (stateDelta 등만 반영하려면 이벤트 생성)
    event = _rest_to_event(body)
    await _session_svc.append_event(sess, event)
    return None


def _session_to_rest(s: Any) -> dict:
    return {
        "id": getattr(s, "id", s.id if hasattr(s, "id") else ""),
        "appName": getattr(s, "app_name", s.app_name if hasattr(s, "app_name") else ""),
        "userId": getattr(s, "user_id", s.user_id if hasattr(s, "user_id") else ""),
        "lastUpdateTime": getattr(s, "last_update_time", 0),
        "state": getattr(s, "state", {}),
        "events": getattr(s, "events", []),
    }


def _rest_to_event(body: dict) -> Any:
    """REST 이벤트 body를 ADK Event 유사 객체로 (append_event용)."""
    from types import SimpleNamespace
    return SimpleNamespace(
        id=body.get("id", ""),
        timestamp=body.get("time", 0),
        invocation_id=body.get("invocationId", ""),
        branch=body.get("branch", ""),
        author=body.get("author", ""),
        content=body.get("content"),
        actions=body.get("actions") or {},
    )


@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok", "llm": get_llm_info()}


@app.get("/list-apps")
def list_apps():
    return [APP_NAME]


def main():
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
