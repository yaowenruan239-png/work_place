from typing import Any, Literal

from pydantic import BaseModel, Field


class RouteDecision(BaseModel):
    mode: Literal["quick_chart", "full_report", "planner_loop"]
    reason: str


class ChartPlan(BaseModel):
    chart_type: Literal["line", "bar", "scatter", "histogram", "box", "correlation_heatmap"]
    x_col: str | None = None
    y_col: str | None = None
    title: str
    reason: str | None = None


class MultiChartPlan(BaseModel):
    charts: list[ChartPlan] = Field(min_length=1, max_length=6)


class SafetyResult(BaseModel):
    passed: bool
    issues: list[str] = []
    rewrite_suggestion: str = ""


class PlannerAction(BaseModel):
    thought: str
    tool_name: Literal[
        "profile_csv",
        "suggest_chart",
        "plot_chart",
        "plot_chart_batch",
        "generate_insight",
        "draft_markdown_report",
        "export_pdf",
        "read_recent_memory",
        "save_memory",
        "final_answer",
    ]
    tool_args: dict[str, Any] = {}
