# Design

## 项目目标

Agent-Experience-Memory 的目标是为 AI Agent 提供一个可复用的经验记忆检索系统。系统记录 Agent 在工具调用、数据分析和任务执行中的错误，将其中具有通用价值的问题总结为经验记忆，并在后续相似任务执行前召回这些经验，作为 prompt hint 注入 Agent 上下文。

核心目标不是替代 Agent 的推理能力，而是在任务开始前提供高相关的历史经验提醒，降低重复犯错概率。

## MVP 范围

MVP 只实现一个单机、最小可运行闭环：

- MySQL 持久化错误日志、经验记忆和经验向量。
- Python 负责数据库读写、embedding 生成、索引加载、检索调用和 prompt context 构造。
- C++ 负责轻量级内存向量索引和暴力 cosine similarity top-k 检索。
- Python 通过 HTTP 将 MySQL 中的向量加载到 C++ 服务。
- Python 通过 HTTP 调用 C++ 服务完成检索。

## 明确不做的内容

第一版不实现：

- Redis
- HNSW
- FAISS
- Milvus
- 分布式部署
- 权限系统
- 前端管理后台
- C++ 服务直连 MySQL
- 自动从错误日志生成经验总结的 LLM pipeline

Redis 可以在后续版本中用于缓存热点经验、prompt context 或检索结果；HNSW、FAISS、Milvus 可以在向量规模变大后替换暴力检索。

## 设计取舍

### 为什么 MySQL 存长期经验

长期经验需要具备可审计、可维护和可恢复的特性。MySQL 适合保存结构化的错误日志、经验正文、命中次数、创建时间和更新时间等元数据。

选择 MySQL 的原因：

- 可靠持久化，服务重启后数据不会丢失。
- 便于通过 SQL 查询、筛选和人工审核经验。
- 适合保存错误上下文、经验正文和向量 JSON 等结构化数据。
- 易于与现有业务系统集成。

在本项目中，MySQL 是唯一长期事实来源；C++ 服务只保存可重建的内存索引。

### 为什么 C++ 做向量检索

向量检索是高频路径，适合放在独立服务中。第一版使用 C++ 实现内存索引，主要是为了验证“Python 编排 + C++ 检索服务”的边界。

选择 C++ 的原因：

- 内存数组和数值计算开销低。
- 服务职责单一，只处理向量加载和 top-k 检索。
- 后续可以平滑替换为更高性能的索引结构。
- Python 侧保持业务编排简单，不承担检索服务生命周期。

MVP 中 C++ 使用暴力 cosine similarity，优先保证实现简单和结果可解释。

### 为什么第一版不用 Redis

Redis 更适合缓存短期、高频、可丢失的数据，例如热点经验、近期 prompt context 或检索结果。第一版的核心目标是跑通错误记录、经验沉淀、向量检索和执行前提醒的闭环，不需要额外引入缓存层。

第一版不用 Redis 的原因：

- 系统规模小，MySQL + C++ 内存索引已足够。
- 缓存一致性会增加实现复杂度。
- prompt context 可以按需实时构造。
- 热点经验和近期记忆策略尚未稳定，过早缓存会增加调试成本。

Redis 会作为后续优化，而不是 MVP 的基础依赖。

### 为什么第一版不用 HNSW/FAISS

HNSW 和 FAISS 适合大规模向量检索，但第一版经验数量较少，暴力检索已经足够。

第一版不用 HNSW/FAISS 的原因：

- 暴力 cosine similarity 对小规模数据更简单、可解释、易调试。
- HNSW/FAISS 会引入额外构建、持久化和参数调优成本。
- 当前更重要的是验证数据链路和 Agent 行为改进，而不是极限检索性能。
- 后续当经验数量增长到暴力检索无法满足延迟要求时，再替换索引层。

C++ 服务的 HTTP API 已经把检索能力封装起来，未来替换内部索引实现时，Python 调用方可以基本保持不变。

### 后续如何扩展 Redis 近期记忆缓存

后续可以引入 Redis 作为近期记忆和热点结果缓存层。

可扩展方向：

1. 缓存近期任务的 prompt context。
2. 缓存高频 query 的检索结果。
3. 保存短期 session memory，例如某个 run_id 下最近发生的错误和工具调用摘要。
4. 对高命中经验做热度缓存，减少 MySQL 回表次数。
5. 使用 TTL 控制近期记忆自动过期，避免长期污染经验库。

