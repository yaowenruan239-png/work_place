# CSV-Insight-Agent 改为 LangChain + LLM Agent Loop 的改造计划

## 1. 目标

你引用的 `csv-insight-agent-fit-analysis.md` 第 12-18 行核心要求是：

```text
LLM Agent Loop
+ Tool / Skill 调用
+ 记忆模块
+ 自动完成具体任务
+ 有可展示产物，比如图表或 PDF
+ 项目规模不要太大
+ 写在简历上看起来高级
```

当前项目已经有 LangGraph、SkillRegistry、PlannerLoop、MemoryStore、图表生成、PDF/HTML 报告生成。下一步你的明确要求是：

```text
框架我要改为 LangChain，有 LLM agent loop 等。
```

所以本计划的目标是：

```text
把 CSV-Insight-Agent 从“LangGraph 工作流 + 自定义 PlannerLoop”升级为“LangChain AgentExecutor + Tools + Memory 的 ReAct-style CSV 数据分析 Agent”。
```

最终项目定位：

```text
基于 LangChain Agent Loop、Tool Calling、MemoryStore 的 CSV 数据分析智能体，支持自动数据画像、图表生成、洞察总结和 PDF/HTML 报告导出。
```

## 2. 改造原则

### 2.1 不建议完全删除 LangGraph

虽然你说框架要改为 LangChain，但建议不要把 LangGraph 立刻全部删掉。

原因：

- 当前 LangGraph 工作流已经稳定。
- Full Report 和 Quick Chart 路径能保证确定性产出。
- LangChain Agent Loop 更适合展示“LLM 一步步决策”，但稳定性可能弱于固定工作流。

推荐改法：

```text
LangChain Agent Loop 作为主打 planner_loop 模式；
LangGraph 固定工作流作为 stable workflow 保留。
```

也就是：

```text
quick_chart / full_report：仍可走稳定工作流
agent_loop：走 LangChain AgentExecutor
```

如果你后续坚持完全改成 LangChain，也可以第二阶段再移除 LangGraph。

### 2.2 保留 SkillRegistry，但包装成 LangChain Tools

当前项目已有 Skill：

- `profile_csv`
- `suggest_chart`
- `plot_chart`
- `plot_chart_batch`
- `generate_insight`
- `draft_markdown_report`
- `export_pdf`
- `read_recent_memory`
- `save_memory`

不要推倒重写。

建议新增一层：

```text
src/agent/langchain_tools.py
```

负责把现有 Skill 包装成 LangChain Tool。

这样项目改造成本低，也能在简历上说：

```text
将自定义 Skill Registry 适配为 LangChain Tool 接口，使 AgentExecutor 能通过 ReAct 循环调用数据分析工具。
```

### 2.3 让 LangChain Agent Loop 完成完整任务

最终要实现用户输入：

```text
请分析这个销售 CSV，自动选择图表，生成洞察，并导出 PDF 报告。
```

Agent 自动执行：

```text
Thought: 先读取 CSV 结构
Action: profile_csv
Observation: 36 行 6 列，包含销售额、利润、客户数

Thought: 需要推荐图表
Action: suggest_chart
Observation: 推荐 bar、scatter、correlation_heatmap

Thought: 批量生成图表
Action: plot_chart_batch
Observation: 生成 3 张图表

Thought: 根据图表生成洞察
Action: generate_insight
Observation: 生成 5 条洞察

Thought: 生成报告并导出 PDF/HTML
Action: draft_markdown_report / export_pdf
Observation: 报告已生成

Final Answer: 已完成分析，报告路径为...
```

这才真正满足“LLM Agent Loop + Tool 调用 + 自动完成目标”。

## 3. 目标架构

推荐改造后的结构：

```text
Streamlit UI / CLI
  -> LangChainCSVAgent
      -> ChatOpenAI / ChatOllama
      -> AgentExecutor
      -> ReAct Prompt
      -> LangChain Tools
          -> SkillRegistry
              -> profile_csv
              -> suggest_chart
              -> plot_chart_batch
              -> generate_insight
              -> draft_markdown_report
              -> export_pdf
      -> MemoryStore
      -> Agent Trace
  -> outputs
      -> charts
      -> reports
      -> html
      -> memory/task_history.jsonl
```

建议新增目录：

```text
src/agent/
  __init__.py
  langchain_agent.py
  langchain_tools.py
  trace.py
  prompts.py
```

各文件职责：

| 文件 | 职责 |
|---|---|
| `src/agent/langchain_agent.py` | 创建和运行 LangChain AgentExecutor |
| `src/agent/langchain_tools.py` | 把现有 Skill 包装成 LangChain Tools |
| `src/agent/trace.py` | 收集 Agent Thought / Action / Observation |
| `src/agent/prompts.py` | 存放 ReAct-style system prompt |
| `src/planner/runner.py` | 可逐步废弃或作为 fallback 保留 |
| `src/skills/registry.py` | 保留，作为底层工具注册和执行系统 |
| `src/memory/store.py` | 保留并增强偏好记忆 |

## 4. 依赖调整

当前 `requirements.txt` 已经有：

```text
langchain-core
langchain-openai
langchain-community
```

