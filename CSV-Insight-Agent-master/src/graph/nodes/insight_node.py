from src.graph.state import GraphState
from src.skills.insight_generate import GenerateInsightSkill


def explain_chart(state: GraphState) -> GraphState:
    result = GenerateInsightSkill().run(profile=state.get("dataframe_profile", {}), charts=state.get("generated_charts", []), query=state.get("user_query", ""))
    state["chart_explanations"] = result.get("insights", [])
    state["final_answer"] = result.get("text", "")
    return state


def generate_insights(state: GraphState) -> GraphState:
    result = GenerateInsightSkill().run(profile=state.get("dataframe_profile", {}), charts=state.get("generated_charts", []), query=state.get("user_query", ""))
    state["analysis_insights"] = result.get("insights", [])
    return state
