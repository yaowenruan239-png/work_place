from src.graph.state import GraphState
from src.skills.csv_profile import ProfileCSVSkill


def profile_csv_node(state: GraphState) -> GraphState:
    result = ProfileCSVSkill().run(csv_path=state["csv_path"])
    if result.get("success"):
        state["dataframe_profile"] = result
    else:
        state.setdefault("errors", []).append(result.get("error", "profile failed"))
        state["status"] = "error"
    return state
