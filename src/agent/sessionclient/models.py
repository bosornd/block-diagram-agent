"""Session Service REST API 요청/응답 모델 (ADK 호환 JSON 형식)."""
from typing import Any

# REST API는 camelCase. Session Service(Go)와 동일한 JSON 형식 사용.
# InvocationContext는 session이 ADK Session 인스턴스 또는 검증 가능한 dict를 요구함.

try:
    from google.adk.sessions import Session as AdkSession
except ImportError:
    AdkSession = None

try:
    from google.adk.events import Event as AdkEvent
except ImportError:
    AdkEvent = None


def _snake_to_camel(name: str) -> str:
    """snake_case -> camelCase (일부 필드용)."""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def session_to_rest(session: Any) -> dict[str, Any]:
    """ADK Session-like 객체를 REST JSON 형태로 변환."""
    return {
        "id": getattr(session, "id", None) if hasattr(session, "id") else session.get("id"),
        "appName": getattr(session, "app_name", None) if hasattr(session, "app_name") else session.get("app_name"),
        "userId": getattr(session, "user_id", None) if hasattr(session, "user_id") else session.get("user_id"),
        "lastUpdateTime": getattr(session, "last_update_time", 0) if hasattr(session, "last_update_time") else session.get("last_update_time", 0),
        "events": getattr(session, "events", []) if hasattr(session, "events") else session.get("events", []),
        "state": getattr(session, "state", {}) if hasattr(session, "state") else session.get("state", {}),
    }


def _rest_event_to_adk_event(ev: dict[str, Any]) -> Any | None:
    """Convert REST event dict to ADK Event. Returns None if conversion fails."""
    if not ev or AdkEvent is None:
        return None
    time_val = ev.get("time", 0)
    if isinstance(time_val, (int, float)) and time_val > 1e12:
        time_val = time_val / 1000.0
    adk_ev: dict[str, Any] = {
        "id": ev.get("id", ""),
        "timestamp": time_val,
        "invocation_id": ev.get("invocationId", ""),
        "branch": ev.get("branch", ""),
        "author": ev.get("author", ""),
        "partial": ev.get("partial", False),
        "turn_complete": ev.get("turnComplete", False),
        "interrupted": ev.get("interrupted", False),
        "content": ev.get("content"),
        "long_running_tool_ids": ev.get("longRunningToolIds", []),
        "error_code": ev.get("errorCode", ""),
        "error_message": ev.get("errorMessage", ""),
    }
    if ev.get("actions") is not None:
        adk_ev["actions"] = ev["actions"]
    if ev.get("groundingMetadata") is not None:
        adk_ev["grounding_metadata"] = ev["groundingMetadata"]
    try:
        return AdkEvent(**adk_ev)
    except Exception:
        return None


def rest_to_session(data: dict[str, Any]) -> Any:
    """REST JSON to ADK Session instance so InvocationContext validation passes."""
    events_raw = data.get("events") or []
    state = data.get("state") or {}
    if isinstance(state, list):
        state = {}
    last_update_time = data.get("lastUpdateTime", 0)
    if isinstance(last_update_time, (int, float)) and last_update_time > 1e12:
        last_update_time = last_update_time / 1000.0
    events: list[Any] = []
    if AdkEvent is not None:
        for e in events_raw:
            if isinstance(e, dict):
                converted = _rest_event_to_adk_event(e)
                if converted is not None:
                    events.append(converted)
            else:
                events.append(e)
    payload = {
        "id": data.get("id", ""),
        "app_name": data.get("appName", ""),
        "user_id": data.get("userId", ""),
        "last_update_time": last_update_time,
        "state": state,
        "events": events,
    }
    if AdkSession is not None:
        try:
            return AdkSession(**payload)
        except Exception:
            pass
        try:
            if hasattr(AdkSession, "model_validate"):
                return AdkSession.model_validate(payload)
        except Exception:
            pass
        try:
            # Ensure we return an AdkSession so InvocationContext accepts it (events may be empty)
            return AdkSession(**{**payload, "events": []})
        except Exception:
            pass
    return SessionLike(**payload)


def event_to_rest(event: Any) -> dict[str, Any]:
    """ADK Event-like 객체를 REST JSON 형태로 변환 (POST .../events body)."""
    # ADK Event: id, timestamp, invocation_id, author, content, actions (dict 또는 EventActions 객체)
    ts = getattr(event, "timestamp", None)
    time_unix = int(ts) if isinstance(ts, (int, float)) else (ts.timestamp() if hasattr(ts, "timestamp") else 0)
    actions = getattr(event, "actions", None) or {}
    state_delta = _get_attr_or_key(actions, "state_delta", "stateDelta") or {}
    artifact_delta = _get_attr_or_key(actions, "artifact_delta", "artifactDelta") or {}
    return {
        "id": getattr(event, "id", ""),
        "time": time_unix,
        "invocationId": getattr(event, "invocation_id", ""),
        "branch": getattr(event, "branch", ""),
        "author": getattr(event, "author", ""),
        "partial": getattr(event, "partial", False),
        "longRunningToolIds": getattr(event, "long_running_tool_ids", []) or [],
        "content": _to_json_safe(getattr(event, "content", None)),
        "groundingMetadata": _to_json_safe(getattr(event, "grounding_metadata", None)),
        "turnComplete": getattr(event, "turn_complete", False),
        "interrupted": getattr(event, "interrupted", False),
        "errorCode": getattr(event, "error_code", "") or "",
        "errorMessage": getattr(event, "error_message", "") or "",
        "actions": {
            "stateDelta": state_delta,
            "artifactDelta": artifact_delta,
        },
    }


def _get_attr_or_key(obj: Any, attr: str, key: str) -> Any:
    """dict면 .get(key), 객체면 getattr(attr). EventActions 등 둘 다 처리."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(attr) or obj.get(key)
    return getattr(obj, attr, None) or getattr(obj, key, None)


def _to_json_safe(obj: Any) -> Any:
    """객체를 JSON 직렬화 가능한 형태로 변환."""
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(x) for x in obj]
    return obj


class SessionLike:
    """REST Session과 호환되는 세션 객체 (ADK Runner가 사용)."""

    __slots__ = ("id", "app_name", "user_id", "last_update_time", "state", "events")

    def __init__(
        self,
        id: str,
        app_name: str,
        user_id: str,
        last_update_time: float,
        state: dict[str, Any],
        events: list,
    ):
        self.id = id
        self.app_name = app_name
        self.user_id = user_id
        self.last_update_time = last_update_time
        self.state = state
        self.events = events
