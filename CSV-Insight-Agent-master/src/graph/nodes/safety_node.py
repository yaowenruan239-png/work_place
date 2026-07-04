from src.graph.state import GraphState


def safety_check(state: GraphState) -> GraphState:
    state["safety_result"] = {"passed": True, "issues": [], "rewrite_suggestion": ""}
    return state


def safety_route(state: GraphState) -> str:
    if state.get("safety_result", {}).get("passed", True):
        return "export_report"
    retry_count = state.get("retry_count", 0)
    if retry_count < 2:
        state["retry_count"] = retry_count + 1
        return "draft_report"
    return "finalize_error"
