from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    name: str
    description: str
    args_schema: dict[str, Any]

    @abstractmethod
    def run(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def fallback_run(self, **kwargs: Any) -> dict[str, Any]:
        return {"success": False, "error": f"Skill '{self.name}' failed and has no fallback."}