如果要使用 LangChain AgentExecutor，需要确认版本支持：

```text
langchain
langchain-core
langchain-openai
langchain-community
```

建议新增或明确：

```text
langchain~=0.3
```

注意：LangChain 版本变化比较快，建议锁定兼容版本，避免 API 变动。

## 5. 核心改造任务

### Task 1：新增 LangChain Tool 适配层

新增：

```text
src/agent/langchain_tools.py
```

目标：把现有 Skill 包成 LangChain Tool。

推荐设计：

```text
build_langchain_tools(registry, runtime_context) -> list[BaseTool]
```

每个 Tool 内部调用：

```text
registry.call(skill_name, **normalized_args)
```

需要处理：

- 自动注入 `csv_path`
- 自动注入 `run_id`
- 自动注入 `profile`
- 自动注入 `charts`
- 自动注入 `insights`
- 自动注入 `query`
- 自动注入 `markdown`

当前 `PlannerLoopRunner._normalize_args()` 里已经有类似逻辑，可以迁移复用。

建议不要让 LangChain Tool 直接操作复杂全局状态，而是传入一个 `runtime_context` dict。

示例上下文：

```python
runtime_context = {
    "run_id": state["run_id"],
    "csv_path": state["csv_path"],
    "query": state["user_query"],
    "profile": state.get("dataframe_profile", {}),
    "charts": state.get("generated_charts", []),
    "insights": state.get("analysis_insights", []),
    "markdown": state.get("report_markdown", ""),
}
```

每次工具调用成功后更新 runtime_context。

### Task 2：新增 LangChain Agent Runner

新增：

```text
src/agent/langchain_agent.py
```

核心类：

```text
LangChainCSVAgent
```

职责：

- 创建 LLM
- 创建 tools
- 创建 ReAct prompt
- 创建 AgentExecutor
- 运行用户任务
- 返回 final_answer、steps、updated_state

推荐接口：

```python
class LangChainCSVAgent:
    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        ...
```

返回 state 中应包含：

```text
final_answer
agent_steps
generated_charts
analysis_insights
report_markdown
report_path
pdf_path
html_path
status
errors
```

### Task 3：设计 ReAct Prompt

新增：

```text
src/agent/prompts.py
```

Prompt 应明确：

```text
你是 CSV 数据分析 Agent。
你必须通过工具完成任务，不要编造数据。
你要按以下顺序优先完成：
1. 读取 CSV profile
2. 推荐图表
3. 生成图表
4. 生成洞察
5. 生成 Markdown 报告
6. 导出 PDF/HTML
7. 给出最终答案
```

并强调：

```text
每一步都必须基于上一步 Observation。
只使用工具返回的数据。
不要编造 CSV 中不存在的字段。
```

如果使用 LangChain ReAct Agent，格式应适配 LangChain 默认 ReAct：

```text
Thought: ...
Action: tool_name
Action Input: ...
Observation: ...
Final Answer: ...
```

### Task 4：Agent Trace 收集

新增：

```text
src/agent/trace.py
```

目标：保存 LangChain Agent 每一步：

```text
step_index
thought
action
action_input
observation
success
error
generated_files
```

可借鉴当前 `PlannerStepTrace`，也可复用它。

Streamlit UI 中展示为：

```text
Step 1
Thought
Action
Action Input
Observation
```

这就是你哥提到的“让大模型一步一步决策”的可视化证据。

### Task 5：新增 LangChain Agent Graph Node

如果保留 LangGraph，可以新增节点：

```text
src/graph/nodes/langchain_agent_node.py
```

节点逻辑：

```python
def langchain_agent_loop(state):
    return LangChainCSVAgent().run(state)
```

然后在 `builder.py` 里加入：

```text
agent_loop -> langchain_agent_loop -> finalize
```

同时修改 route：

```text
quick_chart
full_report
agent_loop
```

或者把原来的 `planner_loop` 改为 LangChain 实现。

### Task 6：增强 MemoryStore

为了满足“记忆模块”，建议新增：

```text
update_chart_preference(chart_types, mode)
```

保存到：

```text
memory/chart_preference.json
```

结构示例：

```json
{
  "chart_type_counts": {
    "bar": 5,
    "line": 3,
    "scatter": 2
  },
  "last_used_chart_types": ["bar", "scatter"],
  "preferred_report_mode": "full_report"
}
```

`build_memory_context()` 中加入：

```text
用户历史常用图表类型为 bar、line，可在合适场景优先推荐。
```

这样记忆不只是存储，而是真的参与 Agent 决策。

### Task 7：Streamlit UI 增加 Agent Loop 模式

修改：

```text
app.py
```

UI 模式建议：

```text
Quick Chart
Full Report
LangChain Agent Loop
```

在 LangChain Agent Loop 模式下展示：

- Agent Trace
- 图表结果
- 报告下载
- Memory 使用情况
- Final Answer

重点展示：

```text
Thought -> Action -> Observation
```

### Task 8：测试

新增测试：

```text
tests/test_langchain_tools.py
tests/test_langchain_agent.py
tests/test_agent_trace.py
```

测试重点：

