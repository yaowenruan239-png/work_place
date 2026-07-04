# CSV-Insight-Agent 合并设计

## 1. 背景与目标

本设计用于将 `ai-report-generator-lite-main` 和 `csv-chart-agent-master` 合并为一个新的独立项目：`CSV-Insight-Agent`。新项目位于 `a:\Bob\CSV-Insight-Agent\`，两个原项目保持不动，只作为迁移来源。

合并目标不是简单拼接代码，而是重构成一个面向 CSV 数据的轻量数据分析智能体。项目应支持 CSV 数据画像、图表规划、图表生成、中文洞察解释、多章节 Markdown 报告、PDF/HTML 导出、文件型长期记忆、Skill Registry 工具编排和多后端 LLM 降级。

完整交付范围包括：

- Quick Chart Mode：单张图表 + 中文解释。
- Full Report Mode：多张图表 + Markdown 报告 + PDF/HTML 导出。
- Planner Loop Mode：LLM 输出 JSON 动作并通过 SkillRegistry 调用白名单 Skill。
- Streamlit UI、README、测试、示例数据和基础运行说明。

## 2. 可复用模块分析

### 2.1 `ai-report-generator-lite-main`

可复用内容：

- LangGraph 工作流主干：`src/graph/builder.py`。
- GraphState 思路：`src/graph/state.py`。
- 数据画像、图表生成、洞察生成、报告撰写、报告最终化节点：`src/agents/`。
- DeepSeek OpenAI-compatible 调用封装：`src/llm_client.py`。
- Markdown/PDF/HTML 报告导出思路。
- 多图报告链路和中文报告结构。
- 示例 CSV、现有测试组织方式、README 中的系统说明。

需要改造的点：

- 原工作流是固定报告流水线，需要升级为三模式条件路由。
- 原节点直接执行工具，需要改为通过 SkillRegistry 调用。
- 原 LLM 后端较单一，需要合并多后端降级。
- 原 memory 主要用于展示历史，需要升级为可注入 prompt 的上下文。

### 2.2 `csv-chart-agent-master`

可复用内容：

- `agent/tool_registry.py` 的工具注册与调用思想。
- `agent/loop_runner.py` 的固定三步流程和 `run_with_json_planner()` 雏形。
- `agent/llm_client.py` 的 DeepSeek / OpenAI / Ollama 后端选择和 JSON 解析重试。
- `agent/memory_store.py` 的 JSONL 追加、`.cursor`、`threading.Lock` 和损坏 JSON 行跳过。
- `tools/csv_profiler.py` 的数据画像工具。
- `tools/chart_tool.py` 的参数化图表生成、字段校验和 fallback。
- Streamlit 调试面板、历史任务和单图生成交互思路。

需要改造的点：

- 原项目无 LangGraph，需要纳入统一 Graph 编排。
- 原 ToolRegistry 是函数式工具注册，需要升级为类式 Skill。
- 原图表类型较少，需要扩展 `box` 和 `correlation_heatmap`。
- 原 Planner Loop 没有正式接入 UI，需要作为独立模式接入。

## 3. 总体架构

新项目采用六层架构。

### 3.1 UI 层

文件：`app.py`

职责：

- CSV 上传。
- 模式选择：Quick Chart / Full Report / Planner Loop。
- 自然语言任务输入。
- 调用 LangGraph 工作流。
- 展示图表、报告、最终回答和错误。
- 提供 Markdown、PDF、HTML、PNG 下载按钮。
- 侧边栏展示最近任务、用户偏好、图表类型筛选和 LLM 后端状态。

### 3.2 Graph 编排层

文件：`src/graph/`

职责：

- 定义统一 `GraphState`。
- 构建 LangGraph 状态图。
- 使用 `route_task` 条件路由三种模式。
- 处理 `safety_check` 失败后的重写或终止。
- 保证固定流水线稳定可运行，同时保留 Planner Loop 的 Agent 能力。

### 3.3 Skill 层

文件：`src/skills/`

职责：

- 将所有可执行能力封装为 Skill。
- 为 Graph 节点和 Planner Loop 提供统一调用接口。
- 通过白名单工具限制 Planner Loop 能力，不执行任意代码。
- 提供结构化错误和 fallback。

### 3.4 LLM 层

文件：`src/llm/`

职责：

- 提供统一 `LLMClient`。
- 支持 DeepSeek → OpenAI → Ollama → 规则 fallback。
- 提供 `chat()` 和 `chat_json()`。
- 集中维护中文 prompt。
- 对 JSON 输出做提取、重试、Pydantic 校验和 fallback。

### 3.5 Memory 层

文件：`src/memory/store.py` 与根目录 `memory/`

职责：

- 统一任务历史、用户偏好和图表偏好。
- 每次运行结束写入 JSONL。
- 运行前读取最近任务并构造中文 memory context。
- 使用文件型轻量长期记忆，不引入向量数据库。

### 3.6 Output 与 Utils 层

文件：`src/utils/` 与根目录 `outputs/`

职责：

- 管理上传文件、图表、报告、HTML、PDF 路径。
- 处理中文字体、Markdown 转 HTML/PDF、JSON 提取、文件名清洗和错误结构。

## 4. 目录结构

```text
CSV-Insight-Agent/
  app.py
  main.py
  requirements.txt
  README.md
  .env.example

  src/
    __init__.py
    config.py

    llm/
      __init__.py
      client.py
      prompts.py
      schemas.py

    graph/
      __init__.py
      state.py
      builder.py
      nodes/
        __init__.py
        memory_node.py
        profile_node.py
        route_node.py
        chart_planning_node.py
        chart_execution_node.py
        insight_node.py
        report_node.py
        safety_node.py
        export_node.py
        finalize_node.py
        planner_loop_node.py

    skills/
      __init__.py
      base.py
      registry.py
      csv_profile.py
      chart_suggest.py
      chart_plot.py
      insight_generate.py
      report_draft.py
      export_pdf.py
      memory_skill.py

    memory/
      __init__.py
      store.py

    utils/
      __init__.py
      file_utils.py
      json_utils.py
      chart_utils.py
      report_utils.py
      errors.py

  tests/
    __init__.py
    test_memory_store.py
    test_skill_registry.py
    test_csv_profile_skill.py
    test_chart_plot_skill.py
    test_llm_client_json.py
    test_graph_routing.py
    test_report_export.py

  examples/
    sales.csv
    students.csv

  memory/
    task_history.jsonl
    user_profile.json
    chart_preference.json
    .cursor

  outputs/
    uploads/
    charts/
    reports/
    html/
