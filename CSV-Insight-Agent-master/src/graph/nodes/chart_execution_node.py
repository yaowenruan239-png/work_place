from src.experience_memory_adapter import safe_tool_call
from src.graph.state import GraphState
from src.skills.chart_plot import PlotChartBatchSkill, PlotChartSkill


def execute_chart(state: GraphState) -> GraphState:
    chart_plan = state.get("chart_plan", {})
    result = safe_tool_call(
        PlotChartSkill().run,
        tool_name="plot_chart",
        task_type="csv_analysis",
        user_query=state.get("user_query", ""),
        context=_build_chart_error_context(state, chart_plan),
        csv_path=state["csv_path"],
        run_id=state["run_id"],
        **chart_plan,
    )
    state["generated_charts"] = [result] if result.get("success") else []
    if not result.get("success"):
        state.setdefault("errors", []).append(result.get("error", "chart failed"))
    return state


def execute_chart_batch(state: GraphState) -> GraphState:
    chart_plan = state.get("chart_plan", [])
    result = safe_tool_call(
        PlotChartBatchSkill().run,
        tool_name="plot_chart_batch",
        task_type="csv_analysis",
        user_query=state.get("user_query", ""),
        context=_build_chart_error_context(state, chart_plan),
        csv_path=state["csv_path"],
        run_id=state["run_id"],
        plans=chart_plan,
    )
    state["generated_charts"] = result.get("charts", [])
    if result.get("errors"):
        state.setdefault("errors", []).extend(str(error) for error in result["errors"])
    return state


def _build_chart_error_context(state: GraphState, chart_spec: object) -> dict[str, object]:
    profile = state.get("dataframe_profile", {}) or {}
    return {
        "run_id": state.get("run_id"),
        "csv_path": state.get("csv_path"),
        "user_query": state.get("user_query", ""),
        "tool_name": "plot_chart_batch" if isinstance(chart_spec, list) else "plot_chart",
        "columns": profile.get("columns") or profile.get("column_names"),
        "dtypes": profile.get("dtypes") or profile.get("column_types"),
        "chart_spec": chart_spec,
    }
