from src.graph.state import GraphState
from src.skills.export_pdf import ExportPDFSkill


def export_report(state: GraphState) -> GraphState:
    result = ExportPDFSkill().run(
        run_id=state["run_id"],
        markdown=state.get("report_markdown", ""),
        profile=state.get("dataframe_profile", {}),
        charts=state.get("generated_charts", []),
        insights=state.get("analysis_insights", []),
        query=state.get("user_query", ""),
    )
    state["report_path"] = result.get("report_path", "")
    state["pdf_path"] = result.get("pdf_path")
    state["html_path"] = result.get("html_path")
    if result.get("error"):
        state.setdefault("errors", []).append(result["error"])
    return state