```

## 5. GraphState 设计

`GraphState` 使用 `TypedDict(total=False)`，便于不同模式共享同一个状态对象。

字段：

- `run_id: str`
- `mode: str`
- `csv_path: str`
- `csv_name: str`
- `user_query: str`
- `dataframe_profile: dict`
- `memory_context: str`
- `route_decision: dict`
- `chart_plan: dict | list`
- `generated_charts: list[dict]`
- `chart_explanations: list[str]`
- `analysis_insights: list[str]`
- `report_markdown: str`
- `report_path: str`
- `html_path: str`
- `pdf_path: str`
- `final_answer: str`
- `errors: list[str]`
- `retry_count: int`
- `status: str`

`errors` 存放结构化错误摘要，`status` 使用 `pending`、`running`、`completed`、`error`、`fallback` 等值。

## 6. LangGraph 工作流设计

主入口：

```text
START
  → load_memory_context
  → profile_csv
  → route_task
```

### 6.1 Quick Chart Mode

```text
route_task
  → plan_single_chart
  → execute_chart
  → explain_chart
  → finalize
  → END
```

职责：

- `plan_single_chart`：根据 profile、query、memory context 输出单图计划。
- `execute_chart`：调用 `plot_chart` Skill。
- `explain_chart`：调用 LLM 或规则 fallback 输出中文解释。
- `finalize`：写入 memory，整理最终回答。

### 6.2 Full Report Mode

```text
route_task
  → plan_multi_charts
  → execute_chart_batch
  → generate_insights
  → draft_report
  → safety_check
  → export_report
  → finalize
  → END
