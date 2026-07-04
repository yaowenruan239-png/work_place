from src.graph.nodes.planner_loop_node import build_default_registry
from src.planner.runner import PlannerLoopRunner
from src.skills.base import BaseSkill
from src.skills.registry import SkillRegistry


class FakeLLM:
    def __init__(self, results):
        self.results = list(results)

    def chat_json_with_trace(self, messages, schema=None):
        return self.results.pop(0)


class RecordingLLM:
    def __init__(self, results):
        self.results = list(results)
        self.messages_seen = []

    def chat_json_with_trace(self, messages, schema=None):
        self.messages_seen.append(list(messages))
        return self.results.pop(0)


def base_state(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("月份,销售额\n1月,100\n2月,120\n", encoding="utf-8")
    return {
        "run_id": "r1",
        "csv_path": str(csv_path),
        "user_query": "分析销售趋势",
        "dataframe_profile": {"rows": 2, "columns": 2, "column_names": ["月份", "销售额"], "numeric_columns": ["销售额"]},
        "memory_context": "暂无历史记忆。",
        "generated_charts": [],
        "analysis_insights": [],
        "errors": [],
    }


def test_default_planner_registry_matches_prompt_tools():
    registry = build_default_registry()
    names = {skill["name"] for skill in registry.list_skills()}

    assert {"profile_csv", "suggest_chart", "plot_chart", "plot_chart_batch", "generate_insight", "draft_markdown_report", "export_pdf", "read_recent_memory", "save_memory"}.issubset(names)


def test_planner_runner_default_max_steps_is_8():
    runner = PlannerLoopRunner(llm=FakeLLM([]), registry=SkillRegistry())

    assert runner.max_steps == 8


def test_planner_runner_records_tool_steps(tmp_path):
    llm = FakeLLM([
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "推荐图表", "tool_name": "suggest_chart", "tool_args": {}}},
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "结束", "tool_name": "final_answer", "tool_args": {"answer": "完成分析"}}},
    ])
    runner = PlannerLoopRunner(llm=llm, registry=build_default_registry(), max_steps=3)

    result = runner.run(base_state(tmp_path))

    assert result["final_answer"] == "完成分析"
    assert len(result["planner_steps"]) == 2
    assert result["planner_steps"][0]["tool_name"] == "suggest_chart"
    assert result["planner_steps"][0]["success"] is True


def test_planner_runner_autofills_csv_path_and_run_id(tmp_path):
    llm = FakeLLM([
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "画图", "tool_name": "plot_chart", "tool_args": {"chart_type": "bar", "x_col": "月份", "y_col": "销售额", "title": "销售趋势"}}},
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "结束", "tool_name": "final_answer", "tool_args": {"answer": "已生成图表"}}},
    ])
    runner = PlannerLoopRunner(llm=llm, registry=build_default_registry(), max_steps=3)

    result = runner.run(base_state(tmp_path))

    args = result["planner_steps"][0]["normalized_args"]
    assert args["csv_path"].endswith("data.csv")
    assert args["run_id"] == "r1"
    assert result["generated_charts"]


def test_planner_runner_records_unknown_tool_error(tmp_path):
    llm = FakeLLM([
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "调用未知工具", "tool_name": "missing_tool", "tool_args": {}}},
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "结束", "tool_name": "final_answer", "tool_args": {"answer": "结束"}}},
    ])
    runner = PlannerLoopRunner(llm=llm, registry=build_default_registry(), max_steps=3)

    result = runner.run(base_state(tmp_path))

    assert result["planner_steps"][0]["success"] is False
    assert result["planner_steps"][0]["phase"] == "validation"
    assert "Unknown planner tool" in result["planner_steps"][0]["error"]


def test_planner_runner_returns_final_answer_without_silent_fallback(tmp_path):
    llm = FakeLLM([
        {"success": False, "phase": "llm_parse", "error": "No JSON object found", "raw_text": "bad", "data": None},
        {"success": False, "phase": "llm_parse", "error": "No JSON object found", "raw_text": "bad", "data": None},
    ])
    runner = PlannerLoopRunner(llm=llm, registry=build_default_registry(), max_steps=3)

    result = runner.run(base_state(tmp_path))

    assert "Planner Loop 执行中断" in result["final_answer"]
    assert len(result["planner_steps"]) == 2
    assert result["planner_steps"][0]["error"] == "No JSON object found"


