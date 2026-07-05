from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    run_id: str
    mode: str
    csv_path: str
    csv_name: str
    user_query: str
    dataframe_profile: dict[str, Any]
    memory_context: str
    route_decision: dict[str, Any]
    chart_plan: dict[str, Any] | list[dict[str, Any]]
    generated_charts: list[dict[str, Any]]
    chart_explanations: list[str]
    analysis_insights: list[str]
    report_markdown: str
    report_path: str
    html_path: str | None
    pdf_path: str | None
    final_answer: str
    experience_context: str
    experience_memory_warning: str
    experience_memories: list[dict[str, Any]]
    planner_steps: list[dict[str, Any]]
    agent_steps: list[dict[str, Any]]
    errors: list[str]
    retry_count: int
    status: str
