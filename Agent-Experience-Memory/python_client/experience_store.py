from __future__ import annotations

import json
from typing import Any

from python_client.db import execute, fetch_all
from python_client.embedding import build_memory_text, embed_text


def add_experience(
    title: str,
    task_type: str,
    problem_pattern: str,
    cause: str,
    solution: str,
    prompt_hint: str,
    importance: int = 3,
) -> int:
    memory_id = execute(
        """
        INSERT INTO experience_memories (
            title,
            task_type,
            problem_pattern,
            cause,
            solution,
            prompt_hint,
            importance
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            title,
            task_type,
            problem_pattern,
            cause,
            solution,
            prompt_hint,
            importance,
        ),
    )

    memory = {
        "id": memory_id,
        "title": title,
        "task_type": task_type,
        "problem_pattern": problem_pattern,
        "cause": cause,
        "solution": solution,
        "prompt_hint": prompt_hint,
        "importance": importance,
    }
    vector = embed_text(build_memory_text(memory))

    execute(
        """
        INSERT INTO memory_vectors (memory_id, dim, vector_json)
        VALUES (%s, %s, %s)
        """,
        (memory_id, len(vector), json.dumps(vector, ensure_ascii=False)),
    )
    return memory_id


def list_memories() -> list[dict[str, Any]]:
    return fetch_all(
        """
        SELECT
            em.id,
            em.title,
            em.task_type,
            em.problem_pattern,
            em.cause,
            em.solution,
            em.prompt_hint,
            em.importance,
            em.hit_count,
            em.created_at,
            em.updated_at,
            mv.dim,
            mv.vector_json,
            mv.created_at AS vector_created_at
        FROM experience_memories em
        JOIN memory_vectors mv ON mv.memory_id = em.id
        ORDER BY em.id ASC
        """
    )


def get_memories_by_ids(ids: list[int]) -> list[dict[str, Any]]:
    if not ids:
        return []

    placeholders = ", ".join(["%s"] * len(ids))
    rows = fetch_all(
        f"""
        SELECT
            id,
            title,
            task_type,
            problem_pattern,
            cause,
            solution,
            prompt_hint,
            importance,
            hit_count,
            created_at,
            updated_at
        FROM experience_memories
        WHERE id IN ({placeholders})
        """,
        tuple(ids),
    )
    rows_by_id = {int(row["id"]): row for row in rows}
    return [rows_by_id[memory_id] for memory_id in ids if memory_id in rows_by_id]


def increase_hit_count(memory_id: int) -> None:
    execute(
        """
        UPDATE experience_memories
        SET hit_count = hit_count + 1
        WHERE id = %s
        """,
        (memory_id,),
    )
