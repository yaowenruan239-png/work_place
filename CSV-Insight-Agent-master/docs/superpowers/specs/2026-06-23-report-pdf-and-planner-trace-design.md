# Report PDF and Planner Trace Design

## Context

CSV-Insight-Agent currently supports CSV profiling, chart planning, chart generation, insight generation, Markdown report drafting, PDF/HTML export, and a Planner Loop mode. Two issues need improvement:

1. The generated PDF report is visually weak and reads like a Markdown dump. Charts are grouped together rather than integrated with narrative analysis.
2. Planner Loop mode can fall back directly to a generic final answer without showing why it failed or which tool step failed.

The selected approach is **方案二：咨询报告模板 + 演示型 Planner Trace**. It keeps the current LangGraph workflow and SkillRegistry, improves the report renderer, and adds a lightweight PlannerLoopRunner without turning the project into a full general-purpose Agent Runtime.

## Goals

- Produce consulting-style PDF reports with cover, executive summary, key metrics, findings, image-plus-text analysis, recommendations, limitations, and appendix.
- Keep WeasyPrint as the primary PDF engine.
- Preserve HTML fallback when WeasyPrint fails.
- Ensure charts are embedded next to explanatory text, not dumped as a separate image list.
- Make Planner Loop mode demo-friendly by recording each JSON action, normalized arguments, tool result, and error.
- Avoid silent Planner Loop fallback. Failures must be visible in `planner_steps` and final answer.
- Keep implementation focused and understandable.

## Non-Goals

- Do not build a full AgentLoop/AgentRunner platform like nanobot.
- Do not replace Streamlit with React.
- Do not add WebSocket trace streaming.
- Do not replace WeasyPrint with Playwright or Chromium in this iteration.
- Do not add multi-file analysis, multi-agent orchestration, or generic plugin marketplaces.

## Chosen Approach

Use the current project architecture:

```text
Streamlit / CLI
  -> LangGraph workflow
  -> graph nodes
  -> SkillRegistry
  -> skills
```

Add two focused subsystems:

```text
src/reporting/
  models.py
  content_builder.py
  html_renderer.py

src/planner/
  models.py
  runner.py
```

The reporting subsystem owns report structure and rendering. The planner subsystem owns Planner Loop trace, argument normalization, tool invocation, and visible failure reporting.

## Report Enhancement Design

### Report Structure

A report is represented as structured data before rendering. The core model is `ReportDocument` with these sections:

- `title`
- `subtitle`
- `query`
- `summary`
- `metrics`
- `findings`
- `chart_narratives`
- `recommendations`
- `limitations`
- `appendix`

Supporting models:

- `ReportMetric`: label, value, description
- `ReportFinding`: title, detail, severity or category
- `ChartNarrative`: title, image_path, chart_type, why_it_matters, observation, recommendation

### Consulting-Style Layout

The rendered HTML/PDF should include:

1. Cover page
2. Executive summary
3. Key metric cards
4. Core findings
5. Chart narrative cards
6. Overall conclusion
7. Recommended actions
8. Limitations
9. Appendix with field overview

Each chart narrative must combine text and image:

```text
Finding title
Why this chart matters
[chart image]
Observation
Recommendation
```

### HTML Rendering

`ReportHTMLRenderer` renders `ReportDocument` into complete HTML with CSS. The CSS should provide:

- A report-like cover page
- Professional typography
- Metric card grid
- Finding cards
- Chart cards
- Page breaks for PDF
- Print-safe colors and spacing
- Chinese font fallback
- Image max-width and captions

Image paths must be normalized for HTML/PDF embedding:

```text
outputs\charts\chart.png -> file:///absolute/path/to/outputs/charts/chart.png
outputs/charts/chart.png -> file:///absolute/path/to/outputs/charts/chart.png
```

If a chart path does not exist, HTML should show a clear missing-image placeholder while still rendering the report.

### Markdown Compatibility

`DraftMarkdownReportSkill` should still return Markdown. The Markdown should improve from a simple chart list to a consulting-style text report. `ExportPDFSkill` remains compatible with calls that only pass `markdown`.

When richer inputs are passed, such as `profile`, `charts`, `insights`, and `query`, `ExportPDFSkill` should use the structured report renderer.

### Export Behavior

`ExportPDFSkill` saves:

```text
outputs/reports/<run_id>.md
outputs/reports/<run_id>.pdf
outputs/html/<run_id>.html
```

Expected behavior:

- Always save Markdown.
- Always save HTML when rendering succeeds.
- Try WeasyPrint to export PDF.
- If WeasyPrint fails, return `success=True`, `pdf_path=None`, `html_path=<path>`, and an explanatory `error`.

PDF export failure must not fail the whole workflow.

## Planner Loop Trace Design

### Current Problem

The existing Planner Loop calls `LLMClient.chat_json()` with a fallback final answer. If parsing, validation, or backend invocation fails, the user sees only a generic fallback answer. The state does not preserve enough diagnostic information to understand what happened.

There is also a mismatch between prompt and runtime: the prompt allows `export_pdf`, but `build_default_registry()` does not register it. Tool arguments are not reliably normalized, so the model may omit `csv_path` or `run_id`.

### PlannerLoopRunner

