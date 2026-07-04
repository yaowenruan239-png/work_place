# C++ Memory Service API

C++ Memory Service 是一个本地 HTTP 服务，负责维护内存向量索引并执行 cosine similarity top-k 检索。

默认监听地址：

```text
http://127.0.0.1:8080
```

## GET `/health`

健康检查接口。

### 请求

```bash
curl --noproxy "*" http://127.0.0.1:8080/health
```

### 响应示例

```json
{
  "status": "ok",
  "index_size": 10
}
```

字段说明：

- `status`：服务状态。
- `index_size`：当前内存索引中的向量数量。

## POST `/index/clear`

清空内存索引。

### 请求

```bash
curl --noproxy "*" -X POST http://127.0.0.1:8080/index/clear
```

### 响应示例

```json
{
  "ok": true,
  "index_size": 0
}
```

## POST `/index/add`

添加一条 memory vector 到内存索引。

### 请求体

```json
{
  "memory_id": 1,
  "vector": [0.1, 0.2, 0.3]
}
```

字段说明：

- `memory_id`：MySQL 中 `experience_memories.id`。
- `vector`：经验记忆的 embedding 向量。

### 请求示例

```bash
curl --noproxy "*" -X POST http://127.0.0.1:8080/index/add \
  -H "Content-Type: application/json" \
  -d '{"memory_id":1,"vector":[0.1,0.2,0.3]}'
```

### 响应示例

```json
{
  "ok": true,
  "memory_id": 1,
  "index_size": 1
}
```

## POST `/index/search`

根据 query vector 检索相似经验。

### 请求体

```json
{
  "vector": [0.1, 0.2, 0.3],
  "top_k": 3
}
```

字段说明：

- `vector`：查询文本的 embedding 向量。
- `top_k`：返回的最大结果数量。

### 请求示例

```bash
curl --noproxy "*" -X POST http://127.0.0.1:8080/index/search \
  -H "Content-Type: application/json" \
  -d '{"vector":[0.1,0.2,0.3],"top_k":3}'
```

### 响应示例

```json
{
  "ok": true,
  "results": [
    {
      "memory_id": 1,
      "score": 0.98
    }
  ]
}
```

## 错误响应

当请求 JSON 非法、字段缺失或字段类型错误时，服务返回错误响应。

示例：

```json
{
  "ok": false,
  "error": "missing field: vector"
}
```
