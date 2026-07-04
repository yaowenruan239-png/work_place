from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from langchain_core.tools import BaseTool

from src.experience_memory_adapter import safe_tool_call
from src.skills.registry import SkillRegistry


class FlexibleToolArgs(BaseModel):
    model_config = ConfigDict(extra="allow")


class DynamicSkillTool(BaseTool):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    registry: SkillRegistry = Field(exclude=True)
    context: "AgentRuntimeContext" = Field(exclude=True)
    skill_name: str = Field(exclude=True)

    def _parse_input(self, tool_input: str | dict[str, Any], tool_call_id: str | None = None) -> str | dict[str, Any]:
        return tool_input

    def _run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raw_args: dict[str, Any]
        if args and isinstance(args[0], dict):
            raw_args = dict(args[0])
        else:
            raw_args = dict(kwargs)
        normalized = _normalize_args(self.skill_name, raw_args, self.context)
        call_context = _build_error_context(self.skill_name, normalized, self.context)
        result = safe_tool_call(
            self.registry.call,
            tool_name=self.skill_name,
            task_type="csv_analysis",
            user_query=self.context.query,
            context=call_context,
            name=self.skill_name,
            **normalized,
        )
        _merge_result(self.skill_name, result, self.context)
        self.context.tool_results.append(
            {
                "skill": self.skill_name,
                "args": normalized,
                "success": bool(result.get("success")),
                "result": result,
            }
        )
        return result


@dataclass
class AgentRuntimeContext:
    run_id: str
    csv_path: str
    query: str
    profile: dict[str, Any] = field(default_factory=dict)
    charts: list[dict[str, Any]] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    markdown: str = ""
    report_path: str = ""
    pdf_path: str | None = None
    html_path: str | None = None
    errors: list[str] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)

    def to_state_update(self) -> dict[str, Any]:
        update: dict[str, Any] = {
            "dataframe_profile": self.profile,
            "generated_charts": self.charts,
            "analysis_insights": self.insights,
            "report_markdown": self.markdown,
            "report_path": self.report_path,
            "pdf_path": self.pdf_path,
            "html_path": self.html_path,
            "errors": self.errors,
        }
        return {key: value for key, value in update.items() if value not in ({}, [], "")}


def build_langchain_tools(registry: SkillRegistry, context: AgentRuntimeContext) -> list[BaseTool]:
    tools: list[BaseTool] = []
    for skill_info in registry.list_skills():
        name = skill_info["name"]
        description = skill_info.get("description") or name
        tools.append(
            DynamicSkillTool(
                name=name,
                description=description,
                registry=registry,
                context=context,
                skill_name=name,
            )
        )
    return tools


def _normalize_args(skill_name: str, args: dict[str, Any], context: AgentRuntimeContext) -> dict[str, Any]:
    normalized = dict(args or {})
    normalized.setdefault("run_id", context.run_id)
    normalized.setdefault("csv_path", context.csv_path)
    normalized.setdefault("query", context.query)
    if skill_name in {"suggest_chart", "generate_insight", "draft_markdown_report", "export_pdf"}:
        normalized.setdefault("profile", context.profile)
    if skill_name in {"generate_insight", "draft_markdown_report", "export_pdf"}:
        normalized.setdefault("charts", context.charts)
    if skill_name in {"draft_markdown_report", "export_pdf"}:
        normalized.setdefault("insights", context.insights)
    if skill_name == "plot_chart_batch":
        normalized.setdefault("plans", normalized.get("plans") or [])
    if skill_name == "export_pdf":
        normalized.setdefault("markdown", context.markdown)
    return {key: value for key, value in normalized.items() if value is not None}


def _build_error_context(skill_name: str, args: dict[str, Any], context: AgentRuntimeContext) -> dict[str, Any]:
    profile = context.profile or {}
    chart_spec = args if skill_name in {"plot_chart", "plot_chart_batch"} else args.get("chart_spec")
    return {
        "run_id": context.run_id,
        "csv_path": context.csv_path,
        "user_query": context.query,
        "tool_name": skill_name,
        "tool_args": args,
        "columns": profile.get("columns") or profile.get("column_names"),
        "dtypes": profile.get("dtypes") or profile.get("column_types"),
        "chart_spec": chart_spec,
    }


def _merge_result(skill_name: str, result: dict[str, Any], context: AgentRuntimeContext) -> None:
    if skill_name == "profile_csv" and result.get("success"):
        context.profile = result
    elif skill_name == "suggest_chart" and result.get("recommended"):
        context.tool_results.append({"skill": skill_name, "recommended": result.get("recommended")})
    elif skill_name == "plot_chart" and result.get("success"):
        context.charts.append(result)
    elif skill_name == "plot_chart_batch" and result.get("charts"):
        context.charts = result.get("charts", [])
    elif skill_name == "generate_insight" and result.get("insights"):
        context.insights = result.get("insights", [])
    elif skill_name == "draft_markdown_report" and result.get("markdown"):
        context.markdown = result.get("markdown", "")
    elif skill_name == "export_pdf":
        context.report_path = result.get("report_path", "")
        context.pdf_path = result.get("pdf_path")
        context.html_path = result.get("html_path")
    if result.get("error"):
        context.errors.append(str(result["error"]))
