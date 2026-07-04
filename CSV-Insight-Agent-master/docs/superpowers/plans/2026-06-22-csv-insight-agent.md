# CSV-Insight-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `CSV-Insight-Agent`, an independent Streamlit + LangGraph CSV analysis agent that merges report generation and chart-agent capabilities.

**Architecture:** LangGraph orchestrates Quick Chart, Full Report, and Planner Loop paths. All executable capabilities are SkillRegistry skills. LLMClient centralizes DeepSeek/OpenAI/Ollama fallback. MemoryStore provides JSONL long-term memory and prompt context.

**Tech Stack:** Python 3.11+, Streamlit, LangGraph, LangChain, pandas, numpy, matplotlib, seaborn, Pydantic, python-dotenv, Markdown, WeasyPrint, pytest.

---

## Guardrails

- Source projects: `a:\Bob\ai-report-generator-lite-main`, `a:\Bob\csv-chart-agent-master`.
- Spec: `docs/superpowers/specs/2026-06-22-csv-insight-agent-design.md`.
- Never commit real API keys. `.env` must be ignored. `.env.example` uses placeholders only.
- Use TDD for implementation tasks: write failing test, verify RED, implement, verify GREEN, commit.

---

## File Structure

Create the target structure from the spec:

```text
app.py, main.py, README.md, requirements.txt, .env.example, .gitignore
src/config.py
src/llm/client.py, prompts.py, schemas.py
src/graph/state.py, builder.py, nodes/*.py
src/skills/base.py, registry.py, csv_profile.py, chart_suggest.py, chart_plot.py, insight_generate.py, report_draft.py, export_pdf.py, memory_skill.py
src/memory/store.py
src/utils/file_utils.py, json_utils.py, chart_utils.py, report_utils.py, errors.py
tests/test_memory_store.py, test_skill_registry.py, test_csv_profile_skill.py, test_chart_plot_skill.py, test_llm_client_json.py, test_graph_routing.py, test_report_export.py
examples/sales.csv, examples/students.csv
memory/user_profile.json, memory/chart_preference.json
outputs/uploads/.gitkeep, outputs/charts/.gitkeep, outputs/reports/.gitkeep, outputs/html/.gitkeep
```

---

## Task 1: Scaffold Project and Safe Config

**Files:** `.gitignore`, `.env.example`, `requirements.txt`, package dirs, examples, runtime dirs.

- [ ] Write `.gitignore` ignoring `.env`, venvs, caches, `memory/task_history.jsonl`, `memory/.cursor`, and runtime files under `outputs/` while keeping `.gitkeep` files.
- [ ] Write `.env.example` with placeholders: `DEEPSEEK_API_KEY=sk-your-deepseek-key`, `DEEPSEEK_BASE_URL=https://api.deepseek.com`, `DEEPSEEK_MODEL=deepseek-chat`, optional OpenAI/Ollama settings.
- [ ] Write `requirements.txt` with Streamlit, pandas, numpy, matplotlib, seaborn, pydantic, python-dotenv, langgraph, langchain-core, langchain-openai, langchain-community, Markdown, weasyprint, pytest.
- [ ] Create all package directories and `__init__.py` files.
- [ ] Copy `sales.csv` and `students.csv` from `a:\Bob\ai-report-generator-lite-main\examples` into `examples/`.
- [ ] Commit: `chore: scaffold CSV Insight Agent project`.

---

## Task 2: MemoryStore

**Files:** `src/memory/store.py`, `tests/test_memory_store.py`

- [ ] Write failing tests for: saving task returns cursor; recent tasks are latest-first; corrupt JSONL lines are skipped; mode filter works; chart type filter works; memory context returns Chinese recent-task summary.
- [ ] Run `pytest tests/test_memory_store.py -q` and verify RED.
- [ ] Implement `MemoryStore` with `save_task`, `get_recent_tasks`, `get_tasks_by_mode`, `get_tasks_by_chart_type`, `load_user_profile`, `save_user_profile`, `load_chart_preference`, `save_chart_preference`, `build_memory_context`.
- [ ] Ensure writes use `threading.Lock`; `.cursor` recovers from corrupt value by scanning history; files are created if missing.
- [ ] Run `pytest tests/test_memory_store.py -q` and verify GREEN.
- [ ] Commit: `feat: add JSONL memory store`.

---

## Task 3: Skill Base and Registry

**Files:** `src/skills/base.py`, `src/skills/registry.py`, `tests/test_skill_registry.py`

