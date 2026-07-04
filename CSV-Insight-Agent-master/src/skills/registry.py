from __future__ import annotations

from datetime import datetime
from typing import Any

from src.skills.base import BaseSkill


class SkillRegistry:
    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}
        self._call_log: list[dict[str, Any]] = []

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> BaseSkill | None:
        return self._skills.get(name)

    def list_skills(self) -> list[dict[str, Any]]:
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "args_schema": skill.args_schema,
            }
            for skill in self._skills.values()
        ]

    def describe_skills(self) -> str:
        return "\n".join(
            f"- {skill['name']}: {skill['description']} args={skill['args_schema']}"
            for skill in self.list_skills()
        )

    def call(self, name: str, **kwargs: Any) -> dict[str, Any]:
        started = datetime.now()
        skill = self.get(name)
        if not skill:
            result = {
                "success": False,
                "error": f"Unknown skill: {name}",
                "available_skills": list(self._skills),
            }
            self._log(name, kwargs, result, started)
            return result

        try:
            result = skill.run(**kwargs)
        except Exception as exc:
            result = skill.fallback_run(**kwargs)
            result["error"] = f"Skill '{name}' failed: {exc}"
        self._log(name, kwargs, result, started)
        return result

    def get_call_log(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._call_log[-limit:]

    def _log(self, name: str, args: dict[str, Any], result: dict[str, Any], started: datetime) -> None:
        self._call_log.append(
            {
                "timestamp": started.isoformat(timespec="seconds"),
                "skill": name,
                "args": args,
                "success": result.get("success", False),
                "result_preview": str(result)[:500],
                "duration_ms": (datetime.now() - started).total_seconds() * 1000,
            }
        )
