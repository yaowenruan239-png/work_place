# CSV-Insight-Agent：基于 LangChain Agent Loop + Skill Registry + Memory 的 CSV 数据分析智能体

CSV-Insight-Agent 是一个面向 CSV 数据的轻量智能分析 Agent，支持自动数据画像、图表规划、图表生成、中文洞察解释、多章节 Markdown/PDF 报告导出，并带有文件型长期记忆、Skill 化工具编排和 LangChain/ReAct-style Agent Loop。

## 技术栈

- UI：Streamlit
- 编排：LangChain AgentExecutor / LangGraph stable workflow
- LLM：DeepSeek / OpenAI / Ollama
- 数据：pandas / numpy
- 图表：matplotlib / seaborn
- 报告：Markdown / WeasyPrint / HTML fallback
- 记忆：JSONL / JSON

## 架构图

```text
Streamlit UI
  -> LangChain Agent Loop / LangGraph Stable Workflow
  -> LangChain Tools -> SkillRegistry
  -> pandas / matplotlib / LLMClient / MemoryStore
  -> PNG + Markdown + PDF/HTML + task_history.jsonl + chart_preference.json
```

## Agent 工作流

```text
START
  -> load_memory_context
  -> profile_csv
  -> route_task
     -> quick_chart: plan_single_chart -> execute_chart -> explain_chart -> finalize
     -> full_report: plan_multi_charts -> execute_chart_batch -> generate_insights -> draft_report -> safety_check -> export_report -> finalize
     -> planner_loop: json_planner_loop -> finalize
     -> agent_loop: langchain_agent_loop -> finalize
```

## Skill Registry 设计

所有可执行能力都封装为 Skill，并通过 `SkillRegistry` 调用。核心 Skill 包括：

- `profile_csv`
- `suggest_chart`
- `plot_chart`
- `plot_chart_batch`
- `generate_insight`
- `draft_markdown_report`
- `export_pdf`
- `read_recent_memory`
- `save_memory`

Planner Loop 只能调用这些白名单 Skill，不执行任意 Python 代码。

## MemoryStore 设计

`MemoryStore` 使用文件型轻量长期记忆：

```text
memory/task_history.jsonl
memory/user_profile.json
memory/chart_preference.json
memory/.cursor
```

它支持最近任务读取、按模式筛选、按图表类型筛选，并在 LLM 调用前构造中文 memory context。任务完成后会更新图表偏好计数，使后续图表推荐和 Agent Loop 能参考历史偏好。

## 执行模式

### Quick Chart Mode

上传 CSV 和输入问题，输出单张 PNG 图表和中文解释。

```bash
python main.py examples/sales.csv "分析销售趋势并画图" --mode quick_chart
```

### Full Report Mode

上传 CSV 和输入分析目标，输出多张图表、完整 Markdown 报告和 PDF/HTML。

Full Report Mode 会生成咨询报告风格的 HTML/PDF：封面、执行摘要、关键指标卡片、核心发现、图文交错分析、行动建议、局限性说明和字段附录。WeasyPrint 是主 PDF 引擎；如果本机缺少 GTK/Pango/Cairo 等系统库，会自动保留 HTML fallback，工作流不会因为 PDF 失败而中断。

```bash
python main.py examples/sales.csv "生成完整销售数据分析报告" --mode full_report
```

### Planner Loop Mode

LLM 输出 JSON 动作，系统通过 SkillRegistry 调用白名单 Skill，并展示工具调用过程。

Planner Loop Mode 会展示每一步 Planner Trace：模型想法、工具名、自动补齐后的参数、工具结果摘要和错误原因。该模式适合演示 Agent 如何逐步规划和调用工具。

```bash
python main.py examples/sales.csv "自动选择工具分析销售数据" --mode planner_loop
```

### LangChain Agent Loop Mode

LangChain Agent Loop Mode 使用 LangChain Tools 包装现有 Skill，并通过 ReAct-style Thought -> Action -> Observation 循环调用工具。该模式用于展示大模型如何一步步决策，自动完成 CSV 数据画像、图表生成、洞察总结和报告导出。

