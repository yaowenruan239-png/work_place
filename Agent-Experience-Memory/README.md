# Agent-Experience-Memory

Agent-Experience-Memory 是一个面向 AI Agent 的经验记忆检索系统。它记录 Agent 在工具调用、数据分析或任务执行过程中的错误，将可复用的问题模式沉淀为经验记忆，并在后续相似任务执行前召回相关经验，构造 prompt context 注入 Agent 上下文，从而减少重复错误和工具调用幻觉。

## Core Idea

```text
错误记录 → 经验沉淀 → 向量检索 → 执行前提醒 → 减少重复错误
```

核心闭环：

1. Agent 执行任务时发生错误。
2. Python 将错误、工具名、用户问题和上下文写入 MySQL。
3. 人工或后续自动流程将错误总结为通用经验。
4. Python 为经验生成 embedding，并将向量保存到 MySQL。
5. Python 将经验向量加载到 C++ 内存索引。
6. 新任务开始前，Python 生成 query embedding 并调用 C++ 服务检索相似经验。
7. Python 根据检索结果构造中文 prompt context，提醒 Agent 优先遵守历史经验。

## Features

当前 MVP 已实现：

- MySQL 持久化存储：
  - `agent_error_logs`
  - `experience_memories`
  - `memory_vectors`
- Python 编排层：
  - 数据库访问工具
  - 错误记录模块
  - 示例经验写入脚本
  - embedding 生成
  - C++ 索引加载脚本
  - 经验检索 Client
  - prompt context 构造
  - 端到端 demo
- C++ Memory Service：
  - 内存向量索引
  - cosine similarity
  - top-k 检索
  - HTTP API
- 项目文档：
  - API 文档
  - 设计说明
  - 架构说明
  - 有无经验记忆的对比 Demo

## Architecture

```text
              ┌──────────────────────┐
              │      AI Agent         │
              └──────────┬───────────┘
                         │
                         │ task / error / query
                         ▼
              ┌──────────────────────┐
              │    Python Client      │
              │                      │
              │ - record errors       │
              │ - DB read/write       │
              │ - embedding           │
              │ - index loading       │
              │ - search orchestration│
              │ - prompt context      │
              └───────┬────────┬─────┘
                      │        │
              SQL     │        │ HTTP
                      ▼        ▼
        ┌────────────────┐   ┌──────────────────────┐
        │     MySQL       │   │ C++ Memory Service   │
        │                │   │                      │
        │ error logs      │   │ in-memory vectors    │
        │ memories        │   │ cosine similarity    │
        │ vectors         │   │ top-k search         │
        └────────────────┘   └──────────────────────┘
```

职责边界：

- Python 负责业务编排、错误记录、embedding、索引加载、检索调用和 prompt context 构造。
- MySQL 负责长期持久化存储，是经验和错误日志的事实来源。
- C++ 服务负责轻量级内存向量检索，不直接连接 MySQL，不保存持久化数据。

## Project Structure

```text
Agent-Experience-Memory/
├── README.md
├── docker-compose.yml
├── requirements.txt
├── docs/
│   ├── api.md
│   ├── architecture.md
│   └── design.md
├── examples/
│   ├── demo_with_memory.md
│   └── demo_without_memory.md
├── mysql/
│   └── schema.sql
├── python_client/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── demo_record_error.py
│   ├── demo_search.py
│   ├── embedding.py
│   ├── error_collector.py
│   ├── experience_store.py
│   ├── load_cpp_index.py
│   ├── memory_client.py
│   └── seed_data.py
└── cpp_memory_service/
    ├── CMakeLists.txt
    ├── include/
    │   └── vector_index.h
    └── src/
        ├── main.cpp
        └── vector_index.cpp
```

## Quick Start

### 1. Start MySQL

