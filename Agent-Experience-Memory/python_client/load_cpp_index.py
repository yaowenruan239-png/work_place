from __future__ import annotations

import json
from typing import Any

import requests

from python_client.experience_store import list_memories

CPP_SERVICE_URL = "http://127.0.0.1:8080"


def _post(path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.post(f"{CPP_SERVICE_URL}{path}", json=body or {}, timeout=10)
    response.raise_for_status()
    return response.json()


def clear_index() -> None:
    _post("/index/clear")


def load_all_memories() -> int:
    memories = list_memories()

    for memory in memories:
        vector = json.loads(memory["vector_json"])
        _post(
            "/index/add",
            {
                "memory_id": int(memory["id"]),
                "vector": vector,
            },
        )

    loaded_count = len(memories)
    print(f"loaded {loaded_count} memories into C++ index")
    return loaded_count


def main() -> None:
    clear_index()
    load_all_memories()


if __name__ == "__main__":
    main()
