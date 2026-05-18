# pyplasmod SDK 用户指南

| 元数据 | 值 |
|--------|-----|
| **文档编号** | pyplasmod-003 |
| **状态** | 当前版本适用 |
| **创建** | 2026-05-06 |
| **更新** | 2026-05-18 |
| **维护方** | [CodeSoul-co](https://github.com/CodeSoul-co) |
| **读者** | 使用 pyplasmod 集成 Plasmod 的应用开发者 |

> **首次使用**建议按顺序阅读：  
> 1. [README.md](../../README.md) — 安装、网关启动、5 分钟快速开始  
> 2. 本文 — 参数含义、推荐填法、可复制样例  
> 3. [docs/SDK.md](../SDK.md) — 架构与 API 全量索引  
>  
> 架构背景：[pyplasmod-001-http-sdk-design.md](pyplasmod-001-http-sdk-design.md)  
> Tier B 扩展 API：[pyplasmod-002-gateway-tier-b-shortcuts-design.md](pyplasmod-002-gateway-tier-b-shortcuts-design.md)

**服务端契约**：JSON 字段与路由以 [Plasmod HTTP API](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api) 为准；本文与当前 `pyplasmod` 代码保持一致。

---

## 1. 安装与运行前提

### 1.1 安装客户端

```bash
pip install pyplasmod
```

可选 LangChain 集成：

```bash
pip install pyplasmod[langchain]
```

从源码开发安装：

```bash
pip install -e ".[dev]"
make unittest
```

### 1.2 运行前提

| 要求 | 说明 |
|------|------|
| Python | 3.8 及以上 |
| Plasmod 网关 | 已启动且可从本机访问（默认 `http://127.0.0.1:8080`） |
| 网络 | `curl $PLASMOD_BASE_URL/healthz` 返回成功 |

网关**不在** pyplasmod 包内。启动方式（`make dev`、Docker Compose 等）见 [README.md — 启动 Plasmod 网关](../../README.md#启动-plasmod-网关)。

### 1.3 包内帮助

```python
from pyplasmod import plasmod_help, plasmod_topics

plasmod_help()           # 主题索引
plasmod_help("easy")     # EasyPlasmod 详细说明
plasmod_help("env")      # 环境变量
```

命令行：`python -m pyplasmod [topic]`。完整函数签名亦可使用 `help(EasyPlasmod)` 等内置帮助。

---

## 2. 环境变量

| 变量 | 作用 |
|------|------|
| `PLASMOD_BASE_URL` / `ANDB_BASE_URL` | HTTP 根地址；默认 `http://127.0.0.1:8080` |
| `PLASMOD_HTTP_TIMEOUT` / `ANDB_HTTP_TIMEOUT` | 超时（秒）；默认 `30` |
| `PLASMOD_ADMIN_API_KEY` / `ANDB_ADMIN_API_KEY` | 访问 `/v1/admin/*` 时设置请求头 `X-Admin-Key` |

构造客户端时传入的 `base_url`、`timeout`、`admin_key` **优先于**环境变量。  
可将仓库 [`.env.example`](../../.env.example) 复制为 `.env` 供本地工具加载（pyplasmod 本身通过 `os.environ` 读取，不强制依赖 dotenv）。

---

## 3. 选择客户端入口

| 入口 | 适用场景 |
|------|----------|
| **`EasyPlasmod`** | 健康检查、文本检索、`ingest_document`、`.fbin` 上传、`memories` |
| **`PlasmodClient`**（= `PlasmodHttpClient`） | Admin、二进制 RPC、`ingest_vectors`、Tier B internal、WAL SSE |
| **`pyplasmod.data`** | `build_query_body`、`upload`（可传入 `client=` 复用连接） |
| **`PlasmodVectorStore`** | LangChain（需 optional extra） |

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
    p.health()
    p.http.dataset_delete({...})  # 完整能力经 .http 访问
```

### 3.1 核心概念

| 概念 | 说明 |
|------|------|
| `workspace_id` | 工作区隔离键，入库与查询通常必填（如 `w_demo`） |
| `dataset_name` | 逻辑数据集名；与 `upload(..., dataset=...)` 对应 |
| `session_id` / `agent_id` | 会话与智能体；**查询须与入库一致** |
| Memory | 网关物化后的记忆；`p.memories(workspace_id)` 列举 |

---

## 4. 数据入库

### 4.1 长文本与文档 — `ingest_document`

网关将 `text` **自动分块**为多条 memory 事件，客户端无需自行切句。

**必填 / 强烈建议字段**

| 字段 | 说明 |
|------|------|
| `text` | 正文（必填） |
| `workspace_id` | 工作区 |
| `agent_id` | 智能体 ID |
| `session_id` | 会话 ID（查询时沿用） |
| `title` | 文档标题（建议） |

**可选**：`chunk_size`、`overlap`、`importance` 等（语义以网关为准）。

```python
from pyplasmod import EasyPlasmod
from pyplasmod.data import build_query_body

workspace = "w_demo"
session_id = "doc_session_001"
agent_id = "pyplasmod_data"

with EasyPlasmod() as p:
    print(
        p.ingest_document(
            {
                "text": "需要入库的正文内容。",
                "workspace_id": workspace,
                "agent_id": agent_id,
                "session_id": session_id,
                "title": "示例文档",
                "chunk_size": 500,
                "overlap": 50,
            }
        )
    )
    print(
        p.query(
            build_query_body(
                "文档主题是什么？",
                workspace,
                session_id=session_id,
                agent_id=agent_id,
                top_k=5,
            )
        )
    )
```

**从文件读取**：

```python
from pathlib import Path

text = Path("/path/to/manual.md").read_text(encoding="utf-8")
# 将 text 填入 ingest_document 的 "text" 字段，title 可用 path.name
```

### 4.2 单条短文本 — `ingest_event`

适用于单条结构化事件、自定义 `payload`、或需附带 `embedding_vector` 的场景。

```python
with EasyPlasmod() as p:
    p.ingest_event(
        {
            "event_id": "evt_unique_001",
            "workspace_id": "w_demo",
            "agent_id": "pyplasmod_data",
            "session_id": "notes_session",
            "event_type": "observation",
            "payload": {"text": "一条备注"},
            "source": "my_application",
            "version": 1,
        }
    )
```

多条事件可循环调用，或使用 `p.http.ingest_events(events, batch_size=...)`。

### 4.3 向量文件 — `upload` / `upload_fbin`

`.fbin` 格式：8 字节头（`uint32` 行数 + `uint32` 维度）+ 按行的 little-endian `float32`。

```python
from pyplasmod import EasyPlasmod
from pyplasmod.data import upload

with EasyPlasmod() as p:
    n = upload(
        "my_dataset",
        "w_demo",
        "/path/to/vectors.fbin",
        client=p.http,
        show_progress=True,
    )
    print("ingested rows:", n)
```

命令行：

```bash
python -m pyplasmod.data upload my_dataset w_demo /path/to/vectors.fbin --show-progress
```

### 4.4 JSON 向量与二进制批量

| 方法 | 适用 |
|------|------|
| `client.ingest_vectors([[...], ...])` | 中等规模 JSON 矩阵 |
| `client.ingest_batch(segment_id, vectors, batch_size=500)` | 大规模；内部 RPC PLIB 自动分片 |
| `client.rpc_ingest_batch(...)` | 低级 RPC，自行控制批次 |

向量维度须与网关 warm 段 / 嵌入配置一致。

### 4.5 网关嵌入与 CPU / GPU — `PlasmodEmbedding`

Plasmod **没有** `/v1/embed`；纯文本在服务端由 ONNX / GGUF / TF-IDF 等生成向量。推荐入口：

```python
from pyplasmod import PlasmodEmbedding, EasyPlasmod

# 独立门面
with PlasmodEmbedding.connect() as emb:
    print(emb.capabilities())
    emb.ingest("入库文本", workspace_id="w_demo")
    print(emb.search("检索词", workspace_id="w_demo", top_k=5))
    print(emb.runtime())

# 或挂在 EasyPlasmod 上
with EasyPlasmod() as p:
    p.embed_ingest("入库文本", workspace_id="w_demo")
    print(p.embed_search("检索词", workspace_id="w_demo"))
```

**启动 Plasmod 前** 配置 CPU 或 GPU（写入 `PLASMOD_EMBEDDER*`）：

```python
emb = PlasmodEmbedding.connect()
emb.use_onnx_cpu(model_path="/models/model.onnx", dim=384, apply=True)
# emb.use_onnx_gpu(model_path="/models/model.onnx", dim=384, apply=True)
```

详见 **[docs/EMBEDDING.md](../EMBEDDING.md)** 与 [SDK.md §8](../SDK.md#8-网关嵌入pyplasmodembedding)。

---

## 5. 查询与检索

### 5.1 简易检索 — `search`

```python
with EasyPlasmod() as p:
    r = p.search("示例问题", "w_demo", top_k=10)
```

内部调用 `build_query_body` 后 `POST /v1/query`。

### 5.2 显式请求体 — `build_query_body` + `query`

| 参数 | 说明 |
|------|------|
| `query_text` | 查询字符串 |
| `embedding_vector` | 可选；传入则跳过网关 embedder |
| `workspace_id` | 工作区；同时写入 `query_scope` |
| `session_id` | 为空时：若同时提供 `dataset_name` 与 `ingest_fbin_path` → `ingest_{dataset}_{文件名}`；否则 `query_{workspace_id}` |
| `agent_id` | 默认 `pyplasmod_data`；须与入库一致 |
| `dataset_name` | 按数据集过滤 |
| `ingest_fbin_path` | 仅用于推导默认 `session_id` |
| `extra` | 合并覆盖任意字段 |

```python
from pyplasmod.data import build_query_body

body = build_query_body(
    "hello",
    "w_demo",
    top_k=5,
    dataset_name="my_dataset",
    ingest_fbin_path="/path/to/vectors.fbin",
)
```

响应结构因服务端版本而异，常见键包括 `objects`、`hits` 等。

### 5.3 列举 Memory

```python
rows = p.memories("w_demo", limit=100)
```

等价于 `GET /v1/memory` 并自动带上 `workspace_id` 查询参数。

---

## 6. `PlasmodHttpClient` 参考

### 6.1 构造

```python
from pyplasmod import PlasmodHttpClient, PlasmodHttpError

client = PlasmodHttpClient(
    base_url=None,      # 默认读环境变量 → http://127.0.0.1:8080
    timeout=None,
    admin_key=None,
    session=None,       # 可选复用 requests.Session
)

with PlasmodHttpClient() as c:
    ...
```

### 6.2 通用方法

| 方法 | 说明 |
|------|------|
| `request_json(method, path, *, json_body=..., params=..., headers=...)` | 任意 JSON API |
| `request_bytes(method, path, *, data=..., headers=...)` | 二进制 body；返回 `(status, bytes, headers)` |

### 6.3 Tier A 常用 JSON 快捷方法

| 方法 | HTTP |
|------|------|
| `health()` | `GET /healthz` |
| `system_mode()` | `GET /v1/system/mode` |
| `ingest_event(event)` | `POST /v1/ingest/events` |
| `ingest_vectors(vectors, *, segment_id=..., object_ids=...)` | `POST /v1/ingest/vectors` |
| `ingest_document(body)` | `POST /v1/ingest/document` |
| `query(body)` | `POST /v1/query` |
| `query_batch(body)` | `POST /v1/query/batch` |
| `memory_get(params)` / `memory_post(body)` | `GET/POST /v1/memory` |
| `dataset_delete(body)` | `POST /v1/admin/dataset/delete` |
| `dataset_purge(body)` | `POST /v1/admin/dataset/purge` |
| `dataset_purge_task(task_id)` | `GET /v1/admin/dataset/purge/task` |
| `warm_prebuild()` | `POST /v1/admin/warm/prebuild` |
| `warm_segment_register(body)` | `POST /v1/internal/warm-segment/register` |

### 6.4 二进制 RPC

| 方法 | 说明 |
|------|------|
| `rpc_ingest_batch(segment_id, vectors, object_ids=None, wire_version=1\|2)` | PLIB 批量入库 |
| `rpc_query_warm(segment_id, top_k, vector)` | PLQW 单向量检索 |
| `rpc_query_warm_batch` / `rpc_query_warm_batch_raw` | PLQB 批量检索 |
| `rpc_unload_segment` / `rpc_register_warm` | 段卸载 / 注册 |

非 200 响应抛出 `PlasmodHttpError`。一般优先使用 `rpc_*`，无需手动调用 `encode_*`。

### 6.5 Canonical CRUD 与 internal memory

- CRUD：`agents_get/post`、`sessions_get/post`、`states_get/post`、`artifacts_get/post`、`edges_get/post`、`policies_get/post`、`share_contracts_get/post`
- 追踪：`traces_get(object_id)`
- 算法桥：`internal_memory_recall`、`internal_memory_ingest` 等（路径 `/v1/internal/memory/*`，**不同于** `/v1/memory` CRUD）

### 6.6 Tier B

Admin 扩展、internal task/MAS、`agent_list_get`、`internal_session_context_get`、`debug_echo` 等见 [pyplasmod-002](pyplasmod-002-gateway-tier-b-shortcuts-design.md) §4。

**数据集 purge 示例**（先 `dry_run`）：

```python
p.http.dataset_purge(
    {"workspace_id": "w_demo", "dataset_name": "my_dataset", "dry_run": True}
)
```

---

## 7. `EasyPlasmod` 方法一览

| 方法 | 行为 |
|------|------|
| `health()` / `system_mode()` | 同 `http.*` |
| `query(body)` | `POST /v1/query` |
| `search(query_text, workspace_id, **kwargs)` | `build_query_body` + `query` |
| `ingest_event` / `ingest_document` | 同 `http.*` |
| `upload_fbin(dataset, workspace_id, path, **kwargs)` | `data.upload(..., client=self.http)` |
| `memories(workspace_id, **params)` | `GET /v1/memory` |
| `http` | 完整 `PlasmodHttpClient` |

---

## 8. 错误处理与排错

### 8.1 捕获 HTTP 错误

```python
from pyplasmod import PlasmodClient, PlasmodHttpError

try:
    PlasmodClient().query({"query_text": "x", "workspace_id": "w_demo"})
except PlasmodHttpError as e:
    print(e.status_code, e.path, (e.body or "")[:500])
```

| 属性 | 含义 |
|------|------|
| `status_code` | HTTP 状态；连接失败时常为 `0` |
| `path` | 请求路径 |
| `body` | 响应体文本 |

### 8.2 常见问题

| 现象 | 可能原因 | 建议 |
|------|----------|------|
| `status_code=0`、连接错误 | 网关未启动或 URL/端口错误 | 检查 `PLASMOD_BASE_URL`、`curl .../healthz` |
| 401/403 on `/v1/admin/*` | 未配置 Admin Key | 设置 `PLASMOD_ADMIN_API_KEY` 或 `admin_key=` |
| 查询无命中 | `session_id`/`agent_id` 与入库不一致 | 对齐 ingest 与 `build_query_body` 参数 |
| 向量入库失败 | 维度与网关不匹配 | 确认 `.fbin` dim 与 embedder 配置 |
| `ingest_document` 后查不到 | 未传相同 `session_id` | 查询 body 显式带上入库时的 session |
| RPC warm 失败 | 段未注册或维度错误 | 检查 `warm_segment_register` 与 `segment_id` |

---

## 9. 示例与延伸阅读

| 资源 | 说明 |
|------|------|
| [README.md](../../README.md) | 快速开始、分场景示例 |
| [docs/SDK.md](../SDK.md) | 架构、实现细节、API 索引 |
| `examples/http_quickstart.py` | 最小 HTTP 示例 |
| `examples/ingest_fbin.py` | `.fbin` 入库 |
| `examples/batch_ingest.py` | 批量向量 |
| `examples/langchain_quickstart.py` | LangChain |
| `examples/test.py` | 综合联调（ingest、query、admin、Tier B） |
| [Plasmod docs/api](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api) | 服务端权威 API |

---

## 10. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-05-06 | 首版：参数、Tier A/B、EasyPlasmod、data、错误处理 |
| 2026-05-18 | 对外规范化：对齐 README 入库分节、网关前提、排错表、文档交叉引用 |
