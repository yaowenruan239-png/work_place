from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PlannerStepTrace:
    step_index: int
    thought: str
    tool_name: str
    tool_args: dict[str, Any] = field(default_factory=dict)
    normalized_args: dict[str, Any] = field(default_factory=dict)
    result_summary: str = ""
    success: bool = False
    error: str | None = None
    raw_model_output: str = ""
    phase: str = "tool_call"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
