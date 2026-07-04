from __future__ import annotations

from typing import Any

from src.agent.langchain_tools import AgentRuntimeContext, build_langchain_tools
from src.skills.base import BaseSkill
from src.skills.registry import SkillRegistry


class CaptureSkill(BaseSkill):
    name = "capture"
    description = "Capture normalized arguments"
    args_schema = {"type": "object", "properties": {}}

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return {"success": True, "received": kwargs}


def test_build_langchain_tools_wraps_registered_skills():
    registry = SkillRegistry()
    registry.register(CaptureSkill())
    context = AgentRuntimeContext(run_id="r1", csv_path="data.csv", query="分析销售")

    tools = build_langchain_tools(registry, context)

    assert [tool.name for tool in tools] == ["capture"]
    assert "Capture normalized arguments" in tools[0].description


def test_langchain_tool_injects_runtime_context_and_updates_context():
    registry = SkillRegistry()
    registry.register(CaptureSkill())
    context = AgentRuntimeContext(run_id="r1", csv_path="data.csv", query="分析销售")
    tool = build_langchain_tools(registry, context)[0]

    result = tool.invoke({"extra": "value"})

    assert result["success"] is True
    assert result["received"]["run_id"] == "r1"
    assert result["received"]["csv_path"] == "data.csv"
    assert result["received"]["query"] == "分析销售"
    assert result["received"]["extra"] == "value"
    assert context.tool_results[-1]["skill"] == "capture"


def test_langchain_tool_merges_skill_outputs_into_runtime_context():
    class ProfileSkill(BaseSkill):
        name = "profile_csv"
        description = "Profile CSV"
        args_schema = {"type": "object", "properties": {}}

        def run(self, **kwargs: Any) -> dict[str, Any]:
            return {"success": True, "rows": 2, "columns": 2, "column_names": ["月份", "销售额"]}

    registry = SkillRegistry()
    registry.register(ProfileSkill())
    context = AgentRuntimeContext(run_id="r1", csv_path="data.csv", query="分析销售")
    tool = build_langchain_tools(registry, context)[0]

    tool.invoke({})

    assert context.profile["rows"] == 2
    assert context.profile["column_names"] == ["月份", "销售额"]
