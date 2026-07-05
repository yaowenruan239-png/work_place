# CSV-Insight-Agent 接入 Agent-Experience-Memory 当前核心问题

本文仅保留当前最严重、最影响体验和架构边界的几个问题。

## 背景

当前目标是让 `CSV-Insight-Agent-master` 在执行前调用 `Agent-Experience-Memory`，检索历史经验并注入 Agent Prompt，从而减少字段名幻觉、工具参数错误和重复失败调用。

理想链路：

```text
CSV-Insight-Agent 用户问题
-> 经验记忆服务检索相似经验
-> 构造 prompt context
-> 注入 LangChain Agent Prompt
-> Agent 更谨慎地调用工具
```

但当前接入方式仍有几个关键问题需要优先处理。

## 问题一：CSV Agent 直接导入 Agent-Experience-Memory Python Client，导致依赖边界不清晰

当前 `CSV-Insight-Agent-master/src/experience_memory_adapter.py` 通过 `sys.path` 动态导入兄弟项目：

```python
from python_client.memory_client import ExperienceMemoryClient
from python_client.error_collector import record_error
```

这会导致 `CSV-Insight-Agent` 的运行环境不仅要能找到 `Agent-Experience-Memory` 的代码，还必须安装它的 Python 依赖。

目前已经出现的问题是：

```text
Warning: experience memory client unavailable: No module named 'mysql.connector'
```

也就是说，`Agent-Experience-Memory` 服务本身虽然已经启动，但 `CSV-Insight-Agent` 所在的 `report` 环境缺少 `mysql-connector-python`，导致经验记忆无法注入。

### 影响

- 服务启动成功不等于 CSV Agent 能用。
- UI 显示“未注入经验记忆”。
- 用户容易误判为 C++ 服务或 MySQL 没启动。
- 破坏了“Agent-Experience-Memory 作为独立记忆服务”的边界。

### 结论

这是当前最核心的问题：

```text
CSV-Insight-Agent 不应该直接 import Agent-Experience-Memory 的内部 Python Client。
```

更合理的方式是通过 HTTP 调用独立服务。

## 问题二：如果安装完整依赖，会把 sentence-transformers / torch / CUDA 引入 report 环境

`Agent-Experience-Memory/requirements.txt` 当前包含：

```text
mysql-connector-python
sentence-transformers
requests
python-dotenv
```

其中最重的是：

```text
sentence-transformers
```

对它执行 dry-run 后发现，它会安装大量依赖：

```text
torch
transformers
scikit-learn
scipy
huggingface-hub
triton
cuda-toolkit
nvidia-cublas
nvidia-cudnn-cu13
nvidia-cusolver
nvidia-cusparse
nvidia-nccl-cu13
...
```

虽然 dry-run 显示不会修改当前 `numpy==2.2.6`，但这些依赖会显著污染 `CSV-Insight-Agent` 的 `report` 环境。

### 影响

- 安装体积大，耗时长。
- `report` 环境会被 PyTorch / Transformers / CUDA 依赖污染。
- 后续维护和排查问题更复杂。
- CSV 报告生成环境与 embedding 模型环境耦合。

### 结论

不建议执行：

```bash
pip install -r ../Agent-Experience-Memory/requirements.txt
```

也不建议把 `sentence-transformers` 安装到 `CSV-Insight-Agent` 的 `report` 环境里。

短期如果只为排查，可以只安装轻量依赖：

```bash
pip install mysql-connector-python
```

但这不是最终方案，因为后续仍可能遇到 `sentence_transformers` 缺失问题。

## 问题三：当前 C++ Memory Service 只支持 vector 检索，不能直接接收 text query

当前 C++ 服务的核心接口是：

```text
POST /index/search
body: { "vector": [...], "top_k": 3 }
```

它只负责：

```text
vector -> cosine similarity top-k -> memory_id
```

它不负责：

```text
text query -> embedding
memory_id -> MySQL 查询经验正文
prompt context 构造
```

这些逻辑现在都在 `Agent-Experience-Memory` 的 Python Client 中。

### 影响

因为 C++ 服务不支持文本检索，所以 `CSV-Insight-Agent` 如果想检索经验，就必须自己导入 Python Client 并在本进程生成 embedding。

这正是导致问题一、问题二的根源。

### 结论

当前服务边界不完整。

`Agent-Experience-Memory` 如果要作为独立记忆服务，应该对外提供文本级接口，例如：

```text
POST /memory/search_context
body: {
  "query": "任务类型：csv_analysis\n用户问题：...",
  "top_k": 3,
  "min_score": 0.25
}

return: {
  "context": "以下是系统过去执行类似任务时总结出的经验，请优先遵守：...",
  "memories": [...]
}
```

这样 `CSV-Insight-Agent` 只需要依赖 `requests`，不需要安装 MySQL、embedding、torch 相关依赖。

## 问题四：当前 UI 能显示经验记忆区域，但由于检索链路未通，实际没有注入经验

目前 UI 已经能显示：

```text
本次检索到的经验记忆
Agent 实际输入 / Prompt
Agent 执行过程 / ReAct 工具调用
```

但因为 `CSV-Insight-Agent` 环境无法成功导入经验记忆 Python Client，所以实际显示的是：

```text
未注入经验记忆：experience memory client unavailable: No module named 'mysql.connector'
```

### 影响

- 用户可以看到诊断信息，但还不能真正体验“经验记忆注入 Prompt”。
- 当前演示只能证明 CSV Agent 自身可以完成分析，不能充分展示 Agent-Experience-Memory 的价值。

### 结论

UI 展示不是主要问题，主要问题是后端检索链路没有以独立服务方式打通。

## 最推荐的后续方案

优先做下面这个改造：

```text
在 Agent-Experience-Memory 中新增 Python HTTP search-context 服务；
CSV-Insight-Agent 改为只通过 requests 调用该服务；
不再直接导入 Agent-Experience-Memory 的 Python Client。
```

推荐新链路：

```text
CSV-Insight-Agent
-> requests.post("http://127.0.0.1:<python_api_port>/memory/search_context")
-> Agent-Experience-Memory Python API
-> sentence-transformers 生成 query embedding
-> C++ Memory Service 做 top-k 检索
-> MySQL 查询经验正文
-> 返回 prompt context
-> CSV-Insight-Agent 注入 Prompt
```

这样可以做到：

- `CSV-Insight-Agent` 不安装 `sentence-transformers`。
- `CSV-Insight-Agent` 不直接连接 MySQL。
- `report` 环境不被 torch / CUDA 依赖污染。
- `Agent-Experience-Memory` 才是真正独立的经验记忆服务。
- UI 中可以稳定显示“本次检索到的经验记忆”。

## 当前优先级排序

1. **最高优先级**：取消 CSV Agent 对 `Agent-Experience-Memory` Python Client 的直接导入，改为 HTTP 调用。
2. **高优先级**：在 `Agent-Experience-Memory` 侧新增文本级 `search_context` API。
3. **中优先级**：启动脚本同时管理 C++ 检索服务和 Python API 服务。
4. **中优先级**：避免 `seed_data.py` 多次插入重复 demo 经验。

## 一句话结论

当前最大问题不是 C++ 服务、MySQL 或 UI，而是：

```text
CSV-Insight-Agent 为了使用经验记忆，直接导入了 Agent-Experience-Memory 的 Python Client，导致 report 环境需要安装 MySQL + sentence-transformers + torch 等依赖。
```

下一步应把 `Agent-Experience-Memory` 做成真正的 HTTP 记忆服务，让 `CSV-Insight-Agent` 只用轻量 HTTP 调用来获取经验上下文。
