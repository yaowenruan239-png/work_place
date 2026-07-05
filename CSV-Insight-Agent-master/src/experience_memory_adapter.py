from __future__ import annotations

import os
from typing import Any, Callable

import requests

EXPERIENCE_MEMORY_API_URL = os.getenv("EXPERIENCE_MEMORY_API_URL", "http://127.0.0.1:8090").rstrip("/")

_LAST_WARNING = ""
_LAST_MEMORIES: list[dict[str, Any]] = []


def get_last_experience_memory_warning() -> str:
    return _LAST_WARNING


def get_last_experience_memories() -> list[dict[str, Any]]:
    return _LAST_MEMORIES


def _post_json(path: str, payload: dict[str, Any], timeout: float = 3.0) -> dict[str, Any]:
    session = requests.Session()
    session.trust_env = False
    response = session.post(f"{EXPERIENCE_MEMORY_API_URL}{path}", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_experience_context(user_query: str, task_type: str) -> str:
    global _LAST_WARNING, _LAST_MEMORIES
    _LAST_WARNING = ""
    _LAST_MEMORIES = []

    search_query = f"任务类型：{task_type}\n用户问题：{user_query}"
    payload = {
        "query": search_query,
        "top_k": 3,
        "min_score": 0.25,
    }

    try:
        data = _post_json("/memory/search_context", payload)
    except Exception as exc:
        _LAST_WARNING = f"experience memory api unavailable: {exc}"
        print(f"Warning: {_LAST_WARNING}")
        return ""

    if data.get("ok") is True:
        memories = data.get("memories") or []
        _LAST_MEMORIES = memories if isinstance(memories, list) else []
        context = str(data.get("context") or "")
        if context:
            return context
        _LAST_WARNING = str(data.get("warning") or "experience memory search returned no memories")
        return ""

    _LAST_WARNING = str(data.get("warning") or "experience memory api returned ok=false")
    return ""


def record_tool_error(
    task_type: str,
    user_query: str,
    tool_name: str,
    error: Exception | str,
    context: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> None:
    payload = {
        "task_type": task_type,
        "user_query": user_query,
        "tool_name": tool_name,
        "error_message": str(error),
        "context": context or {},
        "run_id": run_id,
    }

    try:
        data = _post_json("/memory/record_error", payload)
        if data.get("ok") is not True:
            warning = str(data.get("warning") or "experience memory api returned ok=false while recording error")
            print(f"Warning: {warning}")
    except Exception as exc:
        print(f"Warning: experience memory error recording failed: {exc}")


def safe_tool_call(
    tool_func: Callable[..., Any],
    tool_name: str,
    task_type: str,
    user_query: str,
    context: dict[str, Any] | None = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    try:
        return tool_func(*args, **kwargs)
    except Exception as exc:
        enriched_context: dict[str, Any] = dict(context or {})
        enriched_context.setdefault("user_query", user_query)
        enriched_context.setdefault("tool_name", tool_name)
        enriched_context.setdefault("tool_args", {"args": args, "kwargs": kwargs})

        record_tool_error(
            task_type=task_type,
            user_query=user_query,
            tool_name=tool_name,
            error=exc,
            context=enriched_context,
            run_id=str(enriched_context.get("run_id") or "") or None,
        )
        raise
