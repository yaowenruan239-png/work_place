from src.graph.state import GraphState
from src.skills.report_draft import DraftMarkdownReportSkill


def draft_report(state: GraphState) -> GraphState:
    result = DraftMarkdownReportSkill().run(
        profile=state.get("dataframe_profile", {}),
        charts=state.get("generated_charts", []),
        insights=state.get("analysis_insights", []),
        query=state.get("user_query", ""),
    )
    state["report_markdown"] = result.get("markdown", "")
    return state
