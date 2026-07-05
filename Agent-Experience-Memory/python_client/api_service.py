from __future__ import annotations

import os
from typing import Any

import requests
from fastapi import FastAPI
from pydantic import BaseModel, Field

from python_client.error_collector import record_error
from python_client.memory_client import ExperienceMemoryClient

SERVICE_NAME = "agent-experience-memory-api"
DEFAULT_CPP_SERVICE_URL = "http://127.0.0.1:8080"

app = FastAPI(title="Agent Experience Memory API")

os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
os.environ.setdefault("no_proxy", "127.0.0.1,localhost")


def request_without_proxy() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def get_cpp_service_url() -> str:
    return os.getenv("CPP_MEMORY_SERVICE_URL", DEFAULT_CPP_SERVICE_URL).rstrip("/")


class SearchContextRequest(BaseModel):
    query: str
    top_k: int = Field(default=3, ge=1)
    min_score: float = Field(default=0.25, ge=0.0)


class RecordErrorRequest(BaseModel):
    task_type: str
    user_query: str
    tool_name: str
    error_message: str
    context: dict[str, Any] | None = None
    run_id: str | None = None


def sanitize_memory(memory: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": memory.get("id"),
        "title": memory.get("title"),
        "task_type": memory.get("task_type"),
        "prompt_hint": memory.get("prompt_hint"),
        "score": memory.get("score"),
        "importance": memory.get("importance"),
    }


@app.get("/health")
def health() -> dict[str, Any]:
    cpp_service_url = get_cpp_service_url()
    cpp_health: dict[str, Any] | None = None
    warning = ""

    try:
        response = request_without_proxy().get(f"{cpp_service_url}/health", timeout=5)
        response.raise_for_status()
        cpp_health = response.json()
    except Exception as exc:
        warning = f"failed to check C++ Memory Service health: {exc}"

    return {
        "ok": True,
        "service": SERVICE_NAME,
        "cpp_service_url": cpp_service_url,
        "cpp_health": cpp_health,
        "warning": warning,
    }


@app.post("/memory/search_context")
def search_context(payload: SearchContextRequest) -> dict[str, Any]:
    try:
        client = ExperienceMemoryClient(service_url=get_cpp_service_url())
        memories = client.search(payload.query, payload.top_k, payload.min_score)
        context = client.build_prompt_context(memories)
        sanitized_memories = [sanitize_memory(memory) for memory in memories]
        warning = "no matched memories" if not sanitized_memories else ""

        return {
            "ok": True,
            "context": context,
            "memories": sanitized_memories,
            "warning": warning,
        }
    except Exception as exc:
        return {
            "ok": False,
            "context": "",
            "memories": [],
            "warning": str(exc),
        }


@app.post("/memory/record_error")
def record_memory_error(payload: RecordErrorRequest) -> dict[str, Any]:
    try:
        error_log_id = record_error(
            task_type=payload.task_type,
            user_query=payload.user_query,
            tool_name=payload.tool_name,
            error=payload.error_message,
            context=payload.context,
            run_id=payload.run_id,
        )
        return {
            "ok": True,
            "error_log_id": error_log_id,
            "warning": "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "error_log_id": None,
            "warning": str(exc),
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("python_client.api_service:app", host="0.0.0.0", port=8090, reload=False)