```bash
python main.py examples/sales.csv "自动分析销售数据，选择图表并生成 PDF 报告" --mode agent_loop
```

## Experience Memory Integration

CSV-Insight-Agent 可选通过 HTTP 接入 `Agent-Experience-Memory` 的 Python API Service。当前项目的 `src/experience_memory_adapter.py` 会在 Agent 执行前请求 `http://127.0.0.1:8090/memory/search_context` 检索历史经验，并把相关经验追加注入 prompt；同时在关键工具抛出异常时请求 `/memory/record_error` 记录错误上下文，便于后续沉淀经验。

这是可选增强功能：

- 不启动 `Agent-Experience-Memory` 时，CSV-Insight-Agent 仍可按原流程正常运行。
- 启动后，Agent 执行前会根据用户问题检索历史经验并注入上下文。
- CSV 项目不 import `Agent-Experience-Memory` 的 Python 内部模块，不生成 embedding，不直接连接 MySQL。
- CSV 环境不需要安装 `mysql-connector-python`、`sentence-transformers`、`torch` 或 `transformers`。
- 原有 `MemoryStore` 文件型记忆不变，`memory/task_history.jsonl`、`memory/user_profile.json`、`memory/chart_preference.json` 仍然照常使用。
- 该集成不复制 `Agent-Experience-Memory` 代码，不引入 Redis，也不改变主流程。

详见 `docs/experience_memory_integration.md`。

## LLM 多后端降级机制

`LLMClient` 按以下顺序检测可用后端：

```text
DeepSeek -> OpenAI -> Ollama -> rules fallback
```

`chat_json()` 会提取 JSON、进行可选 Pydantic 校验，并在解析失败时重试。

## 环境变量

复制 `.env.example` 为 `.env`，填入你的 DeepSeek API Key：

```dotenv
DEEPSEEK_API_KEY=sk-your-deepseek-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

不要提交 `.env`。

## 运行方式

```bash
pip install -r requirements.txt
streamlit run app.py
```

CLI：

```bash
python main.py examples/sales.csv "分析销售趋势" --mode quick_chart
python main.py examples/sales.csv "自动分析销售数据并生成报告" --mode agent_loop
```

## 与传统 CSV 工具的区别

传统 CSV 工具通常需要手动选择字段和图表。CSV-Insight-Agent 将 CSV 任务拆成可解释的 Agent 流程：LLM 负责理解、规划和表达，LangChain Agent Loop 负责 ReAct-style 工具循环，Python Skill 负责安全执行，LangGraph 保留稳定工作流，MemoryStore 负责长期上下文。

## 项目亮点

- 使用 LangChain Tools + Agent Loop 实现 ReAct-style Thought -> Action -> Observation 工具循环。
- 使用 LangGraph 构建稳定的 Quick Chart / Full Report 工作流。
- 使用 Skill Registry 管理工具能力。
- 使用 JSON Planner Loop 展示轻量 Agent 决策过程。
- 使用文件型 MemoryStore 注入最近任务上下文，并自动沉淀图表偏好。
- 使用 LLMClient 实现多模型降级和 JSON 解析重试。
- 使用参数化图表生成，避免执行任意 LLM 代码。

## 后续优化方向

- 增加更多图表类型。
- 增加报告模板选择。
- 增加多 CSV 对比分析。
- 增加可选向量记忆。
- 增加部署配置。

## 简历写法

设计并实现基于 LangChain Agent Loop 的 CSV 数据分析智能体，支持用户上传 CSV 后由 LLM 通过 ReAct-style Thought -> Action -> Observation 循环自动调用 profile_csv、suggest_chart、plot_chart_batch、generate_insight、export_pdf 等工具，完成数据画像、图表生成、洞察总结和 Markdown/PDF/HTML 报告导出；使用自定义 SkillRegistry 适配 LangChain Tool 接口，并通过 JSONL MemoryStore 保存历史任务与图表偏好，为后续分析注入 memory context。
