from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

_EXPERIENCE_MEMORY_ROOT = Path(__file__).resolve().parents[2] / "Agent-Experience-Memory"
if _EXPERIENCE_MEMORY_ROOT.exists():
    root_text = str(_EXPERIENCE_MEMORY_ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)

try:
    from python_client.error_collector import record_error
    from python_client.memory_client import ExperienceMemoryClient
except Exception as import_exc:  # pragma: no cover - optional integration fallback
    record_error = None  # type: ignore[assignment]
    ExperienceMemoryClient = None  # type: ignore[assignment]
    _IMPORT_ERROR: Exception | None = import_exc
else:
    _IMPORT_ERROR = None

memory_client = ExperienceMemoryClient("http://127.0.0.1:8080") if ExperienceMemoryClient else None


def get_experience_context(user_query: str, task_type: str) -> str:
    if memory_client is None:
        if _IMPORT_ERROR is not None:
            print(f"Warning: experience memory client unavailable: {_IMPORT_ERROR}")
        return ""

    search_query = f"任务类型：{task_type}\n用户问题：{user_query}"
    try:
        memories = memory_client.search(search_query, top_k=3, min_score=0.25)
        return memory_client.build_prompt_context(memories)
    except Exception as exc:
        print(f"Warning: experience memory search failed: {exc}")
        return ""


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

        if record_error is None:
            if _IMPORT_ERROR is not None:
                print(f"Warning: experience memory error recorder unavailable: {_IMPORT_ERROR}")
        else:
            try:
                record_error(
                    task_type=task_type,
                    user_query=user_query,
                    tool_name=tool_name,
                    error=exc,
                    context=enriched_context,
                    run_id=str(enriched_context.get("run_id") or "") or None,
                )
            except Exception as record_exc:
                print(f"Warning: experience memory error recording failed: {record_exc}")
        raise
