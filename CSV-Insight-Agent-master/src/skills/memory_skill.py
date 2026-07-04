from __future__ import annotations

from typing import Any

from src.memory.store import MemoryStore
from src.skills.base import BaseSkill


class ReadRecentMemorySkill(BaseSkill):
    name = "read_recent_memory"
    description = "读取最近任务历史和用户偏好。"
    args_schema = {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": []}

    def __init__(self, store: MemoryStore | None = None):
        self.store = store or MemoryStore()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return {"success": True, "context": self.store.build_memory_context(kwargs.get("query", ""), kwargs.get("limit", 5))}


class SaveMemorySkill(BaseSkill):
    name = "save_memory"
    description = "保存任务历史。"
    args_schema = {"type": "object", "properties": {"record": {"type": "object"}}, "required": ["record"]}

    def __init__(self, store: MemoryStore | None = None):
        self.store = store or MemoryStore()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        cursor = self.store.save_task(kwargs.get("record", kwargs))
        return {"success": True, "cursor": cursor}
