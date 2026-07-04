from src.graph.state import GraphState
from src.planner.runner import PlannerLoopRunner
from src.skills.chart_plot import PlotChartBatchSkill, PlotChartSkill
from src.skills.chart_suggest import SuggestChartSkill
from src.skills.csv_profile import ProfileCSVSkill
from src.skills.export_pdf import ExportPDFSkill
from src.skills.insight_generate import GenerateInsightSkill
from src.skills.memory_skill import ReadRecentMemorySkill, SaveMemorySkill
from src.skills.registry import SkillRegistry
from src.skills.report_draft import DraftMarkdownReportSkill


def build_default_registry() -> SkillRegistry:
    registry = SkillRegistry()
    for skill in [
        ProfileCSVSkill(),
        SuggestChartSkill(),
        PlotChartSkill(),
        PlotChartBatchSkill(),
        GenerateInsightSkill(),
        DraftMarkdownReportSkill(),
        ExportPDFSkill(),
        ReadRecentMemorySkill(),
        SaveMemorySkill(),
    ]:
        registry.register(skill)
    return registry


def json_planner_loop(state: GraphState) -> GraphState:
    registry = build_default_registry()
    runner = PlannerLoopRunner(registry=registry)
    return runner.run(state)
