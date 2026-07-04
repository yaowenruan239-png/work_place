from __future__ import annotations

from typing import Any

import requests

from python_client.embedding import embed_text
from python_client.experience_store import get_memories_by_ids, increase_hit_count


class ExperienceMemoryClient:
    def __init__(self, service_url: str = "http://127.0.0.1:8080") -> None:
        self.service_url = service_url.rstrip("/")

    def search(self, query: str, top_k: int = 3, min_score: float = 0.25) -> list[dict[str, Any]]:
        query_vector = embed_text(query)
        response = requests.post(
            f"{self.service_url}/index/search",
            json={"vector": query_vector, "top_k": top_k},
            timeout=10,
        )
        response.raise_for_status()

        results = response.json().get("results", [])
        matched_results = [
            result
            for result in results
            if float(result.get("score", 0.0)) >= min_score
        ]
        if not matched_results:
            return []

        scores_by_id = {
            int(result["memory_id"]): float(result["score"])
            for result in matched_results
        }
        memory_ids = list(scores_by_id.keys())
        memories = get_memories_by_ids(memory_ids)

        for memory in memories:
            memory_id = int(memory["id"])
            memory["score"] = scores_by_id[memory_id]
            increase_hit_count(memory_id)

        return memories

    def build_prompt_context(self, memories: list[dict[str, Any]]) -> str:
        if not memories:
            return ""

        lines = ["以下是系统过去执行类似任务时总结出的经验，请优先遵守："]
        for index, memory in enumerate(memories, start=1):
            prompt_hint = str(memory.get("prompt_hint", "")).strip()
            score = float(memory.get("score", 0.0))
            lines.append(f"{index}. {prompt_hint}（相关度：{score:.4f}）")

        return "\n".join(lines)