```

职责：

- `plan_multi_charts`：输出 2-6 个图表计划。
- `execute_chart_batch`：调用 `plot_chart_batch` Skill。
- `generate_insights`：生成 3-8 条中文洞察。
- `draft_report`：生成完整中文 Markdown 报告。
- `safety_check`：检查字段不存在、幻觉、过度推断等问题。
- `export_report`：导出 PDF，失败时导出 HTML。
- `finalize`：写入 memory，整理路径和下载信息。

`safety_check` 条件边：

```text
passed → export_report
failed 且 retry_count < 2 → draft_report
failed 且 retry_count >= 2 → finalize_error
```

### 6.3 Planner Loop Mode

```text
route_task
  → json_planner_loop
  → finalize
  → END
```

Planner Loop 逻辑：

```python
for step in range(max_steps):
    # 1. 注入 user_query、dataframe_profile、memory_context、available_skills
    # 2. LLM 输出 thought / tool_name / tool_args
    # 3. 如果 tool_name == final_answer，则结束
    # 4. 否则调用 SkillRegistry 白名单 Skill
    # 5. 将工具结果追加回 messages
    # 6. 工具失败时把结构化错误也追加给 LLM
```

默认 `max_steps=4`。Planner Loop 失败时根据用户选择或路由结果回退到 `chart_only` 或 `full_report` 固定流水线。

## 7. Skill Registry 设计

### 7.1 BaseSkill

每个 Skill 是一个类，包含：

- `name: str`
- `description: str`
- `args_schema: dict`
- `run(**kwargs) -> dict`
- `fallback_run(**kwargs) -> dict`

`fallback_run()` 默认返回结构化失败信息。图表、报告和 LLM 相关 Skill 可以覆盖 fallback。

### 7.2 SkillRegistry

提供：

- `register(skill)`
- `get(name)`
- `list_skills()`
- `describe_skills()`
- `call(name, **kwargs)`
- `get_call_log(limit=20)`

未知 Skill 返回：

```json
{
  "success": false,
  "error": "Unknown skill: <name>",
  "available_skills": ["profile_csv", "plot_chart"]
}
```

### 7.3 首批 Skills

| Skill | 来源 | 职责 |
|---|---|---|
| `profile_csv` | 两项目共有，优先复用 CSV-Plot-Agent | 读取 CSV，返回行列数、字段类型、缺失值、数值统计、样本数据 |
| `suggest_chart` | CSV-Plot-Agent | 根据字段类型和用户问题推荐图表 |
| `plot_chart` | CSV-Plot-Agent 扩展 | 生成单张图表 |
| `plot_chart_batch` | AI-Report-Generator + 扩展 | 批量生成多张图表 |
| `generate_insight` | 两项目共有 | 基于 profile、charts 和 query 生成中文洞察 |
| `draft_markdown_report` | AI-Report-Generator | 生成 Markdown 报告 |
| `export_pdf` | AI-Report-Generator | Markdown 转 PDF，失败时 HTML fallback |
| `read_recent_memory` | 合并增强 | 读取最近任务和用户偏好 |
| `save_memory` | 合并增强 | 保存任务历史 |

## 8. LLMClient 与 Prompt 设计

### 8.1 LLMClient

支持后端顺序：

```text
DeepSeek → OpenAI → Ollama → rules fallback
```

配置来自 `.env`：

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `USE_OLLAMA`
- `OLLAMA_MODEL`

接口：

- `chat(messages: list[dict]) -> str`
- `chat_json(messages: list[dict], schema=None, fallback=None) -> dict`
- `available_backends() -> list[str]`
- `active_backend() -> str`

`chat_json()` 处理：

1. 追加 JSON 输出要求。
2. 调用 LLM。
3. 从纯文本或 Markdown 代码块中提取 JSON。
4. 可选使用 Pydantic schema 校验。
5. JSON 解析或校验失败时重试。
6. 当前后端失败后切换下一个后端。
7. 全部失败时返回 fallback。

### 8.2 Prompt

Prompt 集中在 `src/llm/prompts.py`：

- `route_task_prompt`
- `chart_plan_prompt`
- `multi_chart_plan_prompt`
- `insight_prompt`
- `report_prompt`
- `safety_prompt`
- `planner_loop_prompt`

Prompt 均使用中文，要求 LLM 不编造字段、不编造数值，不确定时返回可执行 fallback 信息。

## 9. MemoryStore 设计

文件结构：

```text
memory/
  task_history.jsonl
  user_profile.json
  chart_preference.json
  .cursor
