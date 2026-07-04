# Report PDF and Planner Trace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade CSV-Insight-Agent with consulting-style PDF/HTML reports and a traceable demo-oriented Planner Loop.

**Architecture:** Keep the current Streamlit/CLI -> LangGraph -> nodes -> SkillRegistry -> skills architecture. Add `src/reporting/` for structured report content/rendering and `src/planner/` for Planner Loop trace, argument normalization, and visible failure handling.

**Tech Stack:** Python 3.11+, Streamlit, LangGraph, LangChain adapters, Pydantic, Markdown, WeasyPrint, pytest.

---

## Guardrails

- Approved spec: `docs/superpowers/specs/2026-06-23-report-pdf-and-planner-trace-design.md`.
- Use TDD: write failing tests, run RED, implement minimal code, run GREEN.
- Keep WeasyPrint as primary PDF backend and preserve HTML fallback.
- Do not introduce a general nanobot-style AgentLoop/AgentRunner runtime.
- Do not remove public outputs: `report_path`, `pdf_path`, `html_path`, `planner_steps`, `final_answer`.

---

## File Structure

Create:

```text
src/reporting/__init__.py
src/reporting/models.py
src/reporting/content_builder.py
src/reporting/html_renderer.py
src/planner/__init__.py
src/planner/models.py
src/planner/runner.py
tests/test_report_renderer.py
tests/test_planner_loop_runner.py
```

Modify:

```text
src/utils/report_utils.py
src/skills/report_draft.py
src/skills/export_pdf.py
src/graph/nodes/export_node.py
src/graph/nodes/planner_loop_node.py
src/llm/client.py
src/llm/prompts.py
src/llm/schemas.py
app.py
README.md
requirements.txt
tests/test_report_export.py
tests/test_llm_client_json.py
```

---

## Task 1: Add Structured Report Models and Renderer

**Files:** `src/reporting/*`, `tests/test_report_renderer.py`

- [ ] **Step 1: Write failing tests in `tests/test_report_renderer.py`**

Cover these tests:

```python
def test_report_renderer_contains_consulting_sections(tmp_path): ...
def test_report_renderer_embeds_chart_images(tmp_path): ...
def test_report_renderer_normalizes_windows_image_paths(tmp_path): ...
def test_report_renderer_handles_missing_chart_image(tmp_path): ...
```

Assertions must verify the rendered HTML contains `执行摘要`, `关键指标`, `核心发现`, `图文分析`, `行动建议`, `局限性说明`, `附录`, embeds existing chart images with `file:///`, normalizes backslashes, and renders `图表文件不可用` for missing images.

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_report_renderer.py -q
```

Expected: fails because `src.reporting` does not exist.

- [ ] **Step 3: Create report models**

Create `src/reporting/models.py` with dataclasses:

```python
@dataclass
class ReportMetric:
    label: str
    value: str
    description: str = ""

@dataclass
class ReportFinding:
    title: str
    detail: str
    category: str = "核心发现"

@dataclass
class ChartNarrative:
    title: str
    image_path: str | None
    chart_type: str
    why_it_matters: str
    observation: str
    recommendation: str

@dataclass
class ReportDocument:
    title: str
    subtitle: str
    query: str
    summary: str
    metrics: list[ReportMetric] = field(default_factory=list)
    findings: list[ReportFinding] = field(default_factory=list)
    chart_narratives: list[ChartNarrative] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    appendix: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Create `ReportContentBuilder`**

Create `src/reporting/content_builder.py`. `ReportContentBuilder.build(profile, charts, insights, query)` returns `ReportDocument` with:

- title `CSV 数据分析报告`
- subtitle `咨询式数据洞察报告`
- summary using query, rows, columns
- metric cards for rows, columns, numeric field count, chart count
- findings from the first 6 insights, or deterministic fallback
- one `ChartNarrative` per generated chart
- recommendations and limitations from the spec
- appendix for column names, numeric columns, categorical columns

- [ ] **Step 5: Create `ReportHTMLRenderer`**

Create `src/reporting/html_renderer.py`. `ReportHTMLRenderer(base_dir).render(document)` returns full HTML with embedded CSS. It must include cover, sections, metric grid, finding cards, chart cards, recommendations, limitations, and appendix table.

Path handling requirement:

```text
str(path).replace("\\", "/") -> Path -> absolute -> as_uri()
```

Missing image requirement: output a placeholder such as `<div class='missing'>图表文件不可用：missing.png</div>`.

CSS must include A4 page setup, Chinese font fallback, cover gradient, metric cards, chart cards, and print-safe image sizing.