- [ ] Write failing tests for: register/call echo skill; unknown skill structured error; exception triggers fallback; `list_skills()` includes name/description/args_schema; call log records calls.
- [ ] Run `pytest tests/test_skill_registry.py -q` and verify RED.
- [ ] Implement `BaseSkill` with `name`, `description`, `args_schema`, abstract `run`, default `fallback_run`.
- [ ] Implement `SkillRegistry` with `register`, `get`, `list_skills`, `describe_skills`, `call`, `get_call_log`.
- [ ] Run `pytest tests/test_skill_registry.py -q` and verify GREEN.
- [ ] Commit: `feat: add skill registry`.

---

## Task 4: CSV Profile and Chart Skills

**Files:** `src/utils/chart_utils.py`, `src/skills/csv_profile.py`, `src/skills/chart_suggest.py`, `src/skills/chart_plot.py`, `tests/test_csv_profile_skill.py`, `tests/test_chart_plot_skill.py`

- [ ] Write failing tests for `ProfileCSVSkill`: returns `success`, `file_name`, `rows`, `columns`, `column_names`, `numeric_columns`, `categorical_columns`, `dtypes`, `missing_values`, `numeric_summary`, `sample_rows`.
- [ ] Write failing tests for `PlotChartSkill`: creates PNG for `line`, `bar`, `scatter`, `histogram`, `box`, `correlation_heatmap`; missing column returns structured error and suggestions; invalid chart type returns supported chart suggestions.
- [ ] Run `pytest tests/test_csv_profile_skill.py tests/test_chart_plot_skill.py -q` and verify RED.
- [ ] Implement `setup_chinese_font()` in `chart_utils.py` using SimHei, Microsoft YaHei, Arial Unicode MS, Noto Sans CJK SC, DejaVu Sans.
- [ ] Implement `ProfileCSVSkill` using pandas and `is_numeric_dtype`.
- [ ] Implement `SuggestChartSkill` rules: categorical+numeric -> bar/box; >=2 numeric -> scatter/correlation_heatmap; numeric -> histogram; categorical-only -> count bar.
- [ ] Implement `PlotChartSkill` and `PlotChartBatchSkill`, validating fields before plotting and saving PNGs to `outputs/charts` with `run_id`, chart type, timestamp.
- [ ] Run `pytest tests/test_csv_profile_skill.py tests/test_chart_plot_skill.py -q` and verify GREEN.
- [ ] Commit: `feat: add CSV profile and chart skills`.

---

## Task 5: LLM Client, JSON Utility, Prompts, Schemas

**Files:** `src/utils/json_utils.py`, `src/llm/client.py`, `src/llm/prompts.py`, `src/llm/schemas.py`, `tests/test_llm_client_json.py`

- [ ] Write failing tests for extracting plain JSON, fenced Markdown JSON, embedded JSON, and `LLMClient(backends=[]).chat_json(..., fallback={...})` returning fallback.
- [ ] Run `pytest tests/test_llm_client_json.py -q` and verify RED.
- [ ] Implement `extract_json_object(text)`.
- [ ] Implement `LLMClient` with `available_backends`, `active_backend`, `chat`, `chat_json`; detect DeepSeek, OpenAI, Ollama from env; retry invalid JSON; return fallback after failures.
- [ ] Implement Pydantic schemas: `RouteDecision`, `ChartPlan`, `MultiChartPlan`, `SafetyResult`, `PlannerAction`.
- [ ] Implement Chinese prompts: `ROUTE_TASK_PROMPT`, `CHART_PLAN_PROMPT`, `MULTI_CHART_PLAN_PROMPT`, `INSIGHT_PROMPT`, `REPORT_PROMPT`, `SAFETY_PROMPT`, `PLANNER_LOOP_PROMPT`.
- [ ] Run `pytest tests/test_llm_client_json.py -q` and verify GREEN.
- [ ] Commit: `feat: add LLM client and JSON parsing`.

---

## Task 6: Insight, Report, Export, Memory Skills

**Files:** `src/utils/report_utils.py`, `src/skills/insight_generate.py`, `src/skills/report_draft.py`, `src/skills/export_pdf.py`, `src/skills/memory_skill.py`, `tests/test_report_export.py`

