# work_place

这个仓库包含两个相互配合的 AI Agent 项目：

- `CSV-Insight-Agent-master`：面向 CSV 文件的数据分析 Agent，支持数据画像、图表生成、洞察总结和报告导出。
- `Agent-Experience-Memory`：面向 AI Agent 的经验记忆检索系统，用于记录工具调用错误、沉淀经验，并在后续任务执行前召回相似经验注入 Prompt。

二者组合后，可以让 CSV 分析 Agent 在执行前参考历史错误经验，减少字段名幻觉、工具参数错误和重复失败调用。

## 项目结构

```text
work_place/
├── Agent-Experience-Memory/      # 经验记忆检索系统
├── CSV-Insight-Agent-master/     # CSV 数据分析 Agent
├── env_win.yml                   # 环境导出文件
├── pip_req.txt                   # Python 依赖导出文件
└── README.md                     # 当前总览文档
```

## 1. Agent-Experience-Memory

`Agent-Experience-Memory` 是一个面向 AI Agent 的经验记忆引擎，核心流程是：

```text
错误记录 -> 经验沉淀 -> 向量检索 -> Prompt 注入 -> 减少重复错误
```

主要能力：

- 使用 MySQL 持久化存储错误日志、经验记忆和向量数据。
- 使用 Python Client SDK 记录错误、生成 embedding、加载索引、检索经验并构造 Prompt Context。
- 使用 C++ Memory Service 提供内存向量检索能力。
- 基于 cosine similarity 做 top-k 相似经验召回。
- 可被其他 Agent 项目以轻量方式集成。

相关文件：

```text
Agent-Experience-Memory/
├── python_client/                # Python Client SDK
├── cpp_memory_service/           # C++ 向量检索服务
├── mysql/schema.sql              # MySQL 表结构
├── docker-compose.yml            # MySQL 启动配置
├── start_experience_memory.sh    # 一键启动脚本
└── README.md                     # 子项目说明
```

### 启动经验记忆服务

第一次启动建议执行：

```bash
cd Agent-Experience-Memory
./start_experience_memory.sh --install-deps --seed
```

后续日常启动：

```bash
cd Agent-Experience-Memory
./start_experience_memory.sh
```

启动成功后检查：

```bash
curl --noproxy "*" http://127.0.0.1:8080/health
```

预期可以看到类似：

```json
{"index_size":10,"status":"ok"}
```

注意：`--seed` 会插入 demo 经验数据，当前种子脚本没有去重逻辑，不建议每次都加。

## 2. CSV-Insight-Agent-master

`CSV-Insight-Agent-master` 是一个 CSV 数据分析 Agent，支持多种执行模式：

- `quick_chart`：快速生成单张图表。
- `full_report`：生成多图表和完整报告。
- `planner_loop`：通过 JSON Planner Loop 调用白名单 Skill。
- `agent_loop`：通过 LangChain ReAct-style Agent Loop 自动调用工具。

主要能力：

- 自动读取 CSV 并生成数据画像。
- 根据字段和用户问题推荐图表。
- 使用 matplotlib 生成 PNG 图表。
- 生成中文洞察和 Markdown/PDF/HTML 报告。
- 使用文件型 `MemoryStore` 保存最近任务、用户偏好和图表偏好。
- 可选接入 `Agent-Experience-Memory` 做经验记忆增强。

相关文件：

```text
CSV-Insight-Agent-master/
├── src/agent/                    # LangChain Agent Loop 和工具封装
├── src/skills/                   # profile、chart、insight、report 等 Skill
├── src/graph/                    # LangGraph 稳定工作流节点
├── src/memory/                   # 文件型 MemoryStore
├── src/experience_memory_adapter.py
├── examples/                     # 示例 CSV
├── outputs/                      # 图表和报告输出目录
├── app.py                        # Streamlit UI
├── main.py                       # CLI 入口
└── README.md                     # 子项目说明
```

### 启动 CSV 分析 Agent

安装依赖：

```bash
cd CSV-Insight-Agent-master
pip install -r requirements.txt
```

运行 CLI 示例：

```bash
python main.py examples/sales.csv "分析销售趋势并画图" --mode quick_chart
```

运行 LangChain Agent Loop：

```bash
python main.py examples/sales.csv "自动分析销售数据，选择图表并生成报告" --mode agent_loop
```

运行 Streamlit UI：

```bash
streamlit run app.py
```

## 3. 两个项目如何集成

`CSV-Insight-Agent-master` 中新增了：

```text
src/experience_memory_adapter.py
```

它会动态引用兄弟目录：

```text
../Agent-Experience-Memory
```

并使用其中的：

- `python_client.memory_client.ExperienceMemoryClient`
- `python_client.error_collector.record_error`

集成效果：

1. Agent 执行前，根据用户 query 和任务类型构造检索 query。
2. 调用 `Agent-Experience-Memory` 的 C++ 检索服务获取相似经验。
3. 使用 Python Client SDK 构造中文经验上下文。
4. 将经验记忆追加注入到 Agent Prompt / 用户输入中。
5. 工具调用抛异常时，记录工具名、错误信息、字段、参数和上下文到 MySQL。

服务不可用时不会影响 CSV Agent 主流程：

- 经验检索失败时返回空字符串。
- 错误记录失败时只打印 warning。
- 原有 `MemoryStore` 文件型记忆仍然照常工作。

详细集成说明见：

```text
CSV-Insight-Agent-master/docs/experience_memory_integration.md
```

## 4. 推荐体验流程

### Step 1：启动经验记忆服务

```bash
cd Agent-Experience-Memory
./start_experience_memory.sh --install-deps --seed
```

### Step 2：验证经验检索

```bash
cd Agent-Experience-Memory
NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" python -m python_client.demo_search
```

### Step 3：在 CSV Agent 中查看经验注入

```bash
cd CSV-Insight-Agent-master
NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" python - <<'PY'
from src.experience_memory_adapter import get_experience_context

print(get_experience_context(
    user_query="请分析每个月的销售金额趋势，并生成柱状图",
    task_type="csv_analysis",
))
PY
```

如果服务正常，会看到类似经验：

```text
以下是系统过去执行类似任务时总结出的经验，请优先遵守：
1. 生成图表前必须先检查实际字段名，不要基于用户自然语言描述编造列名。
```

### Step 4：运行集成后的 Agent

```bash
cd CSV-Insight-Agent-master
NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" \
python main.py examples/sales.csv "请分析每个月的销售金额趋势，并生成柱状图" --mode agent_loop
```

`sales.csv` 的真实字段是：

```text
月份,销售额,利润,客户数,产品类别,地区
```

这个案例可以观察 Agent 是否更倾向于根据实际字段 `销售额` 生成图表，而不是凭自然语言使用不存在的 `销售金额`。

### Step 5：验证 fallback

停掉 C++ Memory Service 后再运行同样命令，CSV Agent 应该仍能继续执行，只是不会注入经验记忆。

## 5. 技术栈

- Python
- LangChain / LangGraph
- pandas / numpy
- matplotlib / seaborn
- Streamlit
- MySQL
- C++17
- cpp-httplib
- nlohmann/json
- Docker Compose

## 6. 注意事项

- `Agent-Experience-Memory` 是可选增强服务，不启动时 `CSV-Insight-Agent-master` 仍可运行。
- 当前 C++ 检索服务是轻量内存向量索引，不是分布式系统，也不是工业级向量数据库。
- 当前检索方式是 cosine similarity top-k，没有实现 HNSW 或 FAISS。
- 当前项目没有使用 Redis。
- 不建议提交运行时输出、日志、C++ build 目录和本地环境文件。

