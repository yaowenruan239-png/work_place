from src.graph.state import GraphState
from src.memory.store import MemoryStore


def finalize(state: GraphState) -> GraphState:
    charts = state.get("generated_charts", [])
    profile = state.get("dataframe_profile", {})
    state["status"] = "completed" if not state.get("errors") else "fallback"
    MemoryStore().save_task(
        {
            "run_id": state.get("run_id"),
            "mode": state.get("mode"),
            "csv_name": state.get("csv_name"),
            "query": state.get("user_query"),
            "rows": profile.get("rows"),
            "columns": profile.get("columns"),
            "chart_count": len(charts),
            "chart_types": [chart.get("chart_type") for chart in charts if chart.get("chart_type")],
            "chart_paths": [chart.get("path") for chart in charts if chart.get("path")],
            "report_path": state.get("report_path"),
            "success": state["status"] in {"completed", "fallback"},
            "error": "; ".join(state.get("errors", [])) or None,
        }
    )
    return state


def finalize_error(state: GraphState) -> GraphState:
    state["status"] = "error"
    return finalize(state)
