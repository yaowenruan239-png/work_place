# Experience Memory Integration

CSV-Insight-Agent 通过 HTTP 接入 `Agent-Experience-Memory`，作为可选经验记忆增强服务。该集成不会替换当前项目已有的 `MemoryStore` 文件型记忆，也不会改变原有主流程；服务不可用时会自动 fallback。

## 新旧集成方式

旧方式：

```text
CSV Agent 直接 import ../Agent-Experience-Memory/python_client
```

旧方式会让 CSV 项目运行环境被迫安装经验记忆服务内部依赖，例如：

- `mysql-connector-python`
- `sentence-transformers`
- `torch`
- `transformers`

新方式：

```text
CSV-Insight-Agent-master
  -> HTTP requests
  -> Agent-Experience-Memory Python API Service :8090
  -> C++ Memory Service :8080
  -> MySQL
```

CSV 项目只请求：

```text
http://127.0.0.1:8090/memory/search_context
http://127.0.0.1:8090/memory/record_error
```

好处：

- CSV 环境不需要 `mysql-connector-python`。
- CSV 环境不需要 `sentence-transformers` / `torch` / `transformers`。
- CSV 项目不生成 embedding，不直接连接 MySQL。
- `Agent-Experience-Memory` 保持独立服务边界。
- 服务不可用时 CSV Agent fallback 原流程。

## 启动 Agent-Experience-Memory

在兄弟目录中启动 MySQL、C++ Memory Service 和 Python API Service：

```bash
cd ../Agent-Experience-Memory
./start.sh start --install-deps --seed
```

后续日常启动可以使用：

```bash
cd ../Agent-Experience-Memory
./start.sh start
```

查看服务状态：

```bash
./start.sh status
```

健康检查：

```bash
curl --noproxy "*" http://127.0.0.1:8080/health
curl --noproxy "*" http://127.0.0.1:8090/health
```

## CSV-Insight-Agent 如何调用经验记忆

当前项目的 `src/experience_memory_adapter.py` 只依赖：

- `os`
- `typing`
- `requests`
- Python 标准库

它不会把兄弟目录加入 `sys.path`，也不会 import `Agent-Experience-Memory` 的任何 Python 模块。

默认 API 地址：

```text
http://127.0.0.1:8090
```

可通过环境变量覆盖：

```bash
export EXPERIENCE_MEMORY_API_URL="http://127.0.0.1:8090"
```

Agent 执行前会调用：

```text
POST /memory/search_context
```

请求体示例：

```json
{
  "query": "任务类型：csv_analysis\n用户问题：请分析每个月的销售金额趋势，并生成柱状图",
  "top_k": 3,
  "min_score": 0.25
}
```

返回的 `context` 会追加到 LangChain Agent Loop 的用户输入中：

```text
经验记忆上下文：
以下是系统过去执行类似任务时总结出的经验，请优先遵守：
...
```

同时，adapter 会保存最近一次检索状态：

- `get_last_experience_memory_warning()`：返回未注入经验的原因或错误提示。
- `get_last_experience_memories()`：返回最近命中的经验条目。

原有 `memory/task_history.jsonl`、`memory/user_profile.json`、`memory/chart_preference.json` 仍然照常工作。

## 工具错误记录

`safe_tool_call()` 会包装关键工具调用。当前最小接入点包括：

- LangChain Tool 统一执行路径：`src/agent/langchain_tools.py`
- LangGraph 图表执行路径：`src/graph/nodes/chart_execution_node.py`

当工具抛出异常时，adapter 会调用：

```text
POST /memory/record_error
```

请求体包含：

- `task_type`
- `user_query`
- `tool_name`
- `error_message`
- `context`
- `run_id`

错误记录失败时只打印 warning，不影响 CSV Agent 主流程，并重新抛出原异常，保持原错误行为。

注意：如果图表工具只是返回 `{"success": false, "error": ...}` 而没有抛异常，则不会改变当前返回式错误处理逻辑。

## 服务不可用时的 fallback

该集成是可选增强：

- 如果 Python API Service 未启动、HTTP 请求失败或错误写入失败，CSV-Insight-Agent 都不会崩溃。
- `get_experience_context()` 会打印 warning 并返回空字符串。
- prompt 中不会追加经验记忆上下文，Agent 按原有流程继续运行。
- `safe_tool_call()` 在错误记录失败时只打印 warning，仍重新抛出原异常。

## 字段名错误前后对比案例

### 未启用经验记忆

用户问题：

```text
分析销售趋势，按月份画销售额柱状图
```

如果模型误把 CSV 字段 `销售额` 写成 `销售金额`，图表工具可能返回：

```text
列不存在: 销售金额
```

Agent 只能依赖当前 `profile_csv` 的字段建议自行修正。

### 启用经验记忆后

历史经验中可以沉淀类似提示：

```text
生成图表前必须以 profile_csv 返回的 columns 为准；不要臆造近义字段名。若用户说“销售金额”，但 CSV 只有“销售额”，应使用真实字段“销售额”。
```

新任务执行前，CSV-Insight-Agent 会通过 Python API Service 检索并注入该经验。模型在调用 `plot_chart` 前更可能核对 `columns`，避免把 `销售额` 写成不存在的 `销售金额`。
