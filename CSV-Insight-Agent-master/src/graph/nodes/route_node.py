from __future__ import annotations

from src.graph.state import GraphState

VALID_MODES = {"quick_chart", "full_report", "planner_loop", "agent_loop"}


def route_task(state: GraphState) -> GraphState:
    mode = state.get("mode") or "quick_chart"
    if mode not in VALID_MODES:
        query = state.get("user_query", "")
        mode = "full_report" if "报告" in query or "完整" in query else "quick_chart"
    state["mode"] = mode
    state["route_decision"] = {"mode": mode, "reason": "explicit mode or rule fallback"}
    return state


def route_key(state: GraphState) -> str:
    return state.get("route_decision", {}).get("mode", state.get("mode", "quick_chart"))
