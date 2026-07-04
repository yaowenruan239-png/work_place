from src.graph.state import GraphState
from src.memory.store import MemoryStore


def load_memory_context(state: GraphState) -> GraphState:
    state["memory_context"] = MemoryStore().build_memory_context(state.get("user_query", ""))
    return state