- [ ] Write failing tests for `ExportPDFSkill`: always writes Markdown; writes PDF if WeasyPrint works or HTML fallback if it fails; returns `success=True`, `report_path`, and one of `pdf_path`/`html_path`.
- [ ] Run `pytest tests/test_report_export.py -q` and verify RED.
- [ ] Implement `markdown_to_html(markdown_text, title)` and `write_text(path, content)`.
- [ ] Implement `ExportPDFSkill` with Markdown save, PDF attempt, HTML fallback.
- [ ] Implement `GenerateInsightSkill` with LLM call and deterministic fallback insights based on rows/columns/numeric fields/chart count.
- [ ] Implement `DraftMarkdownReportSkill` with LLM call and fallback Markdown containing exactly seven required sections.
- [ ] Implement `ReadRecentMemorySkill` and `SaveMemorySkill` wrapping `MemoryStore`.
- [ ] Run `pytest tests/test_report_export.py -q` and verify GREEN.
- [ ] Commit: `feat: add report and memory skills`.

---

## Task 7: LangGraph State, Nodes, Builder

**Files:** `src/graph/state.py`, `src/graph/builder.py`, `src/graph/nodes/*.py`, `tests/test_graph_routing.py`

- [ ] Write failing tests for `route_task`: explicit `quick_chart`, `full_report`, `planner_loop` preserved; invalid/no mode + query containing `报告` routes to `full_report`; default routes to `quick_chart`.
- [ ] Run `pytest tests/test_graph_routing.py -q` and verify RED.
- [ ] Implement `GraphState` as `TypedDict(total=False)` with all spec fields.
- [ ] Implement nodes: memory load, profile, route, chart planning, chart execution, insight/explain, report draft, safety check/route, export, finalize/error, planner loop.
- [ ] Implement Planner Loop using `PlannerAction`, `PLANNER_LOOP_PROMPT`, `SkillRegistry`, max 4 steps, final answer handling, and tool-result feedback messages.
- [ ] Implement `create_graph_workflow()` with branches: Quick Chart, Full Report, Planner Loop, safety retry, finalize.
- [ ] Run `pytest tests/test_graph_routing.py -q` and verify GREEN.
- [ ] Commit: `feat: add LangGraph workflow`.

---

## Task 8: Streamlit UI, CLI, README

**Files:** `src/config.py`, `app.py`, `main.py`, `README.md`

- [ ] Implement `src/config.py` with root/runtime paths and `ensure_runtime_dirs()`.
- [ ] Implement `app.py`: CSV upload, mode select, query input, run button, LLM backend status, recent tasks, chart previews/downloads, final answer, report preview/downloads, Planner Loop JSON steps.
- [ ] Implement `main.py`: `python main.py examples/sales.csv "分析销售趋势" --mode quick_chart` builds initial state, invokes graph, prints result.
- [ ] Write README with project intro, tech stack, architecture diagram, workflow, SkillRegistry, MemoryStore, Quick Chart example, Full Report example, Planner Loop example, LLM fallback, run instructions, env vars, resume bullets.
- [ ] Commit: `feat: add Streamlit UI and documentation`.

---

## Task 9: Verification and Local DeepSeek Setup

**Files:** local `.env` only; do not commit.

- [ ] Copy `.env.example` to `.env` and set `DEEPSEEK_API_KEY=<provided-deepseek-api-key>`, `DEEPSEEK_BASE_URL=https://api.deepseek.com`, `DEEPSEEK_MODEL=deepseek-chat`.
- [ ] Run `pytest -q`; expected all tests pass.
- [ ] Run `python main.py examples/sales.csv "分析销售趋势并画图" --mode quick_chart`; expected PNG under `outputs/charts/`.
- [ ] Run `python main.py examples/sales.csv "生成完整销售数据分析报告" --mode full_report`; expected Markdown plus PDF or HTML.
- [ ] Run `python main.py examples/sales.csv "自动选择工具分析销售数据" --mode planner_loop`; expected planner steps or fallback answer.
- [ ] Run `git status --short` and `git ls-files | findstr /i "\.env"`; expected `.env` is not tracked.
- [ ] Commit final adjustments if any: `test: verify CSV Insight Agent workflow`.

---

## Plan Self-Review

- Spec coverage: Quick Chart, Full Report, Planner Loop, SkillRegistry, MemoryStore, LLM fallback, chart generation, report export, UI, README, tests covered.
- No real DeepSeek API key is recorded in tracked files.
- No `TBD`, `TODO`, or `implement later` placeholders.
- Mode names are consistent: `quick_chart`, `full_report`, `planner_loop`.
