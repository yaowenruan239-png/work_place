from src.graph.state import GraphState
from src.skills.chart_suggest import SuggestChartSkill


def plan_single_chart(state: GraphState) -> GraphState:
    result = SuggestChartSkill().run(profile=state.get("dataframe_profile", {}), query=state.get("user_query", ""))
    state["chart_plan"] = (result.get("recommended") or [{}])[0]
    return state


def plan_multi_charts(state: GraphState) -> GraphState:
    result = SuggestChartSkill().run(profile=state.get("dataframe_profile", {}), query=state.get("user_query", ""))
    state["chart_plan"] = (result.get("recommended") or [])[:6]
    return state
