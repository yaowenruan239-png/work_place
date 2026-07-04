from __future__ import annotations

from typing import Any


def thought_from_log(log: str | None) -> str:
    text = (log or "").strip()
    if text.startswith("Thought:"):
        return text.removeprefix("Thought:").strip()
    return text


def steps_from_intermediate(intermediate_steps: list[Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for index, item in enumerate(intermediate_steps or [], start=1):
        if not isinstance(item, tuple) or len(item) != 2:
            continue
        action, observation = item
        steps.append(
            {
                "step_index": index,
                "thought": thought_from_log(getattr(action, "log", "")),
                "action": getattr(action, "tool", ""),
                "action_input": getattr(action, "tool_input", {}),
                "observation": observation,
                "success": not (isinstance(observation, dict) and observation.get("success") is False),
                "error": observation.get("error") if isinstance(observation, dict) else None,
            }
        )
    return steps