Add `PlannerLoopRunner` under `src/planner/runner.py`. It should:

1. Build planner messages from query, profile, memory context, and available tools.
2. Call an LLM JSON method that can return traceable parse/validation errors.
3. Validate `tool_name` against the actual registry plus `final_answer`.
4. Normalize arguments using graph state context.
5. Call `SkillRegistry`.
6. Record each step.
7. Stop when final answer is produced or loop limits are reached.
8. Return updated state fields: `planner_steps`, `final_answer`, `generated_charts`, `report_markdown`, and `errors` when applicable.

### Planner Step Trace

Each step should be represented by `PlannerStepTrace`:

- `step_index`
- `thought`
- `tool_name`
- `tool_args`
- `normalized_args`
- `result_summary`
- `success`
- `error`
- `raw_model_output`
- `phase`

`phase` is one of:

- `llm_parse`
- `validation`
- `tool_call`
- `final_answer`

### Tool Whitelist

Planner Loop runtime tools must match the prompt:

- `profile_csv`
- `suggest_chart`
- `plot_chart`
- `plot_chart_batch`
- `generate_insight`
- `draft_markdown_report`
- `export_pdf`
- `read_recent_memory`
- `save_memory`
- `final_answer`

`final_answer` is not a SkillRegistry skill; it terminates the loop.

### Argument Auto-Fill

The runner should auto-fill common arguments from graph state:

- `csv_path`
- `run_id`
- `profile`
- `charts`
- `insights`
- `query`
- `markdown`

Examples:

`profile_csv` gets `csv_path` if missing.

`suggest_chart` gets `profile` and `query` if missing.

`plot_chart` gets `csv_path` and `run_id` if missing.

`plot_chart_batch` gets `csv_path`, `run_id`, and `plans` if missing and chart plans are available.

`generate_insight` gets `profile`, `charts`, and `query` if missing.

`draft_markdown_report` gets `profile`, `charts`, `insights`, and `query` if missing.

`export_pdf` gets `run_id`, `markdown`, `profile`, `charts`, `insights`, and `query` if missing.

### Failure Handling

The runner should not silently return a generic fallback. It should record failures and produce a visible final answer.

Stop conditions:

- `final_answer` emitted
- maximum 5 steps reached
- two consecutive LLM parse/validation failures
- two consecutive tool failures

If interrupted, final answer should summarize completed work and failure cause:

```text
Planner Loop 执行中断，但已完成 2 个步骤。
失败原因：第 3 步工具参数校验失败。
已生成图表：...
建议：请尝试 full_report 模式，或明确指定分析目标。
```

### Streamlit Display

`app.py` should render planner trace as readable steps:

```text
Step 1: 推荐图表
Thought: ...
Skill: suggest_chart
Args: ...
Result: success, recommended chart=bar
```

Raw JSON should remain available in an expander for debugging.

## Data Flow

### Full Report Mode

```text
profile_csv
  -> plan_multi_charts
  -> execute_chart_batch
  -> generate_insights
  -> draft_report
  -> safety_check
  -> export_report
  -> finalize
```

`draft_report` creates improved consulting-style Markdown. `export_report` calls `ExportPDFSkill` with richer report inputs when available.

### Planner Loop Mode

```text
profile_csv
  -> json_planner_loop
  -> PlannerLoopRunner
  -> SkillRegistry
  -> planner_steps + final_answer
  -> finalize
```

The fixed LangGraph topology remains unchanged; only the Planner Loop node delegates to the runner.

## Files to Modify

Create:

```text
src/reporting/__init__.py
src/reporting/models.py
src/reporting/content_builder.py
src/reporting/html_renderer.py
src/planner/__init__.py
src/planner/models.py
src/planner/runner.py
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
```

## Testing Strategy

Use test-driven development. Add failing tests before implementation.

### Report Tests

- `test_report_renderer_contains_consulting_sections`
- `test_report_renderer_embeds_chart_images`
- `test_report_renderer_normalizes_windows_image_paths`
- `test_report_renderer_handles_missing_chart_image`
- `test_export_pdf_saves_markdown_and_html`
- `test_export_pdf_falls_back_to_html_when_pdf_backend_fails`

### Planner Tests

- `test_planner_runner_records_tool_steps`
- `test_planner_runner_autofills_csv_path_and_run_id`
- `test_planner_runner_records_unknown_tool_error`
- `test_planner_runner_returns_final_answer_without_silent_fallback`
- `test_default_planner_registry_matches_prompt_tools`

### LLM JSON Tests

- `test_chat_json_with_trace_returns_parse_error`
- `test_chat_json_with_trace_returns_validation_error`

## Success Criteria

- Full Report mode produces a consulting-style HTML/PDF report with text and chart images integrated section by section.
- HTML fallback still works when WeasyPrint fails.
- Existing report export behavior remains backward compatible.
- Planner Loop displays step-by-step tool calls instead of silently returning a generic fallback.
- Planner tool whitelist matches the registry and prompt.
- Missing common tool arguments are automatically filled from graph state.
- Test suite passes.

## Scope Control

This design intentionally avoids a full nanobot-style runtime. The project remains a focused CSV analysis agent with improved reporting and traceable Planner Loop behavior.
