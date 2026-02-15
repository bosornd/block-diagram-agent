"""Session Service HTTP client — ADK REST API (same paths as Go sessionclient).

Comparison with InMemorySessionService (ADK built-in):
- InMemory: create_session() generates a session ID (if not given), stores Session in process
  memory, returns it. No network, no DB; lost on restart.
- RemoteSessionService: create_session() POSTs to Session Service (e.g. /api/apps/.../sessions),
  which writes to PostgreSQL and returns REST JSON; we convert to ADK Session and return.
  Persistent; used when SESSION_SERVICE_URL is set.
"""
import logging
from typing import Any
from urllib.parse import urljoin

import httpx

from .models import event_to_rest, rest_to_session

logger = logging.getLogger(__name__)

try:
    from google.adk.sessions import BaseSessionService
except ImportError:
    BaseSessionService = object

class RemoteSessionService(BaseSessionService):
    """SessionService that forwards to Session Service HTTP API.
    Subclasses BaseSessionService so InvocationContext validation accepts it.
    Paths: /api/apps/{app_name}/users/{user_id}/sessions, .../events
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._api = f"{self._base}/api"

    def _path(self, *parts: str) -> str:
        return urljoin(self._api + "/", "/".join(parts))

    async def create_session(
        self,
        app_name: str,
        user_id: str,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Any:
        state = state or {}
        url = self._path("apps", app_name, "users", user_id, "sessions")
        if session_id:
            url = self._path("apps", app_name, "users", user_id, "sessions", session_id)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(url, json={"state": state})
            r.raise_for_status()
            return rest_to_session(r.json())

    async def get_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> Any:
        url = self._path("apps", app_name, "users", user_id, "sessions", session_id)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(url)
            r.raise_for_status()
            return rest_to_session(r.json())

    async def list_sessions(
        self,
        app_name: str,
        user_id: str,
    ) -> list:
        url = self._path("apps", app_name, "users", user_id, "sessions")
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                return [rest_to_session(s) for s in data]
            return []

    async def delete_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
    ) -> None:
        url = self._path("apps", app_name, "users", user_id, "sessions", session_id)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.delete(url)
            r.raise_for_status()

    async def append_event(self, session: Any, event: Any) -> None:
        """세션에 이벤트 추가 (POST .../sessions/{id}/events)."""
        app_name = getattr(session, "app_name", None)
        user_id = getattr(session, "user_id", None)
        session_id = getattr(session, "id", None)
        if not all([app_name, user_id, session_id]):
            raise ValueError("session must have app_name, user_id, id")
        url = self._path("apps", app_name, "users", user_id, "sessions", session_id, "events")
        body = event_to_rest(event)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            r = await client.post(url, json=body)
            if r.status_code not in (200, 204):
                r.raise_for_status()
