from __future__ import annotations

import json
from typing import Any

from src.llm.client import LLMClient
from src.llm.prompts import REPORT_PROMPT
from src.skills.base import BaseSkill


class DraftMarkdownReportSkill(BaseSkill):
    name = "draft_markdown_report"
    description = "生成完整中文 Markdown 数据分析报告。"
    args_schema = {"type": "object", "properties": {"profile": {"type": "object"}, "charts": {"type": "array"}}, "required": ["profile"]}

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def run(self, **kwargs: Any) -> dict[str, Any]:
        try:
            markdown = self.llm.chat([
                {"role": "system", "content": REPORT_PROMPT},
                {"role": "user", "content": json.dumps(kwargs, ensure_ascii=False)[:10000]},
            ])
        except Exception:
            markdown = self._fallback_report(kwargs)
        return {"success": True, "markdown": markdown}

    def _fallback_report(self, data: dict[str, Any]) -> str:
        profile = data.get("profile", {})
        charts = data.get("charts", [])
        insights = data.get("insights", [])
        insight_lines = "\n".join(f"- {item}" for item in insights) or "- 当前报告基于数据画像和图表自动生成。"
        chart_sections = []
        for index, chart in enumerate(charts, start=1):
            title = chart.get("title", f"图表 {index}")
            path = chart.get("path", "")
            observation = insights[(index - 1) % len(insights)] if insights else "该图展示了数据中的主要分布、对比或关联模式。"
            chart_sections.append(
                f"### 图表 {index}：{title}\n\n"
                f"![{title}]({path})\n\n"
                f"**观察：** {observation}\n\n"
                f"**建议：** 结合业务背景进一步检查该图中的高值、低值、异常值和结构性差异。"
            )
        return f"""# 数据分析报告

## 1. 执行摘要

本报告围绕“{data.get('query', '分析 CSV 数据。')}”展开，基于 {profile.get('rows', 0)} 行、{profile.get('columns', 0)} 列数据生成画像、图表和行动建议。

## 2. 关键指标

- 记录数：{profile.get('rows', 0)}
- 字段数：{profile.get('columns', 0)}
- 数值字段：{', '.join(profile.get('numeric_columns', [])) or '无'}
- 图表数：{len(charts)}

## 3. 核心发现

{insight_lines}

## 4. 图文分析

{chr(10).join(chart_sections) or '未生成图表。'}

## 5. 行动建议

- 优先关注图表中呈现的高值、低值和异常波动。
- 将数据发现与具体业务周期、区域或产品策略结合验证。
- 对关键指标建立持续监控，避免只基于单次 CSV 快照做结论。

## 6. 局限性说明

本报告仅基于上传 CSV 的现有字段和记录生成，不代表外部事实。
"""