def test_planner_runner_adds_repair_instruction_after_json_parse_failure(tmp_path):
    llm = RecordingLLM([
        {"success": False, "phase": "llm_parse", "error": "Expecting ',' delimiter", "raw_text": '{"thought":"bad"', "data": None},
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "结束", "tool_name": "final_answer", "tool_args": {"answer": "已恢复"}}},
    ])
    runner = PlannerLoopRunner(llm=llm, registry=build_default_registry(), max_steps=3)

    result = runner.run(base_state(tmp_path))

    assert result["final_answer"] == "已恢复"
    second_call_messages = llm.messages_seen[1]
    assert any("上一次输出不是合法 JSON" in message["content"] for message in second_call_messages)
    assert any("Expecting ',' delimiter" in message["content"] for message in second_call_messages)


class StaticSkill(BaseSkill):
    def __init__(self, name, result):
        self.name = name
        self.description = name
        self.args_schema = {"type": "object", "properties": {}}
        self.result = result

    def run(self, **kwargs):
        return self.result


def test_planner_runner_completes_with_deterministic_fallback_after_parse_failures(tmp_path):
    state = base_state(tmp_path)
    state["generated_charts"] = [{"path": "chart.png", "chart_type": "bar", "title": "销售趋势"}]
    llm = FakeLLM([
        {"success": False, "phase": "llm_parse", "error": "Expecting ',' delimiter", "raw_text": '{"bad"', "data": None},
        {"success": False, "phase": "llm_parse", "error": "Expecting ',' delimiter", "raw_text": '{"bad again"', "data": None},
    ])
    registry = SkillRegistry()
    registry.register(StaticSkill("generate_insight", {"success": True, "insights": ["销售额整体稳定。"]}))
    registry.register(StaticSkill("draft_markdown_report", {"success": True, "markdown": "# 报告\n- 销售额整体稳定。"}))
    registry.register(StaticSkill("export_pdf", {"success": True, "report_path": "r1.md", "pdf_path": None, "html_path": "r1.html"}))
    runner = PlannerLoopRunner(llm=llm, registry=registry, max_steps=3)

    result = runner.run(state)

    assert result["analysis_insights"] == ["销售额整体稳定。"]
    assert result["report_markdown"].startswith("# 报告")
    assert result["report_path"] == "r1.md"
    assert "已通过确定性 fallback 完成分析" in result["final_answer"]
    fallback_steps = [step for step in result["planner_steps"] if step.get("phase") == "deterministic_fallback"]
    assert [step["tool_name"] for step in fallback_steps] == ["generate_insight", "draft_markdown_report", "export_pdf"]


def test_planner_runner_finishes_remaining_artifacts_when_max_steps_exhausted(tmp_path):
    llm = FakeLLM([
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "洞察", "tool_name": "generate_insight", "tool_args": {}}},
        {"success": True, "phase": "ok", "error": None, "raw_text": "{}", "data": {"thought": "报告", "tool_name": "draft_markdown_report", "tool_args": {}}},
    ])
    state = base_state(tmp_path)
    state["generated_charts"] = [{"path": "chart.png", "chart_type": "bar", "title": "销售趋势"}]
    registry = SkillRegistry()
    registry.register(StaticSkill("generate_insight", {"success": True, "insights": ["销售额整体稳定。"]}))
    registry.register(StaticSkill("draft_markdown_report", {"success": True, "markdown": "# 报告\n- 销售额整体稳定。"}))
    registry.register(StaticSkill("export_pdf", {"success": True, "report_path": "r1.md", "pdf_path": None, "html_path": "r1.html"}))
    runner = PlannerLoopRunner(llm=llm, registry=registry, max_steps=2)

    result = runner.run(state)

    assert result["analysis_insights"] == ["销售额整体稳定。"]
    assert result["report_markdown"].startswith("# 报告")
    assert result["report_path"] == "r1.md"
    assert "Planner Loop 已完成分析" in result["final_answer"]
    assert result["planner_steps"][-1]["tool_name"] == "export_pdf"
    assert result["planner_steps"][-1]["phase"] == "deterministic_fallback"