- [ ] **Step 6: Run GREEN**

```bash
pytest tests/test_report_renderer.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/reporting tests/test_report_renderer.py
git commit -m "feat: add consulting report renderer"
```

---

## Task 2: Integrate Report Renderer into Draft and Export

**Files:** `src/utils/report_utils.py`, `src/skills/report_draft.py`, `src/skills/export_pdf.py`, `src/graph/nodes/export_node.py`, `tests/test_report_export.py`

- [ ] **Step 1: Replace/extend `tests/test_report_export.py`**

Add tests:

```python
def test_export_markdown_creates_report_and_export_file(tmp_path): ...
def test_export_pdf_saves_structured_html_with_charts(tmp_path): ...
def test_export_pdf_falls_back_to_html_when_pdf_backend_fails(tmp_path, monkeypatch): ...
```

Required assertions:

- Markdown file always exists.
- HTML file always exists.
- PDF path exists when PDF succeeds, else `pdf_path is None`.
- Structured export with `profile`, `charts`, `insights`, `query` contains `执行摘要`, `关键指标`, `图文分析`, chart title, and `file:///`.
- Monkeypatch importing `weasyprint` to raise `RuntimeError("missing pdf backend")`; assert fallback HTML exists and error includes that text.

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_report_export.py -q
```

Expected: fails because current export only writes HTML on PDF failure and does not use structured renderer.

- [ ] **Step 3: Update `markdown_to_html()` fallback CSS**

Keep `src/utils/report_utils.py` simple. Preserve `markdown_to_html(markdown_text, title)` and `write_text(path, content)`. Improve fallback CSS with A4 page, Chinese font fallback, max-width, image styling, and readable headings.

- [ ] **Step 4: Improve `DraftMarkdownReportSkill._fallback_report()`**

Change fallback report from chart dump to consulting-style Markdown:

```text
# 数据分析报告
## 1. 执行摘要
## 2. 关键指标
## 3. 核心发现
## 4. 图文分析
### 图表 N：<title>
![...](...)
**观察：** ...
**建议：** ...
## 5. 行动建议
## 6. 局限性说明
```

Use insights cyclically for chart observations. Keep deterministic text when no LLM is available.

- [ ] **Step 5: Update `ExportPDFSkill`**

Modify `src/skills/export_pdf.py` so `run()`:

1. Saves Markdown to `reports/<run_id>.md`.
2. Builds HTML with `ReportContentBuilder` + `ReportHTMLRenderer` when any of `profile`, `charts`, `insights` is present.
3. Otherwise uses `markdown_to_html(markdown)`.
4. Always writes HTML to `html/<run_id>.html` before PDF attempt.
5. Attempts `weasyprint.HTML(string=html, base_url=str(Path.cwd())).write_pdf(...)`.
6. Returns `success=True`, `report_path`, `html_path`, `pdf_path`, `error`.
7. On PDF failure returns `pdf_path=None` and preserves `html_path`.

- [ ] **Step 6: Pass rich report inputs from `export_node`**

Modify `src/graph/nodes/export_node.py` to call:

```python
ExportPDFSkill().run(
    run_id=state["run_id"],
    markdown=state.get("report_markdown", ""),
    profile=state.get("dataframe_profile", {}),
    charts=state.get("generated_charts", []),
    insights=state.get("analysis_insights", []),
    query=state.get("user_query", ""),
)
```

- [ ] **Step 7: Run GREEN**

```bash
pytest tests/test_report_renderer.py tests/test_report_export.py -q
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add src/reporting src/utils/report_utils.py src/skills/report_draft.py src/skills/export_pdf.py src/graph/nodes/export_node.py tests/test_report_renderer.py tests/test_report_export.py
git commit -m "feat: integrate consulting report export"
```

---

## Task 3: Add Traceable LLM JSON Result

**Files:** `src/llm/client.py`, `tests/test_llm_client_json.py`

- [ ] **Step 1: Add failing tests**

Append tests:

```python
class RequiredName(BaseModel):
    name: str

class StaticLLMClient(LLMClient):
    def __init__(self, responses): ...
    def chat(self, messages): ...

def test_chat_json_with_trace_returns_parse_error(): ...
def test_chat_json_with_trace_returns_validation_error(): ...
```

Parse error test uses response `"not json"` and asserts:

```python
result["success"] is False
result["phase"] == "llm_parse"
"No JSON object found" in result["error"]
result["raw_text"] == "not json"
```

Validation error test uses response `'{"other":"value"}'` and asserts:

```python
result["success"] is False
result["phase"] == "validation"
"name" in result["error"]
result["data"] == {"other": "value"}
```

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_llm_client_json.py -q
```

