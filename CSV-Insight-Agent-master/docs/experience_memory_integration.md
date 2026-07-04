# Experience Memory Integration

CSV-Insight-Agent 已最小化接入兄弟目录 `../Agent-Experience-Memory` 作为可选经验记忆服务。该集成不会替换当前项目已有的 `MemoryStore` 文件型记忆，也不会改变原有主流程；服务不可用时会自动 fallback。

## 启动 Agent-Experience-Memory

在兄弟目录中启动 MySQL、初始化数据、启动 C++ 检索服务：

```bash
cd ../Agent-Experience-Memory
docker compose up -d
pip install -r requirements.txt
python -m python_client.seed_data
```

构建并启动 C++ Memory Service：

```bash
cd ../Agent-Experience-Memory/cpp_memory_service
mkdir -p build
cd build
cmake ..
cmake --build .
./agent_memory_service
```

服务默认监听：

```text
http://127.0.0.1:8080
```

可选健康检查：

```bash
curl --noproxy "*" http://127.0.0.1:8080/health
```

## 加载经验索引

C++ 服务启动后，在 `../Agent-Experience-Memory` 根目录执行：

```bash
NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" python -m python_client.load_cpp_index
```

该命令会从 MySQL 读取 `experience_memories` / `memory_vectors` 中的经验向量，并加载到 C++ 内存索引。后续 CSV-Insight-Agent 会通过 HTTP 检索相似经验。

## CSV-Insight-Agent 如何调用经验记忆

当前项目新增了 `src/experience_memory_adapter.py`：

- 动态把 `../Agent-Experience-Memory` 加入 `sys.path`。
- 导入 `python_client.memory_client.ExperienceMemoryClient`。
- 创建 `ExperienceMemoryClient("http://127.0.0.1:8080")`。
- 在 Agent 执行前调用 `get_experience_context(user_query, task_type="csv_analysis")`。
- 检索 top 3 且分数不低于 0.25 的经验，并用 `build_prompt_context()` 构造中文 prompt context。

LangChain Agent Loop 的用户输入会在原有 `MemoryStore` 上下文后追加：

```text
经验记忆上下文：
以下是系统过去执行类似任务时总结出的经验，请优先遵守：
...
```

原有 `memory/task_history.jsonl`、`memory/user_profile.json`、`memory/chart_preference.json` 仍然照常工作。

## 工具错误记录

`safe_tool_call()` 会包装关键工具调用。当前最小接入点包括：

- LangChain Tool 统一执行路径：`src/agent/langchain_tools.py`
- LangGraph 图表执行路径：`src/graph/nodes/chart_execution_node.py`

当工具抛出异常时，adapter 会调用 `python_client.error_collector.record_error()` 写入错误日志，然后重新抛出原异常，保持原错误行为。记录上下文尽量包含：

- `columns`
- `dtypes`
- `user_query`
- `chart_spec`
- `tool_name`
- `tool_args`
- `csv_path`
- `run_id`

注意：如果图表工具只是返回 `{"success": false, "error": ...}` 而没有抛异常，则不会改变当前返回式错误处理逻辑。

## 服务不可用时的 fallback

该集成是可选增强：

- 如果 `../Agent-Experience-Memory` 不存在、Python client 导入失败、C++ 服务未启动、HTTP 检索失败或错误写入失败，CSV-Insight-Agent 都不会崩溃。
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

新任务执行前，CSV-Insight-Agent 会检索并注入该经验。模型在调用 `plot_chart` 前更可能核对 `columns`，避免把 `销售额` 写成不存在的 `销售金额`。
