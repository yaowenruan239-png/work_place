from __future__ import annotations

import json
from typing import Any

from src.llm.client import LLMClient
from src.llm.prompts import INSIGHT_PROMPT
from src.skills.base import BaseSkill


class GenerateInsightSkill(BaseSkill):
    name = "generate_insight"
    description = "基于 profile、图表和用户目标生成中文洞察。"
    args_schema = {"type": "object", "properties": {"profile": {"type": "object"}}, "required": ["profile"]}

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        fallback = self._fallback(kwargs.get("profile", {}), kwargs.get("charts", []))
        try:
            text = self.llm.chat([
                {"role": "system", "content": INSIGHT_PROMPT},
                {"role": "user", "content": json.dumps(kwargs, ensure_ascii=False)[:6000]},
            ])
            insights = [line.strip().lstrip("- ").strip() for line in text.splitlines() if line.strip()]
            return {"success": True, "insights": insights or fallback, "text": text}
        except Exception:
            return {"success": True, "insights": fallback, "text": "\n".join(f"- {item}" for item in fallback)}

    def _fallback(self, profile: dict[str, Any], charts: list[dict[str, Any]]) -> list[str]:
        return [
            f"数据集包含 {profile.get('rows', 0)} 行、{profile.get('columns', 0)} 列。",
            f"数值字段包括：{', '.join(profile.get('numeric_columns', [])) or '无'}。",
            f"本次生成了 {len(charts)} 张图表用于辅助分析。",
        ]
