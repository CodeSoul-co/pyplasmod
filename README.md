# pyplasmod

面向 **[Plasmod](https://github.com/CodeSoul-co/Plasmod)** 的 **Python HTTP SDK**：实现服务端在 **`docs/sdk/README.md`** 中定义的 **Tier A JSON** 路由，以及 **`/v1/internal/rpc/*`** 的二进制帧编码/解码（PLIB / PLQW / PLQB）。

**Plasmod 是什么**  
Plasmod 面向多智能体系统，将认知对象存储、事件驱动的物化与结构化证据检索整合在可运行的系统中。

## 安装

需要 Python 3.8+。

```bash
pip install pyplasmod
```

LangChain 集成（可选）：

```bash
pip install pyplasmod[langchain]
```

开发：

```bash
pip install -e ".[dev]"
make unittest
```

## 契约与文档

- 路由与字段映射：<https://github.com/CodeSoul-co/Plasmod/blob/main/docs/sdk/README.md>
- 服务端 OpenAPI 子集与同文档附录 YAML 对齐。
- Milvus 迁移指南：[docs/integrations/milvus_plasmod_mapping.md](docs/integrations/milvus_plasmod_mapping.md)

## 快速用法

```python
from pyplasmod import PlasmodClient

client = PlasmodClient(base_url="http://127.0.0.1:8080")
client.health()
client.ingest_event({"event_id": "e1", "agent_id": "a", "session_id": "s", "event_type": "t", "payload": {}})
client.query({"query_text": "hello", "top_k": 5, "relation_constraints": []})
```

## 批量写入

SDK 支持自动分批写入，避免一次性构造大请求体导致内存问题：

```python
from pyplasmod import PlasmodClient

client = PlasmodClient(base_url="http://127.0.0.1:8080")

# 批量写入向量（自动分批，默认 batch_size=500）
vectors = [[0.1, 0.2, ...] for _ in range(10000)]
result = client.ingest_batch(
    segment_id="warm.default",
    vectors=vectors,
    batch_size=500,  # 可选，默认 500
)
print(f"写入 {result.accepted_count} 条，共 {result.batch_count} 批")

# 批量写入事件
events = [{"event_id": f"e{i}", "event_type": "test", "payload": {}} for i in range(1000)]
result = client.ingest_events(events, batch_size=100)
```

详见 `examples/batch_ingest.py`。

## LangChain 集成

pyplasmod 提供 LangChain VectorStore 适配器：

```python
from langchain_openai import OpenAIEmbeddings
from pyplasmod import PlasmodClient
from pyplasmod.langchain import PlasmodVectorStore

client = PlasmodClient(base_url="http://127.0.0.1:8080")
embeddings = OpenAIEmbeddings()

vectorstore = PlasmodVectorStore(
    client=client,
    embedding=embeddings,
    batch_size=500,
)

# 添加文档（自动分批）
vectorstore.add_texts(["Hello world", "Goodbye world"])

# 相似度搜索
docs = vectorstore.similarity_search("Hello", k=5)

# 作为 Retriever 使用
retriever = vectorstore.as_retriever()
```

详见 `examples/langchain_quickstart.py`。

## 管理接口

管理接口（`/v1/admin/*`）在设置了环境变量 **`PLASMOD_ADMIN_API_KEY`** 或 **`ANDB_ADMIN_API_KEY`**（或构造参数 **`admin_key`**）时自动附加 **`X-Admin-Key`**。

## 二进制 RPC

二进制 RPC 与帧工具可从子模块导入：

```python
from pyplasmod.http import encode_ingest_batch, PlasmodHttpClient
```

## 异常

- **`PlasmodHttpError`**：HTTP 非成功响应（含 **`status_code`**、**`body`**、**`path`**）。
- **`ConnectError`**：连接级失败（由客户端在收到响应前抛出）。
- **`PlasmodException`**：其它 SDK 基类。

## 许可证

Apache 2.0（见仓库根目录 `LICENSE`）。