Expected: fails because `LLMClient.chat_json_with_trace()` does not exist.

- [ ] **Step 3: Implement `chat_json_with_trace()`**

Add method to `src/llm/client.py`:

```python
def chat_json_with_trace(self, messages: list[dict[str, str]], schema: type[BaseModel] | None = None) -> dict[str, Any]:
    augmented = list(messages) + [{"role": "system", "content": "请只输出有效 JSON 对象，不要包含其他文字。"}]
    raw_text = ""
    data = None
    try:
        raw_text = self.chat(augmented)
    except RuntimeError as exc:
        return {"success": False, "phase": "llm_call", "error": str(exc), "raw_text": raw_text, "data": None}
    try:
        data = extract_json_object(raw_text)
    except ValueError as exc:
        return {"success": False, "phase": "llm_parse", "error": str(exc), "raw_text": raw_text, "data": None}
    if schema:
        try:
            validated = schema.model_validate(data).model_dump()
        except ValidationError as exc:
            return {"success": False, "phase": "validation", "error": str(exc), "raw_text": raw_text, "data": data}
        return {"success": True, "phase": "ok", "error": None, "raw_text": raw_text, "data": validated}
    return {"success": True, "phase": "ok", "error": None, "raw_text": raw_text, "data": data}
```

Keep existing `chat_json()` behavior unchanged for backward compatibility.

- [ ] **Step 4: Run GREEN**

```bash
pytest tests/test_llm_client_json.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/llm/client.py tests/test_llm_client_json.py
git commit -m "feat: add traceable JSON parsing"
```

---

## Task 4: Add Planner Models and Runner

**Files:** `src/planner/*`, `src/graph/nodes/planner_loop_node.py`, `src/llm/prompts.py`, `src/llm/schemas.py`, `tests/test_planner_loop_runner.py`

- [ ] **Step 1: Write failing planner tests**

Create `tests/test_planner_loop_runner.py` with:

```python
class FakeLLM:
    def __init__(self, results): ...
    def chat_json_with_trace(self, messages, schema=None): ...

def base_state(tmp_path): ...
def test_default_planner_registry_matches_prompt_tools(): ...
def test_planner_runner_records_tool_steps(tmp_path): ...
def test_planner_runner_autofills_csv_path_and_run_id(tmp_path): ...
def test_planner_runner_records_unknown_tool_error(tmp_path): ...
def test_planner_runner_returns_final_answer_without_silent_fallback(tmp_path): ...
```

Required assertions:

- Default registry includes `profile_csv`, `suggest_chart`, `plot_chart`, `plot_chart_batch`, `generate_insight`, `draft_markdown_report`, `export_pdf`, `read_recent_memory`, `save_memory`.
- Runner records successful tool steps with `tool_name`, `normalized_args`, `success`, `phase`.
- `plot_chart` step auto-fills `csv_path` and `run_id`.
- Unknown tool records `phase == "validation"` and error containing `Unknown planner tool`.
- Two parse failures produce final answer containing `Planner Loop 执行中断`.

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_planner_loop_runner.py -q
```

Expected: fails because `src.planner` does not exist or registry tools are incomplete.

- [ ] **Step 3: Create planner trace model**

Create `src/planner/models.py` with `PlannerStepTrace` dataclass fields:

```text
step_index, thought, tool_name, tool_args, normalized_args, result_summary, success, error, raw_model_output, phase
```

Include `to_dict()` using `dataclasses.asdict()`.

- [ ] **Step 4: Update `PlannerAction` schema**

Modify `src/llm/schemas.py` so `PlannerAction.tool_name` is a `Literal` of:

```text
profile_csv, suggest_chart, plot_chart, plot_chart_batch, generate_insight, draft_markdown_report, export_pdf, read_recent_memory, save_memory, final_answer
```

Keep `tool_args: dict[str, Any] = {}`.

- [ ] **Step 5: Update planner prompt**

Modify `PLANNER_LOOP_PROMPT` to list the same tools, state that system auto-fills `csv_path`, `run_id`, `profile`, `charts`, `insights`, `query`, `markdown`, and require JSON-only output.

- [ ] **Step 6: Implement `PlannerLoopRunner`**

Create `src/planner/runner.py`. Required behavior:

- Constructor accepts `llm`, `registry`, `max_steps=5`.
- `run(state)` builds messages from `PLANNER_LOOP_PROMPT`, registry description, query, csv_path, profile, memory.
- Calls `llm.chat_json_with_trace(messages, schema=PlannerAction)`.
- Records parse/validation/tool errors as `PlannerStepTrace`.
- Handles `final_answer` by setting `state["final_answer"]` and stopping.
- Validates tool exists in registry before calling.
- Auto-fills common args for each supported tool from graph state.
- Merges successful tool results back into state: profile, chart_plan, generated_charts, analysis_insights, report_markdown, report_path/pdf_path/html_path.
- Stops after 5 steps or after 2 consecutive parse/validation/tool failures.
- If no final answer, writes interruption summary into `state["final_answer"]`.

- [ ] **Step 7: Update default planner registry and node**

Modify `src/graph/nodes/planner_loop_node.py`:

- Register `ExportPDFSkill`, `ReadRecentMemorySkill`, and `SaveMemorySkill` in `build_default_registry()`.
- Replace inline loop implementation with:

```python
def json_planner_loop(state: GraphState) -> GraphState:
    registry = build_default_registry()
    runner = PlannerLoopRunner(registry=registry)
    return runner.run(state)