```bash
docker compose up -d
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Verify MySQL connection

```bash
python -c "from python_client.db import fetch_all; print(fetch_all('SELECT 1 AS ok'))"
```

Expected output:

```text
[{'ok': 1}]
```

### 4. Seed experience memories

```bash
python -m python_client.seed_data
```

### 5. Build and start C++ Memory Service

```bash
cd cpp_memory_service
mkdir -p build
cd build
cmake ..
cmake --build .
./agent_memory_service
```

The service listens on:

```text
0.0.0.0:8080
```

Health check:

```bash
curl --noproxy "*" http://127.0.0.1:8080/health
```

Expected output:

```json
{"index_size":0,"status":"ok"}
```

If your terminal has proxy variables such as `HTTP_PROXY` or `HTTPS_PROXY`, use `--noproxy "*"` for curl, or set:

```bash
export NO_PROXY="127.0.0.1,localhost"
export no_proxy="127.0.0.1,localhost"
```

### 6. Load MySQL vectors into C++ index

Run in another terminal from the project root:

```bash
NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" python -m python_client.load_cpp_index
```

Expected output:

```text
loaded 10 memories into C++ index
```

### 7. Run search demo

```bash
NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" python -m python_client.demo_search
```

The demo prints retrieved memories and a Chinese prompt context.

## Demo

### Record an error

Run:

```bash
python -m python_client.demo_record_error
```

This demo intentionally raises:

```text
ValueError: column sales_amount not found
```

Then it records the error into `agent_error_logs` with:

- `task_type`: `chart_generation`
- `user_query`: `帮我画销售额趋势图`
- `tool_name`: `plot_chart`
- `context.columns`: `date`, `amount`, `region`
- `context.dtypes`: field type information

Expected output:

```text
inserted error_log_id=1
```

### Search experience memories

Run:

```bash
python -m python_client.seed_data
NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" python -m python_client.load_cpp_index
NO_PROXY="127.0.0.1,localhost" no_proxy="127.0.0.1,localhost" python -m python_client.demo_search
```

Example output:

```text
Search Results
- memory_id=... score=... title=日期列需要先解析
  prompt_hint=涉及日期筛选、排序、分组或重采样时，先确认日期列已解析为 datetime 类型。

Prompt Context
以下是系统过去执行类似任务时总结出的经验，请优先遵守：
1. 涉及日期筛选、排序、分组或重采样时，先确认日期列已解析为 datetime 类型。（相关度：0.3877）
```

### Without memory vs with memory

See:

- `examples/demo_without_memory.md`
- `examples/demo_with_memory.md`

The comparison shows a typical chart-generation failure:

- Without memory: Agent guesses `sales_amount`, calls `plot_chart(x="date", y="sales_amount")`, and fails with `ColumnNotFound`.
- With memory: Agent retrieves “生成图表前必须检查字段名”, checks schema first, uses real field `amount`, and succeeds with `plot_chart(x="date", y="amount")`.

## C++ API

See `docs/api.md` for details.

Implemented endpoints:

- `GET /health`
- `POST /index/clear`
- `POST /index/add`
- `POST /index/search`

## Design Notes

See:

- `docs/design.md`
- `docs/architecture.md`

Key decisions:

- MySQL stores long-term memories because it is durable, queryable and easy to audit.
- C++ handles vector search because it is a dedicated low-overhead retrieval service.
- Redis is not required in the first version because the MVP does not need a cache layer.
- HNSW/FAISS are not required in the first version because brute-force cosine search is enough for small-scale validation.
- Redis can be added later for recent memory cache, hot prompt context cache or search-result cache.

## Roadmap

Planned next steps:

1. Add deduplication to `seed_data` to avoid repeated demo memories.
2. Add result deduplication in `ExperienceMemoryClient.search()` by title or prompt hint.
3. Add richer error-to-experience workflow.
4. Add evaluation cases for retrieval quality.
5. Add optional Redis cache for recent memories and prompt context.
6. Replace brute-force search with HNSW/FAISS when memory scale grows.
7. Add integration adapters for external Agent projects.

CSV-Insight-Agent integration is intentionally not included in this repository step. It should be implemented separately in the original project.
