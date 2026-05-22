# pyplasmod

> **English** | [README.md](README.md)

**pyplasmod** 是面向 **[Plasmod](https://github.com/CodeSoul-co/Plasmod)** 的 Python **HTTP 客户端库**：通过标准 HTTP（及部分二进制 RPC）访问已部署的 Plasmod 网关，完成向量入库、检索、Memory 列举、数据集运维与健康检查等操作。

**Plasmod** 面向多智能体场景，将认知对象存储、事件驱动的物化与结构化证据检索集成在可运行系统中。  
请求路径、字段与语义以 Plasmod 官方 **[HTTP API 文档](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api)** 为准；本 README 仅说明本仓库提供的封装与典型用法。

包内主题索引：`from pyplasmod import plasmod_help; plasmod_help()`；命令行：`python -m pyplasmod [topic]`。  
SDK 架构与实现细节见 **[docs/zh-CN/SDK.md](docs/zh-CN/SDK.md)**；网关嵌入（CPU/GPU）见 **[docs/zh-CN/EMBEDDING.md](docs/zh-CN/EMBEDDING.md)**。

---

## 快速开始（约 5 分钟）

下列步骤假设你在本机已能访问 Plasmod 网关（默认 `http://127.0.0.1:8080`）。若尚未启动网关，请先阅读下一节 **[启动 Plasmod 网关](#启动-plasmod-网关)**。

| 步骤 | 做什么 | 命令 / 代码 |
|------|--------|-------------|
| 0 | 确认网关存活 | `curl -sS http://127.0.0.1:8080/healthz` |
| 1 | 安装本客户端 | `pip install pyplasmod` |
| 2 | 配置网关地址（可选） | `export PLASMOD_BASE_URL=http://127.0.0.1:8080`（也可复制仓库内 [`.env.example`](.env.example) 为 `.env`） |
| 3 | 健康检查 | 见下方 Python 片段 |
| 4 | （可选）上传数据 | 文本/文档 **§2.1**；`.fbin` **§2.3**；JSON 矩阵 + ANN 索引 **§2.4**；无数据可跳过 |
| 5 | 发起检索 | `p.search("你的问题", "w_demo", top_k=10)` |
| 6 | 查 API 细节 | `plasmod_help("easy")` 或阅读 [docs/zh-CN/SDK.md](docs/zh-CN/SDK.md) |

**步骤 3 + 5 最小示例**（无需自备数据即可验证连通性；有数据时 `search` 才会返回命中）：

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
    print("health:", p.health())                    # 应返回网关 JSON
    print("search:", p.search("hello", "w_demo"))  # 空库时 objects/hits 可能为空
```

仓库示例脚本（需先 `export PLASMOD_BASE_URL=...`）：

```bash
python examples/http_quickstart.py
```

---

## 启动 Plasmod 网关

**pyplasmod 只负责调用已运行的 Plasmod HTTP 服务**，不包含服务端二进制。网关默认监听 **`127.0.0.1:8080`**（可用环境变量 `PLASMOD_HTTP_ADDR` 覆盖），与本客户端默认的 `PLASMOD_BASE_URL` 一致。

### 方式 A：从 Plasmod 源码本地开发启动（推荐调试）

在 [Plasmod](https://github.com/CodeSoul-co/Plasmod) 仓库根目录：

```bash
# 依赖：Go、Python 3 等，详见 Plasmod README
make dev
```

启动后验证：

```bash
curl -sS http://127.0.0.1:8080/healthz
curl -sS http://127.0.0.1:8080/v1/system/mode
```

更多说明（HNSW 构建、`make build`、种子数据、`scripts/run_demo.py`）见 Plasmod 官方 README 的 **Quick start / Run** 章节。

### 方式 B：Docker Compose 全栈

在 Plasmod 仓库：

```bash
docker compose up -d
```

生产或测试模式可通过 `APP_MODE=prod` / `APP_MODE=test` 等变量切换，详见 Plasmod 文档。

### 方式 C：仅验证 pyplasmod 客户端

若你暂时没有 Plasmod 环境，可先 `pip install pyplasmod` 并运行 `python -c "from pyplasmod import plasmod_help; plasmod_help()"` 查看帮助；**任何 HTTP 调用（`health`、`search`、`upload` 等）都必须有可达的网关**。

### 与客户端对齐的检查清单

| 检查项 | 说明 |
|--------|------|
| URL 一致 | `PLASMOD_BASE_URL`（或代码里 `base_url=`）与网关实际地址一致 |
| 端口可达 | `curl $PLASMOD_BASE_URL/healthz` 返回 2xx |
| Admin 接口 | 调用 `/v1/admin/*` 时配置 `PLASMOD_ADMIN_API_KEY`；开发环境未设置时 Plasmod 可能不校验（生产务必开启） |
| 向量维度 | `.fbin` 或 `ingest_vectors` 的维度须与网关嵌入模型配置一致 |

---

## 选择客户端入口与内置帮助

### 用哪个类？

| 入口 | 适用场景 |
|------|----------|
| **`EasyPlasmod`** | 日常集成：健康检查、`search`/`query`、`.fbin` 上传、`ingest_document`、`memories` |
| **`PlasmodEmbedding`** | **网关侧嵌入**（CPU/GPU 预设、`ingest`/`search`、运行时探针）；也可用 `p.embedding` |
| **`PlasmodClient`**（= `PlasmodHttpClient`） | 需要完整 HTTP/RPC：admin 运维、`ingest_vectors`、二进制 `rpc_*`、内部 task/MAS、WAL SSE 等 |
| **`pyplasmod.data.upload` / `build_query_body`** | 与 HTTP 解耦的辅助函数；可传入 `client=` 复用连接 |
| **`PlasmodVectorStore`** | LangChain 集成（`pip install pyplasmod[langchain]`）；嵌入在**客户端**完成 |

关系：`EasyPlasmod` 内部持有一个 **`PlasmodHttpClient`**，通过 **`p.http`** 访问完整能力。多数示例用 `with EasyPlasmod() as p:` 自动关闭连接。

```python
from pyplasmod import EasyPlasmod, PlasmodClient

# 精简入口
with EasyPlasmod() as p:
    p.health()
    p.http.dataset_delete({...})   # 管理接口走 .http

# 或直接使用完整客户端
with PlasmodClient(base_url="http://127.0.0.1:8080", admin_key="...") as c:
    c.ingest_vectors([[0.1, 0.2, ...]])
```

### 核心概念（小白版）

| 概念 | 含义 |
|------|------|
| **`workspace_id`** | 工作区/租户隔离边界，查询与入库通常都要带（如 `w_demo`） |
| **`dataset_name`** | 逻辑数据集名，用于过滤 bulk 导入的数据；与 `upload(..., dataset=...)` 对应 |
| **`session_id` / `agent_id`** | 会话与智能体标识；**查询时的值须与入库时一致**，否则可能查不到刚写入的数据 |
| **Memory** | 网关物化后的记忆对象；`p.memories(workspace_id)` 列举 |
| **`.fbin`** | SDK 支持的 bulk 向量文件格式（见 §2） |
| **网关嵌入** | 无 `/v1/embed`；文本在 ingest/query 时由服务端 ONNX/GGUF/TF-IDF 等生成向量；CPU/GPU 由 `PLASMOD_EMBEDDER_DEVICE` 控制 |

`upload` 默认 `session_id = ingest_{dataset}_{文件名}`；`build_query_body` 在传入相同 `dataset_name` 与 `ingest_fbin_path` 时会自动对齐该 session。

### `plasmod_help()` 主题

```python
from pyplasmod import plasmod_help, plasmod_topics

plasmod_help()              # 打印主题索引
print(plasmod_topics())     # [..., 'embedding', 'env', ...]
plasmod_help("embedding")   # PlasmodEmbedding / CPU·GPU
plasmod_help("easy")        # EasyPlasmod 说明 + 内置 help() 全文
plasmod_help("env")         # 仅环境变量
```

命令行等价：`python -m pyplasmod`、`python -m pyplasmod upload`、`python -m pyplasmod client`。  
单主题会嵌入 `help(EasyPlasmod)` 等完整签名；`client` 方法较多，建议在 REPL 中 `help(PlasmodHttpClient)` 分页查看。

---

## 前置条件

1. **已部署并启动 Plasmod 网关**（见上文 **[启动 Plasmod 网关](#启动-plasmod-网关)**）。  
2. **Python 3.8 及以上**。  
3. 使用 **`.fbin` 向量文件** 时：文件格式须符合 SDK 约定（见 **§2.3**）；向量维度须与网关侧配置一致。

---

## 安装

```bash
pip install pyplasmod
```

可选依赖（LangChain 向量库适配 `PlasmodVectorStore` 等）：

```bash
pip install pyplasmod[langchain]
```

从本仓库进行可编辑安装与开发测试：

```bash
pip install -e ".[dev]"
make unittest
```

---

## 环境变量与客户端配置

下列环境变量由 `PlasmodHttpClient` / `EasyPlasmod` 在构造时读取（构造参数可覆盖环境变量）。

| 环境变量 | 作用 |
|----------|------|
| `PLASMOD_BASE_URL` 或 `ANDB_BASE_URL` | 网关根 URL；未设置时默认为 `http://127.0.0.1:8080`。 |
| `PLASMOD_HTTP_TIMEOUT` 或 `ANDB_HTTP_TIMEOUT` | HTTP 超时（秒）；未设置时默认为 `30`。 |
| `PLASMOD_ADMIN_API_KEY` 或 `ANDB_ADMIN_API_KEY` | 访问 `/v1/admin/*` 时在请求头中加入 `X-Admin-Key`。 |

**网关嵌入（Plasmod 进程，非 pyplasmod 客户端）** — 由 `PlasmodEmbedding.use_cpu` / `use_gpu` 或 `EmbedderConfig` 写入：

| 环境变量 | 作用 |
|----------|------|
| `PLASMOD_EMBEDDER` | `tfidf` \| `onnx` \| `gguf` \| `tensorrt` \| `openai` \| … |
| `PLASMOD_EMBEDDER_DEVICE` | `cpu` \| `cuda` \| `metal`（本地 ONNX/GGUF 双路径） |
| `PLASMOD_EMBEDDER_DIM` | 向量维度 |
| `PLASMOD_EMBEDDER_MODEL_PATH` | 本地模型路径 |

详见 **[docs/zh-CN/EMBEDDING.md](docs/zh-CN/EMBEDDING.md)** 与 [`.env.example`](.env.example)。

与上述 `PLASMOD_ADMIN_API_KEY` 等价地，亦可在代码中传入 `EasyPlasmod(..., admin_key="...")` 或 `PlasmodHttpClient(..., admin_key="...")`。是否强制校验 Admin Key 由网关部署决定。

```bash
export PLASMOD_BASE_URL=http://127.0.0.1:8080
# export PLASMOD_ADMIN_API_KEY=...   # 仅在需要调用管理接口时配置
```

---

## 常用 API 与 HTTP 路径对照

下表中的 **`p`** 均表示 **`EasyPlasmod`** 的实例。`upload` 与 `build_query_body` 定义在 **`pyplasmod.data`** 中，须单独 `import`（见第 2、3 节示例）。

| 方法 | HTTP | 说明 |
|------|------|------|
| `p.health()` | `GET /healthz` | 存活探针 |
| `p.system_mode()` | `GET /v1/system/mode` | 系统模式等 |
| `p.search(query_text, workspace_id, **kwargs)` | `POST /v1/query` | 内部调用 `build_query_body` 后发起查询；`kwargs` 传入 `build_query_body` 的可选参数（如 `top_k`、`dataset_name`） |
| `p.query(body)` | `POST /v1/query` | 使用完整查询 JSON；`body` 可由 `build_query_body(...)` 生成 |
| `build_query_body(...)` | — | 仅构造 `dict`，**不**发起 HTTP；结果交给 `p.query` |
| `upload(dataset, workspace_id, path, **kwargs)` | `POST /v1/ingest/events`（每行一次） | `.fbin` 按行入库；建议传入 `client=p.http` 以复用连接 |
| `p.upload_fbin(...)` | 同上 | 与 `upload` 等价，内部固定使用 `p.http` |
| `p.ingest_document(body)` | `POST /v1/ingest/document` | 长文档分块写入；`body` 至少包含 `text`，通常包含 `workspace_id`、`agent_id`、`session_id`、`title` |
| `p.memories(workspace_id, **params)` | `GET /v1/memory` | 列举指定 `workspace_id` 下的 Memory |
| `p.embedding.ingest(text, workspace_id)` | `POST /v1/ingest/events` | 文本入库，**服务端**嵌入（CPU/GPU 由网关 env 决定） |
| `p.embed_search(query, workspace_id, **kw)` | `POST /v1/query` | 同上，语义检索简写 |
| `p.embedding.runtime(...)` | `POST /v1/query`（探针） | 从 `provenance` 解析 `embedding_runtime_family` / `dim` |
| `PlasmodEmbedding.use_onnx_cpu/gpu(..., apply=True)` | —（写 `os.environ`） | 启动 Plasmod **前** 配置 CPU/GPU 预设 |
| `p.http.dataset_delete(body)` | `POST /v1/admin/dataset/delete` | 数据集软删除（`body` 字段以服务端为准） |
| `p.http.dataset_purge(body)` | `POST /v1/admin/dataset/purge` | 数据集硬清理；执行前应使用 `dry_run: True` 评估影响 |
| `p.http.dataset_purge_task(task_id)` | `GET /v1/admin/dataset/purge/task` | 查询异步 purge 任务状态 |

其余 HTTP 与 RPC 接口均位于 **`PlasmodHttpClient`** 实例上。`EasyPlasmod` 通过属性 **`http`** 暴露该实例。类型别名 **`PlasmodClient`** 与 **`PlasmodHttpClient`** 指向同一类。完整方法名列表见 [docs/zh-CN/SDK.md](docs/zh-CN/SDK.md)。

---

## 1. 健康检查

用于确认网络可达且网关进程正常：

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
    print(p.health())
    # print(p.system_mode())
```

---

## 2. 上传数据

入库方式取决于数据形态：**长文本/文档** → `ingest_document`（§2.1）；**已向量化或逐条事件** → `.fbin` / `ingest_event`（§2.2–2.3）；**内存中的 JSON 向量矩阵且需指定 ANN 索引** → `ingest_vectors`（§2.4）。与后续 `search` 共用同一 `EasyPlasmod` 实例，并记住 **`workspace_id`、`session_id`、`agent_id` 在查询时须与入库一致**。

### 2.1 文本与长文档（`ingest_document`）

网关 `POST /v1/ingest/document` 会将 **`text`** 按块切分为多条 episodic memory 事件（服务端分块，无需客户端自己切句）。

| 字段 | 是否必填 | 说明 |
|------|----------|------|
| `text` | **是** | 正文（字符串） |
| `workspace_id` | 强烈建议 | 工作区，如 `w_demo` |
| `agent_id` | 强烈建议 | 智能体 ID，查询时需一致 |
| `session_id` | 强烈建议 | 会话 ID，查询时需一致 |
| `title` | 建议 | 文档标题，便于检索与运维 |
| `chunk_size` | 可选 | 分块大小（字符/字节语义以网关为准） |
| `overlap` | 可选 | 相邻块重叠长度 |
| `importance` | 可选 | 重要性权重（若网关支持） |

**直接写入字符串**：

```python
from pyplasmod import EasyPlasmod

workspace = "w_demo"
session_id = "my_doc_session"   # 查询时沿用同一 session_id
agent_id = "pyplasmod_data"

with EasyPlasmod() as p:
    r = p.ingest_document(
        {
            "text": "这是要入库的正文。可以是一段说明、会议纪要或 RAG 文档内容。",
            "workspace_id": workspace,
            "agent_id": agent_id,
            "session_id": session_id,
            "title": "示例文档",
            "chunk_size": 500,   # 可选：控制分块粒度
            "overlap": 50,       # 可选：块间重叠
        }
    )
    print("ingest_document:", r)
```

**从本地文件读取再上传**（`.txt`、`.md` 等纯文本）：

```python
from pathlib import Path
from pyplasmod import EasyPlasmod
from pyplasmod.data import build_query_body

path = Path("/path/to/readme.md")
workspace = "w_demo"
session_id = "readme_session"
agent_id = "pyplasmod_data"

with EasyPlasmod() as p:
    p.ingest_document(
        {
            "text": path.read_text(encoding="utf-8"),
            "workspace_id": workspace,
            "agent_id": agent_id,
            "session_id": session_id,
            "title": path.name,
        }
    )
    # 检索时传入相同的 session_id / agent_id
    hits = p.query(
        build_query_body(
            "文档里讲了什么？",
            workspace,
            session_id=session_id,
            agent_id=agent_id,
            top_k=5,
        )
    )
    print(hits)
```

`ingest_document` **不要求**本地准备 `.fbin` 或 `embedding_vector`（嵌入由网关侧完成）。适合 RAG 语料、说明文档、对话纪要等纯文本场景。

也可用嵌入门面一次完成（等价于网关侧嵌入 + 后续 `search`）：

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
    p.embedding.ingest_document(
        "长文档正文……",
        workspace_id="w_demo",
        title="手册",
        session_id="doc_session",
    )
```

### 2.2 单条短文本（`ingest_event`）

需要写入**单条**结构化事件（可带自定义 `payload`、可选向量）时，使用 `POST /v1/ingest/events`：

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
  p.ingest_event(
      {
          "event_id": "evt_note_001",       # 建议全局唯一
          "workspace_id": "w_demo",
          "agent_id": "pyplasmod_data",
          "session_id": "notes_session",
          "event_type": "observation",
          "payload": {"text": "一条简短的观察或备注"},
          "source": "my_app",
          "version": 1,
          # 若网关要求向量字段，可添加 embedding_vector: [0.1, 0.2, ...]
      }
  )
```

多条可循环调用 `ingest_event`，或使用 `p.http.ingest_events([...])` 批量提交。字段完整列表以 [Plasmod HTTP API](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api) 为准。

### 2.3 向量文件（`.fbin`）

**文件格式**：前 8 字节为 little-endian `uint32` 行数、`uint32` 维度；随后为按行排列的 **little-endian `float32`** 向量。当前 `upload` **仅支持** 后缀名为 `.fbin` 的文件；其他后缀将抛出 `ValueError` 并提示暂不支持。

```python
from pyplasmod import EasyPlasmod
from pyplasmod.data import upload

with EasyPlasmod() as p:
    n = upload(
        "my_dataset",
        "w_demo",
        "/path/to/vectors.fbin",
        client=p.http,
        limit=0,
        show_progress=True,
    )
    print("ingested rows:", n)
```

命令行等价入口：

```bash
python -m pyplasmod.data upload my_dataset w_demo /path/to/vectors.fbin --show-progress
```

已有 **JSON 向量矩阵**（非 `.fbin`）时，用 `p.http.ingest_vectors` 或大规模场景下的 `p.http.ingest_batch`（PLIB）；若需选择 warm 段 ANN 索引类型，见 **§2.4**。

### 2.4 JSON 向量与 warm ANN 索引（`ingest_vectors`）

通过 `POST /v1/ingest/vectors` 用已有向量**构建 warm 段**；`index_type` 在入库时选定，查询须使用同一 `segment_id`（或查询 JSON 中的 `warm_segment_id`）。

| `index_type` | 何时考虑 |
|--------------|----------|
| `HNSW` | **默认**（省略 `index_type` 即可） |
| `IVF_FLAT` / `IVF_PQ` / `IVF_SQ8` | 向量量大；可调 `ivf_nlist`、`ivf_nprobe` 等 |
| `DISKANN` | 超大规模、偏磁盘友好 |

**注意：** 仅 `ingest_vectors` 支持 `index_type`；

```python
from pyplasmod import PlasmodClient, WARM_INDEX_IVF_FLAT

with PlasmodClient() as c:
    c.ingest_vectors(
        [[0.1, 0.2, ...]],  # 维度须与网关 warm 段 / 嵌入配置一致
        segment_id="demo.ivf",
        index_type=WARM_INDEX_IVF_FLAT,  # 也可写 "IVF_FLAT"
        ivf_nlist=128,
        ivf_nprobe=32,
    )
```

省略 `index_type` 即服务端默认 **HNSW**。`IVF_PQ`、`DISKANN` 等同理传入对应常量或字符串。完整字段与 `ingest_batch` 对比见 [docs/zh-CN/SDK.md](docs/zh-CN/SDK.md) §10。

---

## 3. 查询（自然语言检索）

**简易用法**（内部完成 `build_query_body` 与 `POST /v1/query`）：

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod()
r = p.search("示例问题", "w_demo", top_k=10)
print(r)
```

**与 `upload` 使用相同逻辑数据集名、并对齐会话规则**时，使用 `build_query_body` 显式传入 `dataset_name` 与 `ingest_fbin_path`（路径与上传时使用的 `.fbin` 一致即可，通常需包含相同文件名）：

```python
from pyplasmod import EasyPlasmod
from pyplasmod.data import build_query_body

p = EasyPlasmod()
body = build_query_body(
    "示例问题",
    "w_demo",
    top_k=20,
    dataset_name="my_dataset",
    ingest_fbin_path="/path/to/vectors.fbin",
)
r = p.query(body)
print(r)
```

响应 JSON 的结构由服务端版本决定。常见字段包括 **`objects`** 或 **`hits`** 等；请以实际返回为准。

---

## 3.1 网关嵌入与 CPU / GPU（`PlasmodEmbedding`）

Plasmod **没有** 单独的 embed HTTP 接口；向量在 **ingest / query** 时由网关内的 embedder 生成。pyplasmod 用 **`PlasmodEmbedding`** 封装该流程，并映射 Plasmod 的 **CPU / GPU 双路径**（ONNX、GGUF、TensorRT 等）。

**最小用法**（文本入库 + 检索 + 查看网关实际 embedder）：

```python
from pyplasmod import PlasmodEmbedding

with PlasmodEmbedding.connect() as emb:
    emb.ingest("要入库的句子", workspace_id="w_demo")
    print(emb.search("检索词", workspace_id="w_demo", top_k=5))
    print(emb.runtime())  # family / dim（来自 query provenance）
```

**与 `EasyPlasmod` 相同能力**：

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
    p.embed_ingest("要入库的句子", workspace_id="w_demo")
    print(p.embed_search("检索词", workspace_id="w_demo"))
```

**部署前选择 CPU 或 GPU**（写入环境变量后启动 Plasmod）：

```python
from pyplasmod import PlasmodEmbedding

emb = PlasmodEmbedding.connect()
emb.use_onnx_cpu(model_path="/models/model.onnx", dim=384, apply=True)   # CPU
# emb.use_onnx_gpu(model_path="/models/model.onnx", dim=384, apply=True)  # CUDA
print(emb.capabilities())  # 各 provider 的 cpu/cuda/metal 能力表
```

专题文档：**[docs/zh-CN/EMBEDDING.md](docs/zh-CN/EMBEDDING.md)**。架构细节见 [docs/zh-CN/SDK.md](docs/zh-CN/SDK.md) §8。

---

## 4. 估算条数（近似）

Plasmod 未必提供独立 COUNT 接口。可采用下列方式之一获得**近似或当前页范围内**的数量（需将 `top_k` 或 Memory 列表的 `limit` 设为足够大）。

**方式 A：根据查询结果中的列表长度**

```python
from pyplasmod import EasyPlasmod
from pyplasmod.data import build_query_body

p = EasyPlasmod()
r = p.query(build_query_body(".", "w_demo", top_k=5000))
objs = r.get("objects") or []
print("objects in response:", len(objs))
```

**方式 B：根据 Memory 列表接口返回长度**

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod()
rows = p.memories("w_demo")
print("memories in response:", len(rows or []))
```

---

## 5. 数据集删除与清理（管理接口）

以下接口属于 **`/v1/admin/*`**。若网关启用密钥校验，须配置 `PLASMOD_ADMIN_API_KEY` 或构造时传入 `admin_key`。

**软删除数据集**（语义以服务端为准）：

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod(admin_key="...")
print(p.http.dataset_delete({"workspace_id": "w_demo", "dataset_name": "my_dataset"}))
```

**硬清理（purge）**：须先使用 **`dry_run: True`** 评估影响，确认后再执行实际删除。

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod(admin_key="...")
print(
    p.http.dataset_purge(
        {"workspace_id": "w_demo", "dataset_name": "my_dataset", "dry_run": True}
    )
)
```

**异步 purge 任务查询**（当服务端返回 `task_id` 时）：

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod(admin_key="...")
print(p.http.dataset_purge_task("<task_id>"))
```

---

## 6. 示例脚本与扩展阅读

| 路径 | 内容 |
|------|------|
| `examples/http_quickstart.py` | HTTP 快速示例（`python examples/http_quickstart.py`） |
| `examples/ingest_fbin.py` | `.fbin` 入库示例 |
| `examples/batch_ingest.py` | 批量向量 / 事件 |
| `examples/langchain_quickstart.py` | LangChain 集成（需 `pip install pyplasmod[langchain]`） |
| `examples/embedding_cpu_gpu.py` | 网关嵌入与 CPU/GPU 预设、`PlasmodEmbedding` |

- **网关嵌入（CPU/GPU）**：[docs/zh-CN/EMBEDDING.md](docs/zh-CN/EMBEDDING.md)  
- **SDK 架构与实现**：[docs/zh-CN/SDK.md](docs/zh-CN/SDK.md)  
- **SDK 用户指南**（参数、样例、排错）：[docs/zh-CN/plans/pyplasmod-003-sdk-usage-guide.md](docs/zh-CN/plans/pyplasmod-003-sdk-usage-guide.md)  
- **HTTP SDK 架构说明**：[docs/zh-CN/plans/pyplasmod-001-http-sdk-design.md](docs/zh-CN/plans/pyplasmod-001-http-sdk-design.md)  
- **Tier B 扩展 API**：[docs/zh-CN/plans/pyplasmod-002-gateway-tier-b-shortcuts-design.md](docs/zh-CN/plans/pyplasmod-002-gateway-tier-b-shortcuts-design.md)  
- **英文文档索引**：[docs/README.md](docs/README.md)  
- **路由与字段映射**：[Plasmod `docs/sdk/README.md`](https://github.com/CodeSoul-co/Plasmod/blob/main/docs/sdk/README.md)  
- **二进制帧工具**：`from pyplasmod.http import encode_ingest_batch` 等（多数场景可直接使用 `PlasmodHttpClient.rpc_*`）

---

## 许可证

MIT（见仓库根目录 `LICENSE`）。