```

`task_history.jsonl` 每条记录至少包含：

- `cursor`
- `run_id`
- `timestamp`
- `mode`
- `csv_name`
- `query`
- `rows`
- `columns`
- `chart_count`
- `chart_types`
- `report_path`
- `chart_paths`
- `success`
- `error`

方法：

- `save_task(record: dict) -> int`
- `get_recent_tasks(limit: int = 5) -> list[dict]`
- `get_tasks_by_mode(mode: str) -> list[dict]`
- `get_tasks_by_chart_type(chart_type: str) -> list[dict]`
- `load_user_profile() -> dict`
- `save_user_profile(profile: dict) -> None`
- `load_chart_preference() -> dict`
- `save_chart_preference(preference: dict) -> None`
- `build_memory_context(query: str, limit: int = 5) -> str`

容错：

- 写入使用 `threading.Lock`。
- JSONL 读取跳过损坏行。
- `.cursor` 损坏时扫描历史最大 cursor 恢复。
- 文件不存在时自动创建空文件或默认 JSON。

Memory context 示例：

```text
以下是用户最近的数据分析任务摘要，可作为风格和偏好参考：
1. 最近多次使用 full_report 模式，偏好完整中文报告。
2. 常使用 line 图分析时间趋势。
3. 偏好报告中包含“结论建议”和“局限性说明”。
请参考这些偏好，但不要编造数据中不存在的事实。
```

## 10. 图表设计

支持图表：

- `line`
- `bar`
- `scatter`
- `histogram`
- `box`
- `correlation_heatmap`

规则：

- `x_col` 必须存在。
- `y_col` 如果提供，也必须存在。
- `line`、`scatter` 通常需要 x/y，其中 `y_col` 必须是数值列。
- `histogram` 只需要一个数值字段。
- `bar` 支持分类计数，也支持分类字段聚合数值字段。
- `box` 支持分类字段 + 数值字段。
- `correlation_heatmap` 至少需要两个数值字段。
- 没有数值列时只允许分类计数柱状图。
- 字段不存在时返回结构化错误和可选字段。
- 图表统一保存到 `outputs/charts/`。
- 文件名包含 `run_id`、`chart_type` 和序号。

中文字体：

- `SimHei`
- `Microsoft YaHei`
- `Arial Unicode MS`
- `Noto Sans CJK SC`
- `DejaVu Sans`

## 11. 报告与导出设计

Markdown 报告固定章节：

```markdown
# 数据分析报告

