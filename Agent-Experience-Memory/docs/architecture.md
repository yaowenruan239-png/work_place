# Architecture

## 总体架构

Agent-Experience-Memory 由三部分组成：

1. Python Client
2. MySQL
3. C++ Memory Service

三者职责边界清晰：

- Python 负责业务编排和数据流转。
- MySQL 负责持久化存储。
- C++ 负责高频、轻量的内存向量检索。

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

## 模块职责

### Python Client

Python Client 是系统的控制层，负责连接各个组件。

主要职责：

- 写入 Agent 错误日志。
- 写入人工或自动总结后的经验记忆。
- 生成经验文本和查询文本的 embedding。
- 将经验向量写入 MySQL。
- 从 MySQL 读取经验向量。
- 调用 C++ 服务加载内存索引。
- 调用 C++ 服务检索相似经验。
- 根据检索结果查询经验正文。
- 构造可注入 Agent prompt 的上下文文本。

MVP 中 Python 后续计划包含以下脚本：

- `python -m python_client.seed_data`
- `python -m python_client.load_cpp_index`
- `python -m python_client.demo_search`

### MySQL

MySQL 是唯一持久化存储层。

负责保存：

- Agent 原始错误日志
- 经验记忆正文
- 经验向量

MySQL 不负责向量相似度检索，只负责可靠存储和查询。

### C++ Memory Service

C++ Memory Service 是独立 HTTP 服务，只维护内存中的向量索引。

主要职责：

- 接收 Python 发送的向量数据。
- 将向量保存在进程内存中。
- 对 query vector 执行暴力 cosine similarity 检索。
- 返回 top-k memory ID 和 score。

C++ 服务不直接连接 MySQL，不保存持久化数据。服务重启后，索引为空，需要 Python 重新加载。

## C++ HTTP API

### `GET /health`

用于健康检查。

响应示例：

```json
{
  "status": "ok"
}
```

### `POST /index/clear`

清空内存索引。

响应示例：

```json
{
  "cleared": true
}
```

### `POST /index/add`

添加一条 memory vector。

请求示例：

```json
{
  "memory_id": 1,
  "vector": [0.1, 0.2, 0.3],
  "metadata": {
    "title": "确认工具参数 schema"
  }
}
```

响应示例：

```json
{
  "added": true,
  "size": 1
}
```

### `POST /index/search`

搜索相似 memory。

请求示例：

```json
{
  "query_vector": [0.1, 0.2, 0.3],
  "top_k": 3
}
```

响应示例：

```json
{
  "results": [
    {
      "memory_id": 1,
      "score": 0.93,
      "metadata": {
        "title": "确认工具参数 schema"
      }
    }
  ]
}
```

## 数据流

### 数据写入链路

```text
Agent error
    │
    ▼
Python Client
    │
    ├── write agent_error_logs
    │
    ├── write experience_memories
    │
    └── generate embedding and write memory_vectors
             │
             ▼
           MySQL
```

### 索引加载链路

```text
Python Client
    │
    ├── read memory_vectors from MySQL
    │
    ├── POST /index/clear
    │
    └── POST /index/add for each vector
             │
             ▼
    C++ Memory Service
```

### 检索链路

```text
Task description
    │
    ▼
Python Client
    │
    ├── generate query embedding
    ├── POST /index/search
    │        │
    │        ▼
    │   C++ Memory Service
    │        │
    │        ▼
    │   top-k memory IDs
    │
    ├── read experience_memories from MySQL
    │
    ▼
Prompt context
```

## 部署与运行边界

MVP 的运行方式是本地单机多进程：

- MySQL 通过 Docker Compose 启动。
- C++ Memory Service 作为本地 HTTP 服务启动。
- Python 脚本在本地运行，负责初始化数据、加载索引和执行检索 demo。

## 配置边界

后续实现时建议通过环境变量配置：

- MySQL host
- MySQL port
- MySQL user
- MySQL password
- MySQL database
- C++ service URL
- embedding dimension

MVP 可提供默认值，降低本地运行成本。

## 故障边界

### C++ 服务重启

C++ 服务只保存内存索引，重启后索引丢失。需要重新执行：

```bash
python -m python_client.load_cpp_index
```

### MySQL 数据保留

经验记忆和向量保存在 MySQL 中，只要 MySQL volume 不删除，数据可以保留。

### 向量维度不一致

C++ 服务在添加和搜索时应校验向量维度。若维度不一致，应返回错误，避免计算结果无意义。

## 后续可演进方向

MVP 之后可以考虑：

- Redis 缓存热点经验或 prompt context。
- 使用 HNSW、FAISS 或 Milvus 提升大规模向量检索性能。
- 增加经验记忆质量评分和过期机制。
- 增加基于 LLM 的错误自动总结 pipeline。
- 增加管理后台用于浏览、编辑和审核经验记忆。
- 增加多租户和权限系统。
- 增加检索评估集和召回质量指标。
