from __future__ import annotations

from src.agent.langchain_agent import LangChainCSVAgent
from src.graph.nodes.planner_loop_node import build_default_registry
from src.graph.state import GraphState


def langchain_agent_loop(state: GraphState) -> GraphState:
    registry = build_default_registry()
    runner = LangChainCSVAgent(registry=registry)
    return runner.run(state)