扩展后的典型链路：

```text
query
  │
  ├── check Redis prompt context cache
  │       └── hit: return cached context
  │
  └── miss: embedding -> C++ search -> MySQL memories -> build context -> write Redis
```

Redis 只缓存可重建数据，长期经验仍以 MySQL 为准。

## 数据模型草案

### `agent_error_logs`

用于保存 Agent 执行过程中的原始错误。

建议字段：

- `id`：主键
- `task_type`：任务类型，例如 `tool_call`、`data_analysis`、`sql_generation`
- `task_input`：任务输入或用户目标
- `tool_name`：发生错误的工具名，可为空
- `error_type`：错误类别
- `error_message`：错误信息
- `context`：错误上下文 JSON
- `created_at`：创建时间

### `experience_memories`

用于保存从错误中提炼出的通用经验。

建议字段：

- `id`：主键
- `title`：经验标题
- `content`：经验正文
- `scope`：适用范围，例如 `mysql`、`python_tool`、`data_analysis`
- `source_error_log_id`：来源错误日志 ID，可为空
- `severity`：经验重要程度
- `created_at`：创建时间
- `updated_at`：更新时间

### `memory_vectors`

用于保存经验记忆的向量。

建议字段：

- `id`：主键
- `memory_id`：关联 `experience_memories.id`
- `embedding_model`：embedding 模型名
- `dimension`：向量维度
- `vector_json`：向量 JSON 数组
- `created_at`：创建时间

MVP 中优先使用 JSON 存储向量，便于实现和调试。后续如性能不足，可再考虑二进制存储或专用向量数据库。

## 核心流程

### 1. 错误日志记录

Agent 执行任务失败后，Python 将错误信息写入 `agent_error_logs`。

流程：

1. 接收任务输入、工具名、错误类型、错误消息和上下文。
2. 写入 MySQL。
3. 返回错误日志 ID，供后续人工或自动总结经验时引用。

### 2. 经验记忆写入

从错误日志中提炼通用经验后，Python 写入 `experience_memories`。

流程：

1. 写入经验标题、经验正文、适用范围和来源错误日志 ID。
2. 对经验文本生成 embedding。
3. 将向量写入 `memory_vectors`。

### 3. C++ 索引加载

C++ 服务不访问 MySQL。Python 负责读取 MySQL 中的向量并加载到 C++ 服务。

流程：

1. Python 调用 `/index/clear` 清空 C++ 内存索引。
2. Python 从 MySQL 查询经验及其向量。
3. Python 将每条向量通过 `/index/add` POST 到 C++ 服务。
4. C++ 服务保存在内存数组中。

### 4. 相似经验检索

Agent 执行任务前，Python 生成任务 embedding，并向 C++ 服务查询 top-k。

流程：

1. 输入任务描述。
2. Python 生成 query embedding。
3. Python 调用 `/index/search`。
4. C++ 返回 memory ID、score 和 metadata。
5. Python 根据 memory ID 查询 MySQL 中的经验正文。
6. Python 构造 prompt context。

### 5. Prompt Context 构造

Prompt context 只包含与当前任务最相关的经验，避免注入过多无关内容。

示例格式：

```text
Relevant experience memories:
1. [score=0.91] 调用工具前先确认参数 schema，避免编造不存在的字段。
2. [score=0.84] 执行 SQL 前先确认表名和字段名，避免基于假设生成查询。
```

## 检索策略

MVP 使用暴力 cosine similarity：

1. 遍历内存中的所有向量。
2. 计算 query 向量与 memory 向量的 cosine similarity。
3. 按分数降序排序。
4. 返回 top-k。

该方案适合小规模原型，优点是实现简单、可解释、无额外索引依赖。

## Embedding 策略

MVP 可以先使用本地确定性 embedding 实现，保证项目独立运行，不依赖外部 API。后续可替换为 OpenAI、BGE、E5 或其他 embedding 模型。

无论使用哪种实现，Python 对外提供统一接口：

- 输入：文本
- 输出：固定维度 float 向量

## 成功标准

MVP 成功标准：

1. MySQL 能启动并初始化三张核心表。
2. Python 能插入示例经验和向量。
3. C++ 服务能启动并响应健康检查。
4. Python 能把 MySQL 中的向量加载到 C++ 内存索引。
5. Python 能输入一个任务描述并召回相关经验。
6. Python 能输出可注入 Agent 上下文的 prompt hint。