```

Remove unused imports.

- [ ] **Step 8: Run GREEN**

```bash
pytest tests/test_planner_loop_runner.py -q
```

Expected: pass.

- [ ] **Step 9: Commit**

```bash
git add src/planner src/graph/nodes/planner_loop_node.py src/llm/prompts.py src/llm/schemas.py tests/test_planner_loop_runner.py
git commit -m "feat: add traceable planner loop runner"
```

---

## Task 5: Improve Streamlit Display and Documentation

**Files:** `app.py`, `README.md`, `requirements.txt`

- [ ] **Step 1: Improve Streamlit planner trace display**

In `app.py`, replace raw-only `st.json(result["planner_steps"])` with step expanders showing:

```text
Step <index>: <tool_name or phase> · 成功/失败
Thought
Skill
Phase
Error if present
Result summary if present
Normalized Args JSON
```

Keep raw JSON in a final expander labeled `查看原始 Planner JSON`.

- [ ] **Step 2: Update README**

Document:

- Full Report Mode now generates consulting-style HTML/PDF with cover, executive summary, metric cards, findings, chart narrative cards, recommendations, limitations, appendix.
- Planner Loop Mode now shows Planner Trace: thought, tool name, normalized args, result summary, and error cause.
- WeasyPrint remains primary PDF backend; HTML fallback remains available when system libraries are missing.

- [ ] **Step 3: Clarify WeasyPrint in `requirements.txt`**

If WeasyPrint is commented, keep it commented and add:

```text
# Install WeasyPrint via conda-forge or uncomment after GTK/Pango/Cairo libraries are available on Windows.
# weasyprint~=65.1
```

If it is uncommented, add:

```text
# On Windows, WeasyPrint also needs GTK/Pango/Cairo system libraries.
```

- [ ] **Step 4: Check lints for `app.py`**

Use editor diagnostics on `app.py`. Expected: no linter errors.

- [ ] **Step 5: Commit**

```bash
git add app.py README.md requirements.txt
git commit -m "docs: describe report and planner trace improvements"
```

---

## Task 6: End-to-End Verification

**Files:** no code changes expected unless verification reveals issues.

- [ ] **Step 1: Run focused tests**

```bash
pytest tests/test_report_renderer.py tests/test_report_export.py tests/test_planner_loop_runner.py tests/test_llm_client_json.py -q
```

Expected: all pass.

- [ ] **Step 2: Run full tests**

```bash
pytest -q
```

Expected: all pass.

- [ ] **Step 3: Run Full Report smoke test**

```bash
python main.py examples/sales.csv "生成完整销售数据分析报告，包含图表、核心发现和建议" --mode full_report
```

Expected: Markdown and HTML exist. PDF exists if WeasyPrint system dependencies are available; otherwise HTML fallback error is visible and workflow still completes.

- [ ] **Step 4: Run Planner Loop smoke test**

```bash
python main.py examples/sales.csv "自动选择合适工具分析销售数据，并展示每一步工具调用" --mode planner_loop
```

Expected: output contains `planner_steps` with `step_index`, `tool_name`, `normalized_args`, `success`, `phase`; failures produce explanatory interruption answer rather than silent fallback.

- [ ] **Step 5: Check git status**

```bash
git status --short
```

Expected: no unexpected tracked runtime artifacts; `.env`, `outputs/`, and `memory/task_history.jsonl` remain ignored.

- [ ] **Step 6: Commit verification fixes if needed**

If verification required fixes:

```bash
git add <fixed-files>
git commit -m "fix: stabilize report and planner trace verification"
```

If no fixes were needed, do not create an empty commit.
