# pyplasmod SDK 使用指南（参数、填法与样例）

- **Created:** 2026-05-06
- **Updated:** 2026-05-06
- **Author(s):** pyplasmod 维护者

本文面向 **在本仓库内开发与联调** 的读者，说明如何安装与配置环境、如何选择 **`EasyPlasmod` / `PlasmodHttpClient`（`PlasmodClient`）/ `pyplasmod.data`**，以及各层 API 的**参数含义、推荐填法**与**可复制样例**。权威 JSON 字段与路由仍以 Plasmod 仓库 [`docs/api`](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api) 与 [`gateway.go`](https://github.com/CodeSoul-co/Plasmod/blob/main/src/internal/access/gateway.go) 为准；本指南与实现对齐到当前 `pyplasmod` 代码。

---

## 1. 安装与运行前提

```bash
pip install pyplasmod
# 或在本仓库根目录：
pip install -e ".[dev]"
```

- **Python**：3.8+
- **运行时依赖**：`requests`
- **服务端**：本机或远端已启动 Plasmod/ANDB HTTP 网关（默认监听示例见 Plasmod `docs/api/overview.md`）。

---

## 2. 环境变量（客户端）

| 变量 | 作用 |
|------|------|
| `PLASMOD_BASE_URL` 或 `ANDB_BASE_URL` | HTTP 根地址；未设置时默认为 `http://127.0.0.1:8080`。 |
| `PLASMOD_HTTP_TIMEOUT` 或 `ANDB_HTTP_TIMEOUT` | 秒数，默认 `30`。 |
| `PLASMOD_ADMIN_API_KEY` 或 `ANDB_ADMIN_API_KEY` | 访问 `/v1/admin/*` 时自动加到请求头 **`X-Admin-Key`**（也可在构造客户端时传入 `admin_key`）。 |

说明：凡路径以 **`/v1/admin/`** 开头的 `request_json` / 封装方法，在配置了 `admin_key`（或上述环境变量）时会自动带 `X-Admin-Key`，无需每次手写。

---

## 3. 模块分层：该用哪一个？

| 入口 | 典型场景 |
|------|----------|
| **`PlasmodHttpClient`**（别名 **`PlasmodClient`**） | 需要**完整网关面**：ingest/query、Admin、二进制 RPC、Tier B internal、CRUD 等。 |
| **`EasyPlasmod`** | Demo / 小应用：**健康检查、文本检索、ingest、`.fbin` 上传、列 memory**；其余一律走 **`EasyPlasmod.http`**（即同一个 `PlasmodHttpClient`）。 |
| **`pyplasmod.data`**（`build_query_body`、`upload`） | 构造 **`/v1/query`** 请求体；把 **`.fbin`** 按行打成 **`ingest_event`** 批量上传。 |
| **`pyplasmod.http.binary`** | 自行组 **`PLIB` / `PLQW` / `PLQB`** 字节流，或解码响应（一般更推荐用客户端上的 **`rpc_*`** 方法）。 |

---

## 4. `PlasmodHttpClient`（`PlasmodClient`）

### 4.1 构造参数

```python
from pyplasmod import PlasmodHttpClient, PlasmodHttpError

client = PlasmodHttpClient(
    base_url=None,       # None 时按环境变量 → 默认 127.0.0.1:8080
    timeout=None,      # None 时用 PLASMOD_HTTP_TIMEOUT / ANDB_HTTP_TIMEOUT / 30
    admin_key=None,    # None 时用 PLASMOD_ADMIN_API_KEY / ANDB_ADMIN_API_KEY / ""
    session=None,      # 可选传入已有 requests.Session
)
```

- 上下文管理：`with PlasmodHttpClient(...) as c:`，退出时关闭自建的 `Session`。
- 手动关闭：`client.close()`。

### 4.2 通用底层方法

**`request_json(method, path, *, json_body=None, params=None, headers=None)`**

- **`method`**：`GET` / `POST` 等。
- **`path`**：以 `/` 开头，例如 `"/v1/query"`。
- **`json_body`**：`dict` 或 `list`，会作为 JSON 请求体（`GET` 通常不传）。
- **`params`**：查询字符串键值。
- **返回**：解析后的 JSON（`dict`/`list` 等）；空响应体时可能为 `None`。

**`request_bytes(method, path, *, data: bytes, headers=None)`**

- 用于非 JSON 或自定义 Content-Type；返回 **`(status_code, response_body: bytes, response_headers)`**。

### 4.3 核心 JSON 快捷方法（Tier A 主路径）

以下方法均为 **`json_body=dict(...)`** 的薄封装，字段名需与服务端一致。

| 方法 | HTTP | `body` / 要点 |
|------|------|----------------|
| `health()` | `GET /healthz` | 无参数。 |
| `system_mode()` | `GET /v1/system/mode` | 无参数。 |
| `ingest_event(event)` | `POST /v1/ingest/events` | **`event`**：`Mapping`，常见键含 `event_id`、`tenant_id`、`workspace_id`、`agent_id`、`session_id`、`event_type`、`event_time`、`ingest_time`、`visible_time`、`embedding_vector`（float 列表）、`payload`（常含 `text`）、`source`、`version` 等。 |
| `ingest_vectors(vectors, *, segment_id="warm.default", object_ids=None)` | `POST /v1/ingest/vectors` | **`vectors`**：若干等长 float 行；可选 **`object_ids`** 与行数一致。 |
| `ingest_document(body)` | `POST /v1/ingest/document` | **`body`**：至少含网关要求的 **`text`**；常用还有 `agent_id`、`session_id`、`workspace_id`、`title`，以及可选 `chunk_size`、`overlap`、`importance`、`upload_batch_id`、`segment_index`、`segment_total` 等。 |
| `query(body)` | `POST /v1/query` | **`body`**：查询请求 JSON；可用 `build_query_body` 生成（见第 6 节）。 |
| `warm_prebuild()` | `POST /v1/admin/warm/prebuild` | 无 body。 |
| `dataset_delete(body)` | `POST /v1/admin/dataset/delete` | 例如 `{"workspace_id": "w_demo", "dataset_name": "myds"}`。 |
| `dataset_purge(body)` | `POST /v1/admin/dataset/purge` | 例如 `{"workspace_id": "w_demo", "dataset_name": "myds", "dry_run": True}`；与 `admin_dataset_purge` 同一路径。 |
| `dataset_purge_task(task_id)` | `GET /v1/admin/dataset/purge/task` | **`task_id`**：查询参数 `task_id`。 |
| `warm_segment_register(body)` | `POST /v1/internal/warm-segment/register` | 见服务端 warm 段注册契约。 |

**ingest_document 最小样例**（与 `examples/test.py` 思路一致）：

```python
import os
from pyplasmod import PlasmodClient

c = PlasmodClient(admin_key=os.environ.get("PLASMOD_ADMIN_API_KEY", ""))
body = {
    "agent_id": "pyplasmod_data",
    "session_id": "test_doc_only",
    "workspace_id": "w_demo",
    "title": "标题",
    "text": "正文……",
}
print(c.ingest_document(body))
```

### 4.4 二进制 RPC 快捷方法

客户端内部使用 **`application/octet-stream`** 发送 **`PLIB` / `PLQW` / `PLQB`** 帧；帧编码与 Go 端 **`framing.go`** 对齐。

| 方法 | 说明 |
|------|------|
| `rpc_ingest_batch(segment_id, vectors, object_ids=None, *, wire_version=1\|2)` | 返回服务端 JSON 文本解析结果或 `None`；非 200 抛 `PlasmodHttpError`。 |
| `rpc_query_warm(segment_id, top_k, vector)` | **`vector`** 长度须与段维度一致；返回解码后的 id 列表等（见 `decode_query_warm_response`）。 |
| `rpc_query_warm_batch(segment_id, top_k, queries)` | 返回 **`(nq, topk, internal_ids, distances)`**（内部 id，非业务 object id 时需结合 `rpc_register_warm` 映射）。 |
| `rpc_query_warm_batch_raw(...)` | 同 PLQB 体，走服务端 Raw 检索路径。 |
| `rpc_unload_segment(segment_id)` | JSON body：`{"segment_id": "..."}`。 |
| `rpc_register_warm(body)` | 例如 `{"segment_id": "warm.default"}`。 |

**烟测片段**（与 `examples/try.py` 一致；需服务端已注册 warm 段且维度匹配）：

```python
dim = 128  # 须与 warm 段一致
vec = [0.0] * dim
try:
    print(client.rpc_query_warm("warm.default", 2, vec))
except PlasmodHttpError as e:
    print(e.status_code, e.body[:200])
```

### 4.5 Canonical CRUD（GET 列表 / POST 创建或替换）

每组两个方法：**`*_get(params=None)`**、**`*_post(body)`**，路径分别为：

`/v1/agents`、`/v1/sessions`、`/v1/memory`、`/v1/states`、`/v1/artifacts`、`/v1/edges`、`/v1/policies`、`/v1/share-contracts`。

- **`params`**：过滤、分页等键值对，**以服务端为准**。
- **`body`**：POST 的 JSON 对象。

**memory 列表示例**：

```python
rows = client.memory_get(params={"workspace_id": "w_demo"}) or []
print(len(rows))
```

### 4.6 Traces 与 internal memory 算法桥

| 方法 | HTTP |
|------|------|
| `traces_get(object_id)` | `GET /v1/traces/{object_id}`（`object_id` 会做 URL 编码） |
| `internal_memory_recall(body)` 等 | `POST /v1/internal/memory/...`（`recall` / `ingest` / `compress` / `summarize` / `decay` / `share` / `conflict/resolve` / `stale` / `conflict/inject`） |

请求体字段请对照 **`gateway.go`** 与 Plasmod **`docs/api`**；与 **`/v1/memory`** 的 CRUD（`memory_get` / `memory_post`）是不同路由。

### 4.7 Tier B 与其它 JSON 面（Admin 扩展、internal task、MAS、debug）

下列方法均为 **`request_json` 薄封装**；具体键名、是否必填、枚举取值以 **`Gateway.RegisterRoutes`** 为准。联调时可参考仓库内 **`examples/try.py`**。

- **Admin 扩展**：`admin_topology_get`、`admin_storage_get`、`admin_config_effective_get`、`admin_s3_export`、`admin_s3_snapshot_export`、`admin_s3_cold_purge`、`admin_data_wipe`、`admin_rollback`、`admin_replay`、`admin_consistency_mode_get/post`、`admin_metrics_get`、`admin_governance_mode_get/post`、`admin_runtime_mode_get/post`、`admin_algorithm_profile_mode_get/post`、`admin_algorithm_profile_health_get`。
- **Internal task / plan / MAS**：`internal_task_start`、`internal_task_complete`、`internal_task_tokens`、`internal_task_claim`、`internal_task_stage`、`internal_plan_step`、`internal_plan_repair`、`internal_mas_answer_consistency`、`internal_mas_aggregate`。
- **其它**：`internal_tool_state_get`、`internal_agent_handoff`、`agent_list_get`、`internal_session_context_get`（**`params` 必填**）、`internal_eval_ground_truth_get/post`、`debug_echo`（仅服务端 test 模式可能注册）。

**`admin_data_wipe` 破坏性示例**（仅联调环境）：

```python
print(client.admin_data_wipe({"confirm": "delete_all_data"}))
```

**`internal_task_stage` 示例**（`try.py`：`task/stage` 需与 `task_start` 使用同一 `agent_id`）：

```python
_sid, _aid = "sess_try", "agent_try"
client.internal_task_start(
    {"session_id": _sid, "task_type": "smoke", "goal": "demo", "agent_id": _aid}
)
client.internal_task_stage(
    {
        "session_id": _sid,
        "agent_id": _aid,
        "stage": "outline",
        "stage_index": 0,
        "total_stages": 1,
        "description": "d",
    }
)
```

---

## 5. `EasyPlasmod`

### 5.1 构造与 `http` 属性

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod(base_url="http://127.0.0.1:8080", admin_key="...") as ez:
    print(ez.health())
    # 完整能力：
    print(ez.http.admin_topology_get())
```

构造参数与 **`PlasmodHttpClient`** 相同：`base_url`、`timeout`、`admin_key`、`session`。

### 5.2 封装方法一览

| 方法 | 行为说明 |
|------|----------|
| `health()` | 同 `http.health()`。 |
| `system_mode()` | 同 `http.system_mode()`。 |
| `query(body)` | 同 `http.query(body)`。 |
| `search(query_text, workspace_id, **kwargs)` | 内部 **`build_query_body(query_text, workspace_id, **kwargs)`** 再 **`http.query`**。 |
| `ingest_event(event)` | 同 `http.ingest_event`。 |
| `ingest_document(body)` | 同 `http.ingest_document`。 |
| `upload_fbin(dataset, workspace_id, path, **kwargs)` | 调用 **`pyplasmod.data.upload(..., client=self.http, ...)`**，返回成功 ingest 的行数。 |
| `memories(workspace_id, **params)` | **`GET /v1/memory`**：自动合并 `workspace_id` 到 query，再传入 `params`。 |

**search 与 upload 联用思路**：先用 `upload_fbin` 写入向量事件（默认 `session_id` 为 `ingest_{dataset}_{文件名}`），再用 `search` 时若按数据集过滤，需让 **`build_query_body` 的 session 规则**与 ingest 一致（见第 6 节 `dataset_name` + `ingest_fbin_path`）。

---

## 6. `pyplasmod.data`：`build_query_body` 与 `upload`

### 6.1 `build_query_body(query_text, workspace_id, *, ...)`

生成 **`PlasmodHttpClient.query`** 所需的 **`dict`**，**不发起 HTTP**。

| 参数 | 含义与填法 |
|------|------------|
| `query_text` | 自然语言查询字符串。 |
| `workspace_id` | 工作空间 id；同时会写入 `query_scope`（与当前实现一致）。 |
| `tenant_id` | 默认 `"t_demo"`。 |
| `session_id` | 若为空字符串：当 **`dataset_name` 与 `ingest_fbin_path` 均非空** 时，自动设为 **`ingest_{dataset_name}_{fbin文件名}`**（与 `upload` 默认 session 对齐）；否则为 **`query_{workspace_id}`**。 |
| `agent_id` | 默认 `"pyplasmod_data"`；若网关按 ingest 过滤，需与写入时一致。 |
| `top_k` | 整数，默认 `10`。 |
| `response_mode` | 默认 `"structured_evidence"`。 |
| `include_cold` | 默认 `True`。 |
| `dataset_name` | 非空时写入 body，用于按数据集过滤（需与 ingest 时 payload 中的 dataset 等一致，见服务端行为）。 |
| `import_batch_id` / `latest_batch_only` / `source_file_name` | 按需过滤导入批次或源文件名。 |
| `ingest_fbin_path` | **`Path` 或 `str`**，仅用于推导默认 **`session_id`**（见上）。 |
| `extra` | **`Mapping`**，合并进 body（可覆盖前述字段）。 |

**示例**：

```python
from pyplasmod.data import build_query_body
from pyplasmod import PlasmodClient

c = PlasmodClient()
body = build_query_body("hello", "w_demo", top_k=5, dataset_name="myds", ingest_fbin_path="/data/x.fbin")
print(c.query(body))
```

### 6.2 `upload(dataset, workspace_id, path, *, ...)`

将 **`.fbin`**（头 8 字节：`uint32 n`、`uint32 dim`，随后 `n×dim` 个 **little-endian float32**）按行拆成多条 **`ingest_event`** 顺序 POST。

| 参数 | 含义与填法 |
|------|------------|
| `dataset` | 逻辑数据集名，进入 payload 与 `event_id` 片段。 |
| `workspace_id` | 工作空间。 |
| `path` | `.fbin` 文件路径。 |
| `client` | 若传入，则使用该 **`PlasmodHttpClient`**；否则内部临时 new 一个（可用 **`base_url`** 指定）。 |
| `tenant_id` | 默认 `"t_demo"`。 |
| `agent_id` | 默认 `"pyplasmod_data"`。 |
| `session_id` | 默认 **`ingest_{dataset}_{文件名}`**。 |
| `import_batch_id` | 若留空，每次 **`upload()`** 调用会生成新的批次 id（避免无意合并批次）。 |
| `limit` | `>0` 时最多读前 `limit` 行；`0` 表示全部。 |
| `dry_run` | `True` 时只构造第一行事件、**不 POST**。 |
| `show_progress` / `progress_every` / `on_progress` / `progress_file` | 进度展示与回调。 |
| `event_id_scope` | `"file"` 或 `"batch"`，影响 `event_id` 命名策略。 |

**示例**：

```python
from pyplasmod.data import upload
from pyplasmod import PlasmodClient

c = PlasmodClient()
n = upload("my_dataset", "w_demo", "/data/vectors.fbin", client=c, limit=100, show_progress=True)
print("ingested", n)
```

**命令行**（等价入口）：

```bash
python -m pyplasmod.data upload my_dataset w_demo /path/to/file.fbin
```

---

## 7. `pyplasmod.http.binary`（低级编解码）

适合自定义调用 **`request_bytes`** 或调试：

- **`encode_ingest_batch` / `encode_query_warm` / `encode_query_warm_batch`**
- **`decode_query_warm_response` / `decode_query_warm_batch_response`**

通常直接使用 **`PlasmodHttpClient.rpc_*`** 即可，无需手动组帧。

---

## 8. 错误处理

非 2xx 或网络失败时，JSON 路径会抛出 **`PlasmodHttpError`**（继承自包内 **`PlasmodException`**），常用属性：

- **`status_code`**：HTTP 状态码（连接失败时可能为 `0`）。
- **`path`**：请求路径。
- **`body`**：响应体文本（便于打印服务端错误信息）。

```python
from pyplasmod import PlasmodClient, PlasmodHttpError

try:
    PlasmodClient().query({"query_text": "x", "workspace_id": "w"})
except PlasmodHttpError as e:
    print(e.status_code, e.path, (e.body or "")[:500])
```

---

## 9. 推荐阅读与示例脚本

| 资源 | 说明 |
|------|------|
| [Plasmod docs/api/overview.md](https://github.com/CodeSoul-co/Plasmod/blob/main/docs/api/overview.md) | 路由分组与延伸阅读。 |
| 本仓库 **`examples/test.py`** | 仅 `ingest_document` 的最小脚本。 |
| 本仓库 **`examples/try.py`** | 双数据集、purge、memory、二进制 RPC、Tier B、internal task 等烟测。 |
| [pyplasmod-001-http-sdk-design.md](pyplasmod-001-http-sdk-design.md) | 设计背景与边界。 |

---

## 10. 变更记录

| 日期 | 说明 |
|------|------|
| 2026-05-06 | 首版：覆盖构造、通用请求、Tier A/B、EasyPlasmod、data、binary、错误处理与样例。 |
