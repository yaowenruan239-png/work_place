from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


class MemoryStore:
    def __init__(self, memory_dir: str | Path = "memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.history_path = self.memory_dir / "task_history.jsonl"
        self.profile_path = self.memory_dir / "user_profile.json"
        self.preference_path = self.memory_dir / "chart_preference.json"
        self.cursor_path = self.memory_dir / ".cursor"
        self._lock = threading.Lock()
        self._cursor = self._load_cursor()
        self._ensure_json_file(self.profile_path)
        self._ensure_json_file(self.preference_path)

    def save_task(self, record: dict[str, Any]) -> int:
        with self._lock:
            cursor = self._cursor + 1
            entry = {
                "cursor": cursor,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "run_id": record.get("run_id", ""),
                "mode": record.get("mode", ""),
                "csv_name": record.get("csv_name", ""),
                "query": record.get("query", ""),
                "rows": record.get("rows"),
                "columns": record.get("columns"),
                "chart_count": record.get("chart_count", 0),
                "chart_types": record.get("chart_types", []),
                "report_path": record.get("report_path"),
                "chart_paths": record.get("chart_paths", []),
                "success": record.get("success", True),
                "error": record.get("error"),
            }
            for key, value in record.items():
                entry.setdefault(key, value)

            with self.history_path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(entry, ensure_ascii=False) + "\n")

            self._cursor = cursor
            self.cursor_path.write_text(str(cursor), encoding="utf-8")
            chart_types = entry.get("chart_types") or []
            if chart_types:
                self.update_chart_preference(chart_types, mode=str(entry.get("mode") or ""))
            return cursor

    def get_recent_tasks(self, limit: int = 5) -> list[dict[str, Any]]:
        tasks = self._read_all_tasks()
        return tasks[-limit:][::-1]

    def get_tasks_by_mode(self, mode: str) -> list[dict[str, Any]]:
        return [task for task in self.get_recent_tasks(1000) if task.get("mode") == mode]

    def get_tasks_by_chart_type(self, chart_type: str) -> list[dict[str, Any]]:
        return [
            task
            for task in self.get_recent_tasks(1000)
            if chart_type in (task.get("chart_types") or [])
        ]

    def update_chart_preference(self, chart_types: list[str], mode: str = "") -> None:
        preference = self.load_chart_preference()
        counts = preference.get("chart_type_counts")
        if not isinstance(counts, dict):
            counts = {}
        for chart_type in chart_types:
            if not chart_type:
                continue
            counts[chart_type] = int(counts.get(chart_type, 0)) + 1
        preference["chart_type_counts"] = counts
        preference["last_used_chart_types"] = list(chart_types)
        if mode:
            preference["preferred_report_mode"] = mode
        preference["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.save_chart_preference(preference)

    def load_user_profile(self) -> dict[str, Any]:
        return self._read_json(self.profile_path)

    def save_user_profile(self, profile: dict[str, Any]) -> None:
        self._write_json(self.profile_path, profile)

    def load_chart_preference(self) -> dict[str, Any]:
        return self._read_json(self.preference_path)

    def save_chart_preference(self, preference: dict[str, Any]) -> None:
        self._write_json(self.preference_path, preference)

    def build_memory_context(self, query: str, limit: int = 5) -> str:
        tasks = self.get_recent_tasks(limit)
        profile = self.load_user_profile()
        preference = self.load_chart_preference()
        if not tasks and not profile and not preference:
            return "暂无历史记忆。"

        lines = ["以下是用户最近的数据分析任务摘要，可作为风格和偏好参考："]
        for index, task in enumerate(tasks, start=1):
            chart_types = ", ".join(task.get("chart_types") or []) or "无图表"
            lines.append(
                f"{index}. mode={task.get('mode')}，文件={task.get('csv_name')}，"
                f"问题={task.get('query')}，图表={chart_types}。"
            )
        if profile:
            lines.append(f"用户偏好：{json.dumps(profile, ensure_ascii=False)}")
        if preference:
            chart_counts = preference.get("chart_type_counts")
            if isinstance(chart_counts, dict) and chart_counts:
                top_charts = sorted(chart_counts.items(), key=lambda item: item[1], reverse=True)[:3]
                chart_text = "，".join(f"{name}({count})" for name, count in top_charts)
                lines.append(f"常用图表偏好：{chart_text}。")
            lines.append(f"图表偏好：{json.dumps(preference, ensure_ascii=False)}")
        if query:
            lines.append(f"本次问题：{query}")
        lines.append("请参考这些偏好，但不要编造数据中不存在的事实。")
        return "\n".join(lines)

    def _read_all_tasks(self) -> list[dict[str, Any]]:
        if not self.history_path.exists():
            return []

        tasks: list[dict[str, Any]] = []
        for line in self.history_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                tasks.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return tasks

    def _load_cursor(self) -> int:
        try:
            return int(self.cursor_path.read_text(encoding="utf-8").strip())
        except (FileNotFoundError, ValueError):
            return max((int(task.get("cursor", 0)) for task in self._read_all_tasks()), default=0)

    @staticmethod
    def _ensure_json_file(path: Path) -> None:
        if not path.exists():
            path.write_text("{}\n", encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