## 1. 数据概况
## 2. 分析目标
## 3. 核心发现
## 4. 图表分析
## 5. 综合结论
## 6. 建议
## 7. 局限性说明
```

图表引用使用相对路径：

```markdown
![图表标题](../charts/<filename>.png)
```

导出流程：

```text
Markdown → WeasyPrint PDF → HTML fallback
```

输出路径：

- Markdown：`outputs/reports/{run_id}.md`
- PDF：`outputs/reports/{run_id}.pdf`
- HTML：`outputs/html/{run_id}.html`

如果 WeasyPrint 不可用或系统缺少依赖，仍然生成 HTML，并在 UI 中展示提示。

## 12. UI 设计

`app.py` 使用 Streamlit 实现。

主区域：

- 标题与项目简介。
- CSV 上传。
- 模式选择。
- 用户问题输入。
- 运行按钮。
- 运行状态、错误、fallback 提示。
- Quick Chart：图表预览、中文解释、PNG 下载。
- Full Report：多图预览、Markdown 预览、PDF/HTML/Markdown 下载。
- Planner Loop：工具调用步骤、最终回答、产物下载。

侧边栏：

- 最近任务历史。
- 按图表类型筛选历史。
- 用户偏好摘要。
- LLM 当前可用后端。
- 输出目录说明。

## 13. 测试策略

使用 pytest。优先测试不依赖真实 LLM 的核心模块。

测试文件：

- `tests/test_memory_store.py`
  - 保存任务记录。
  - 读取最近任务。
  - 跳过损坏 JSON 行。
  - `.cursor` 损坏恢复。

- `tests/test_skill_registry.py`
  - 注册和调用 Skill。
  - 未知 Skill 返回结构化错误。
  - Skill 异常时调用 fallback。

- `tests/test_csv_profile_skill.py`
  - 对示例 CSV 生成 profile。
  - 返回数值列、类别列、缺失值和样本数据。

- `tests/test_chart_plot_skill.py`
  - 生成 line、bar、scatter、histogram、box、correlation_heatmap。
  - 字段不存在返回结构化错误。
  - 无数值列时 fallback 到分类计数图。

- `tests/test_llm_client_json.py`
  - 从纯 JSON 文本中提取。
  - 从 Markdown 代码块中提取。
  - 解析失败时返回 fallback。

- `tests/test_graph_routing.py`
  - Quick Chart 路由。
  - Full Report 路由。
  - Planner Loop 路由。

- `tests/test_report_export.py`
  - Markdown 保存。
  - HTML fallback。
  - PDF 导出失败时不阻断报告产物。

LLM 输出测试使用 fake client 或 fallback，不要求真实 API Key。

## 14. README 交付内容

README 标题：

```text
CSV-Insight-Agent：基于 LangGraph + Skill Registry + Memory 的 CSV 数据分析智能体
```

README 必须包含：

- 项目简介。
- 技术栈。
- 架构图。
- Agent 工作流。
- Skill Registry 设计。
- MemoryStore 设计。
- Quick Chart Mode 示例。
- Full Report Mode 示例。
- Planner Loop Mode 示例。
- LLM 多后端降级机制。
- 与传统 CSV 分析工具的区别。
- 项目亮点。
- 运行方式。
- 环境变量配置。
- 后续优化方向。
- 简历写法。

## 15. 实施顺序

实施按以下顺序推进：

1. 创建项目骨架、依赖文件、示例数据、README 初稿。
2. 实现 MemoryStore，并测试。
3. 实现 BaseSkill 和 SkillRegistry，并测试。
4. 实现 CSV profile、chart suggest、chart plot、chart batch，并测试。
5. 实现 LLMClient、JSON 工具和 prompt。
6. 实现 insight、report、export Skills，并测试。
7. 实现 GraphState、节点和 LangGraph builder。
8. 实现 Planner Loop 节点。
9. 实现 Streamlit UI。
10. 完善 README、运行说明和简历描述。
11. 运行测试并修复问题。

## 16. 范围边界

本版本包含：

- 文件型 memory，不引入数据库或向量数据库。
- 参数化图表生成，不允许 LLM 执行任意 Python 代码。
- 同步工作流，不引入异步队列或后台任务系统。
- Streamlit 单页应用，不做多用户权限系统。
- PDF 失败时可接受 HTML fallback。

本版本不包含：

- 多文件批量上传分析。
- 用户登录。
- 云端部署脚本。
- 向量检索记忆。
- 复杂 BI 仪表盘编辑器。

## 17. 成功标准

项目完成后应满足：

- `streamlit run app.py` 可以启动 UI。
- Quick Chart Mode 可以基于示例 CSV 生成 PNG 和中文解释。
- Full Report Mode 可以生成多图、Markdown 报告，并导出 PDF 或 HTML。
- Planner Loop Mode 可以展示 JSON 动作循环和 Skill 调用过程。
- MemoryStore 能写入并读取任务历史。
- README 能清晰解释架构、亮点、运行方式和简历价值。
- pytest 核心测试通过，且 LLM 相关测试不依赖真实 API Key。
