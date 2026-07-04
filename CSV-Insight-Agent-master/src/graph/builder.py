from langgraph.graph import END, StateGraph

from src.graph.nodes.chart_execution_node import execute_chart, execute_chart_batch
from src.graph.nodes.chart_planning_node import plan_multi_charts, plan_single_chart
from src.graph.nodes.export_node import export_report
from src.graph.nodes.finalize_node import finalize, finalize_error
from src.graph.nodes.insight_node import explain_chart, generate_insights
from src.graph.nodes.langchain_agent_node import langchain_agent_loop
from src.graph.nodes.memory_node import load_memory_context
from src.graph.nodes.planner_loop_node import json_planner_loop
from src.graph.nodes.profile_node import profile_csv_node
from src.graph.nodes.report_node import draft_report
from src.graph.nodes.route_node import route_key, route_task
from src.graph.nodes.safety_node import safety_check, safety_route
from src.graph.state import GraphState


def create_graph_workflow():
    workflow = StateGraph(GraphState)
    workflow.add_node("load_memory_context", load_memory_context)
    workflow.add_node("profile_csv", profile_csv_node)
    workflow.add_node("route_task", route_task)
    workflow.add_node("plan_single_chart", plan_single_chart)
    workflow.add_node("execute_chart", execute_chart)
    workflow.add_node("explain_chart", explain_chart)
    workflow.add_node("plan_multi_charts", plan_multi_charts)
    workflow.add_node("execute_chart_batch", execute_chart_batch)
    workflow.add_node("generate_insights", generate_insights)
    workflow.add_node("draft_report", draft_report)
    workflow.add_node("safety_check", safety_check)
    workflow.add_node("export_report", export_report)
    workflow.add_node("json_planner_loop", json_planner_loop)
    workflow.add_node("langchain_agent_loop", langchain_agent_loop)
    workflow.add_node("finalize", finalize)
    workflow.add_node("finalize_error", finalize_error)

    workflow.set_entry_point("load_memory_context")
    workflow.add_edge("load_memory_context", "profile_csv")
    workflow.add_edge("profile_csv", "route_task")
    workflow.add_conditional_edges(
        "route_task",
        route_key,
        {
            "quick_chart": "plan_single_chart",
            "full_report": "plan_multi_charts",
            "planner_loop": "json_planner_loop",
            "agent_loop": "langchain_agent_loop",
        },
    )
    workflow.add_edge("plan_single_chart", "execute_chart")
    workflow.add_edge("execute_chart", "explain_chart")
    workflow.add_edge("explain_chart", "finalize")
    workflow.add_edge("plan_multi_charts", "execute_chart_batch")
    workflow.add_edge("execute_chart_batch", "generate_insights")
    workflow.add_edge("generate_insights", "draft_report")
    workflow.add_edge("draft_report", "safety_check")
    workflow.add_conditional_edges(
        "safety_check",
        safety_route,
        {
            "export_report": "export_report",
            "draft_report": "draft_report",
            "finalize_error": "finalize_error",
        },
    )
    workflow.add_edge("export_report", "finalize")
    workflow.add_edge("json_planner_loop", "finalize")
    workflow.add_edge("langchain_agent_loop", "finalize")
    workflow.add_edge("finalize", END)
    workflow.add_edge("finalize_error", END)
    return workflow.compile()