1. Tool wrapper 能调用 SkillRegistry。
2. Tool wrapper 能自动注入上下文参数。
3. Agent runner 能接收 fake LLM 输出并执行多步工具。
4. MemoryStore 能更新图表偏好。
5. UI 依赖字段 `agent_steps` 不丢失。

## 6. 分阶段实施计划

### Phase 1：保留现有项目，新增 LangChain Agent Loop

目标：不要破坏现有稳定功能，先加新模式。

改动：

- 新增 `src/agent/`
- 新增 LangChain Tool wrapper
- 新增 LangChain Agent runner
- 新增 ReAct prompt
- 新增 trace model
- route 中新增 `agent_loop`

验收：

```text
python main.py examples/sales.csv "自动分析销售数据并生成 PDF 报告" --mode agent_loop
```

能看到 Agent 调用多个工具，并生成图表和报告。

### Phase 2：让 LangChain Agent Loop 成为主打模式

目标：对外宣传时主推 LangChain Agent Loop。

改动：

- README 改成 LangChain + Skill + Memory 叙述
- Streamlit 默认推荐 Agent Loop
- Planner Trace 改成 Agent Trace
- 完整 demo 文档

验收：

打开 README 第一屏就能看到：

```text
LangChain Agent Loop
Tool Calling
Memory
CSV Chart Generation
PDF Report Export
```

### Phase 3：增强记忆和工具稳定性

目标：让项目更像成熟 Agent 应用。

改动：

- SkillRegistry.prepare_call
- 参数校验
- 工具名建议
- chart preference 自动学习
- memory context 影响图表推荐

验收：

重复运行几次后，memory context 中出现历史图表偏好，并影响后续推荐。

### Phase 4：可选移除或弱化 LangGraph

如果你坚持“框架改为 LangChain”，最后可以：

- README 中把 LangChain 放第一位
- LangGraph 只作为 legacy stable workflow
- 或完全删除 LangGraph 工作流，CLI/UI 统一走 LangChain Agent

但不建议一开始就删，因为现有 LangGraph 保证了稳定产物。

## 7. 新旧架构对比

### 当前架构

```text
Streamlit / CLI
  -> LangGraph Workflow
      -> profile_csv
      -> route_task
      -> plan_chart
      -> execute_chart
      -> generate_insight
      -> draft_report
      -> export_report
  -> SkillRegistry
  -> MemoryStore
```

### 改造后架构

```text
Streamlit / CLI
  -> LangChainCSVAgent
      -> AgentExecutor
      -> ReAct Prompt
      -> LangChain Tools
          -> SkillRegistry
      -> MemoryStore Context
      -> Agent Trace
  -> outputs/charts
  -> outputs/reports
```

### 推荐过渡架构

```text
Streamlit / CLI
  -> mode = quick_chart      -> LangGraph stable workflow
  -> mode = full_report      -> LangGraph stable workflow
  -> mode = agent_loop       -> LangChain AgentExecutor
```

## 8. 最小可行版本

如果时间有限，只做这些：

```text
1. 新增 src/agent/langchain_tools.py
2. 新增 src/agent/langchain_agent.py
3. 新增 src/agent/prompts.py
4. 新增 agent_loop 模式
5. UI 展示 Thought / Action / Observation
```

这五项完成后，就能满足核心要求：

```text
LLM Agent Loop + Tool 调用 + 记忆 + 图表/PDF 产物
```

## 9. 简历写法

改造完成后可以写：

```text
设计并实现基于 LangChain AgentExecutor 的 CSV 数据分析智能体，支持用户上传 CSV 后由 LLM 通过 ReAct-style Thought -> Action -> Observation 循环自动调用 profile_csv、suggest_chart、plot_chart_batch、generate_insight、export_pdf 等工具，完成数据画像、图表生成、洞察总结和 PDF/HTML 报告导出。项目通过自定义 SkillRegistry 适配 LangChain Tool 接口，并使用 JSONL MemoryStore 保存历史任务和图表偏好，为后续分析注入 memory context。
```

英文版：

```text
Built a LangChain-based CSV analysis agent that uses an LLM Agent Loop with ReAct-style Thought -> Action -> Observation reasoning to call tools for CSV profiling, chart planning, batch visualization, insight generation, and PDF/HTML report export. Adapted a custom Skill Registry into LangChain Tools and added a lightweight JSONL MemoryStore to persist task history and chart preferences for memory-aware analysis.
```

## 10. 最终建议

你要尽量满足你哥说的方向，最关键不是“把所有代码都换成 LangChain”，而是让项目具备一个清晰可演示的 LangChain Agent Loop：

```text
用户目标
-> LLM 思考
-> 调用 Tool
-> 得到 Observation
-> 再思考
-> 再调用 Tool
-> 最终生成图表和 PDF 报告
```

因此推荐：

```text
先新增 LangChain Agent Loop 模式，不破坏现有 LangGraph 稳定流程；
再把 Agent Loop 做成主打亮点；
最后根据需要弱化或移除 LangGraph。
```

这样项目既能满足“框架改为 LangChain”的要求，也能保留当前项目已经实现好的图表、报告、记忆和测试能力。
