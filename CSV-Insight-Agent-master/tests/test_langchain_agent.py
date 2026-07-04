from __future__ import annotations

from typing import Any

from src.agent.langchain_agent import LangChainCSVAgent
from src.agent.langchain_tools import AgentRuntimeContext
from src.skills.base import BaseSkill
from src.skills.registry import SkillRegistry


class ProfileSkill(BaseSkill):
    name = "profile_csv"
    description = "Profile CSV"
    args_schema = {"type": "object", "properties": {}}

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return {"success": True, "rows": 2, "columns": 2, "column_names": ["月份", "销售额"]}


class ReportSkill(BaseSkill):
    name = "export_pdf"
    description = "Export report"
    args_schema = {"type": "object", "properties": {}}

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return {"success": True, "report_path": "outputs/reports/r1.md", "pdf_path": None, "html_path": "outputs/html/r1.html"}


class FakeExecutor:
    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        tools = {tool.name: tool for tool in payload["tools"]}
        profile_result = tools["profile_csv"].invoke({})
        export_result = tools["export_pdf"].invoke({"markdown": "# 报告"})
        return {
            "output": f"完成分析：{profile_result['rows']} 行，报告 {export_result['report_path']}",
            "intermediate_steps": [
                (FakeAction("profile_csv", {}, "Thought: 读取 CSV"), profile_result),
                (FakeAction("export_pdf", {"markdown": "# 报告"}, "Thought: 导出报告"), export_result),
            ],
        }


class FakeAction:
    def __init__(self, tool: str, tool_input: dict[str, Any], log: str):
        self.tool = tool
        self.tool_input = tool_input
        self.log = log


def test_langchain_csv_agent_runs_executor_and_returns_state_update(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("月份,销售额\n1月,100\n2月,120\n", encoding="utf-8")
    registry = SkillRegistry()
    registry.register(ProfileSkill())
    registry.register(ReportSkill())
    agent = LangChainCSVAgent(registry=registry, executor_factory=lambda tools, prompt, llm: FakeExecutor())

    result = agent.run({"run_id": "r1", "csv_path": str(csv_path), "user_query": "分析销售", "errors": []})

    assert result["final_answer"].startswith("完成分析")
    assert result["dataframe_profile"]["rows"] == 2
    assert result["report_path"] == "outputs/reports/r1.md"
    assert result["html_path"] == "outputs/html/r1.html"
    assert result["status"] == "completed"
    assert len(result["agent_steps"]) == 2
    assert result["agent_steps"][0]["action"] == "profile_csv"
    assert "读取 CSV" in result["agent_steps"][0]["thought"]


def test_langchain_csv_agent_builds_runtime_context_from_state():
    context = LangChainCSVAgent.build_context({"run_id": "r2", "csv_path": "data.csv", "user_query": "分析", "dataframe_profile": {"rows": 1}})

    assert isinstance(context, AgentRuntimeContext)
    assert context.run_id == "r2"
    assert context.csv_path == "data.csv"
    assert context.query == "分析"
    assert context.profile == {"rows": 1}
