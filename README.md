# pyplasmod

面向 **[Plasmod](https://github.com/CodeSoul-co/Plasmod)** 的 **Python HTTP SDK**：HTTP 路由与 JSON 形态以服务端 **[`docs/api/overview.md`](https://github.com/CodeSoul-co/Plasmod/blob/main/docs/api/overview.md)** 及 **[`docs/api`](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api)** 下细分文档为准；**`/v1/internal/rpc/*`** 二进制帧（PLIB / PLQW / PLQB）以源码 **`src/internal/transport/framing.go`** 与 **`Gateway.RegisterRoutes`**（[`gateway.go`](https://github.com/CodeSoul-co/Plasmod/blob/main/src/internal/access/gateway.go)）为准；产品能力总览见 **Plasmod 根目录 README**（链接见下）。

**Plasmod 是什么**  
Plasmod 面向多智能体系统，将认知对象存储、事件驱动的物化与结构化证据检索整合在可运行的系统中。

## 安装

需要 Python 3.8+。

```bash
pip install pyplasmod
```

开发：

```bash
pip install -e ".[dev]"
make unittest
```

## 契约与文档

本仓库 **不复制** Plasmod 长篇契约全文；请以服务端文档为准：

- **产品与 HTTP 能力总览（README）**：[Plasmod README（GitHub）](https://github.com/CodeSoul-co/Plasmod/blob/main/README.md)  
- **HTTP API 文档（路由总览 + ingest/query/admin）**：[docs/api/overview.md](https://github.com/CodeSoul-co/Plasmod/blob/main/docs/api/overview.md) · [docs/api 目录](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api)
- **本仓库已实现能力与测试说明**：[docs/SDK.md](docs/SDK.md)（可仅在本地保留、不上传远端时，**对外 API 以本节表格为准**）

## 已实现 API 一览（方法 · 参数 · 地址 · 描述）

下列为 **本仓库已实现** 的对外能力：**地址** 为相对服务根（`base_url`，默认读 `PLASMOD_BASE_URL` / `ANDB_BASE_URL`，再 `http://127.0.0.1:8080`）的路径；**参数** 为调用要点，完整 JSON 字段以 **Plasmod** [docs/api](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api) 与 [`gateway.go`](https://github.com/CodeSoul-co/Plasmod/blob/main/src/internal/access/gateway.go) 为准。

### 用户精简封装 `EasyPlasmod`（`pyplasmod/easy.py`）

进阶能力通过 **`EasyPlasmod.http`** 使用完整 **`PlasmodHttpClient`**。

| 方法 | 参数 | 地址 | 描述 |
|------|------|------|------|
| `EasyPlasmod(...)` | `base_url?`, `timeout?`, `admin_key?`, `session?` | — | 内部创建 `PlasmodHttpClient`；`admin_key` 亦可来自环境变量。 |
| `EasyPlasmod.http` | — | — | 只读，为 **`PlasmodHttpClient`** 实例。 |
| `close()` / `with` | 无 | — | 关闭或随上下文退出时关闭底层 Session。 |
| `health()` | 无 | `GET /healthz` | 存活探针。 |
| `system_mode()` | 无 | `GET /v1/system/mode` | 读取系统模式（如 `app_mode`）。 |
| `query(body)` | `body`：QueryRequest 形字典 | `POST /v1/query` | 结构化检索。 |
| `search(query_text, workspace_id, **kwargs)` | 查询串、`workspace_id`，其余传入 `build_query_body` | `POST /v1/query` | 拼查询体并检索一步完成。 |
| `ingest_event(event)` | 单条事件字典 | `POST /v1/ingest/events` | 单条事件入库。 |
| `ingest_document(body)` | 长文档字段（`text`、`workspace_id`、`agent_id`、`session_id` 等） | `POST /v1/ingest/document` | 服务端分块写入 episodic memory。 |
| `upload_fbin(dataset, workspace_id, path, **kwargs)` | 同 **`pyplasmod.data.upload`**，内部固定 `client=self.http` | 多次 `POST /v1/ingest/events` | `.fbin` 按行入库。 |
| `memories(workspace_id, **params)` | `workspace_id` 及可选查询参数 | `GET /v1/memory` | 列出 workspace 下 memory。 |

### `PlasmodHttpClient` / `PlasmodClient`（`pyplasmod/http/client.py`）

#### 通用

| 方法 | 参数 | 地址 | 描述 |
|------|------|------|------|
| `request_json(method, path, …)` | HTTP 方法、路径、可选 `json_body` / `params` / `headers` | 任意 | 通用 JSON；`/v1/admin/*` 且配置了 Admin Key 时自动加 `X-Admin-Key`。 |
| `request_bytes(method, path, …)` | 路径、`data: bytes`、可选头 | 任意 | 原始字节请求；返回 `(status_code, body_bytes, headers)`。 |

#### 健康与入库 / 查询

| 方法 | 参数 | 地址 | 描述 |
|------|------|------|------|
| `health()` | 无 | `GET /healthz` | 存活探针。 |
| `system_mode()` | 无 | `GET /v1/system/mode` | 系统模式。 |
| `ingest_event(event)` | 事件 JSON | `POST /v1/ingest/events` | 单条事件入库。 |
| `ingest_vectors(vectors, *, segment_id, object_ids)` | 向量行、可选段与 object id | `POST /v1/ingest/vectors` | 向量直灌 warm；常依赖服务端 CGO 检索桥。 |
| `ingest_document(body)` | 长文档 body | `POST /v1/ingest/document` | 长文分块入库。 |
| `query(body)` | QueryRequest 形 body | `POST /v1/query` | 结构化检索。 |

#### 数据集与 warm（部分 admin / internal）

| 方法 | 参数 | 地址 | 描述 |
|------|------|------|------|
| `warm_prebuild()` | 无 | `POST /v1/admin/warm/prebuild` | 触发 warm 预构建。 |
| `dataset_delete(body)` | `workspace_id` 与选择器等 | `POST /v1/admin/dataset/delete` | 按条件软删 memory。 |
| `dataset_purge(body)` | `workspace_id`、选择器、`dry_run` 等 | `POST /v1/admin/dataset/purge` | 硬清匹配 memory（默认仅 inactive）。 |
| `admin_dataset_purge(body)` | 同上 | 同 `dataset_purge` | `dataset_purge` 别名。 |
| `dataset_purge_task(task_id)` | 异步任务 id | `GET /v1/admin/dataset/purge/task?task_id=…` | 查询异步 purge 任务。 |
| `admin_dataset_purge_task(task_id)` | 同上 | 同上 | `dataset_purge_task` 别名。 |
| `warm_segment_register(body)` | `segment_id`、**非空** `object_ids` | `POST /v1/internal/warm-segment/register` | 登记 warm 段 object id。 |

#### 二进制 RPC（`application/octet-stream`）

| 方法 | 参数 | 地址 | 描述 |
|------|------|------|------|
| `rpc_ingest_batch(…)` | `segment_id`, `vectors`, `object_ids?`, `wire_version` | `POST /v1/internal/rpc/ingest_batch` | PLIB 批量灌库。 |
| `rpc_query_warm(…)` | `segment_id`, `top_k`, `vector` | `POST /v1/internal/rpc/query_warm` | PLQW warm 检索。 |
| `rpc_query_warm_batch(…)` | `segment_id`, `top_k`, `queries` | `POST /v1/internal/rpc/query_warm_batch` | PLQB 批量检索。 |
| `rpc_query_warm_batch_raw(…)` | 同上 | `POST /v1/internal/rpc/query_warm_batch_raw` | Raw 检索路径。 |
| `rpc_unload_segment(segment_id)` | 段 id | `POST /v1/internal/rpc/unload_segment` | 卸载 warm 段。 |
| `rpc_register_warm(body)` | JSON body（须含合法 `segment_id` 与 `object_ids`） | `POST /v1/internal/rpc/register_warm` | 登记 warm 元数据。 |

#### Canonical CRUD（同路径 GET 列表 \| POST 写入）

| 方法 | 参数 | 地址 | 描述 |
|------|------|------|------|
| `agents_get` / `agents_post` | `params` / `body` | `GET` / `POST /v1/agents` | Agent 列表与写入。 |
| `sessions_get` / `sessions_post` | `params` / `body` | `GET` / `POST /v1/sessions` | Session。 |
| `memory_get` / `memory_post` | `params` / `body` | `GET` / `POST /v1/memory` | Memory。 |
| `states_get` / `states_post` | `params` / `body` | `GET` / `POST /v1/states` | State。 |
| `artifacts_get` / `artifacts_post` | `params` / `body` | `GET` / `POST /v1/artifacts` | Artifact。 |
| `edges_get` / `edges_post` | `params` / `body` | `GET` / `POST /v1/edges` | Edge。 |
| `policies_get` / `policies_post` | `params` / `body` | `GET` / `POST /v1/policies` | Policy。 |
| `share_contracts_get` / `share_contracts_post` | `params` / `body` | `GET` / `POST /v1/share-contracts` | 共享契约。 |

#### Traces 与 Agent 内存桥

| 方法 | 参数 | 地址 | 描述 |
|------|------|------|------|
| `traces_get(object_id)` | URL 路径编码后的 id | `GET /v1/traces/{object_id}` | 对象证明链 / trace。 |
| `internal_memory_recall` / `ingest` / `compress` / `summarize` / `decay` / `share` / `conflict_resolve` / `stale` / `conflict_inject` | 各 `body` 见网关 | `POST /v1/internal/memory/…` | 算法侧召回、写入、生命周期与冲突实验等。 |

#### Admin（运维）

| 方法 | 参数 | 地址 | 描述 |
|------|------|------|------|
| `admin_topology_get` / `admin_storage_get` / `admin_config_effective_get` | 无 | `GET /v1/admin/topology` 等 | 只读拓扑 / 存储 / 生效配置。 |
| `admin_s3_export` / `admin_s3_snapshot_export` | `body` 可选，`None` 时不发 JSON | `POST /v1/admin/s3/export` 等 | S3 导出（需服务端对象存储配置）。 |
| `admin_s3_cold_purge(body)` | 含 `confirm` 等 | `POST /v1/admin/s3/cold-purge` | 冷层清理。 |
| `admin_data_wipe(body)` | 含 `confirm` 令牌 | `POST /v1/admin/data/wipe` | 破坏性清空（仅联调/运维）。 |
| `admin_rollback` / `admin_replay` | `body` | `POST /v1/admin/rollback` / `replay` | 回滚与 WAL 重放类。 |
| `admin_consistency_mode_get` / `_post` | `body`（post） | `GET` / `POST /v1/admin/consistency-mode` | 一致性模式。 |
| `admin_metrics_get(params)` | 可选 `params` | `GET /v1/admin/metrics` | 指标。 |
| `admin_governance_mode_get` / `_post` | `body`（post） | `GET` / `POST /v1/admin/governance-mode` | 治理模式。 |
| `admin_runtime_mode_get` / `_post` | `body`（post） | `GET` / `POST /v1/admin/runtime-mode` | 运行时模式。 |
| `admin_algorithm_profile_mode_get` / `_post` / `admin_algorithm_profile_health_get` | `body`（post） | `GET` / `POST /v1/admin/memory/providers/…` | 算法 profile 模式与健康。 |

#### Internal（任务 / MAS / 工具 / 评测等）

| 方法 | 参数 | 地址 | 描述 |
|------|------|------|------|
| `internal_task_start` / `complete` / `tokens` / `claim` / `stage` | `body`（`stage` 须含 `agent_id`） | `POST /v1/internal/task/…` | 任务与阶段指标；`stage` 经 ingest 落库。 |
| `internal_plan_step` / `internal_plan_repair` | `body` | `POST /v1/internal/plan/step` / `repair` | 计划步与修复统计。 |
| `internal_mas_answer_consistency` / `internal_mas_aggregate` | `body` | `POST /v1/internal/mas/…` | MAS 相关。 |
| `internal_tool_state_get(params)` | 可选 `params` | `GET /v1/internal/tool-state` | 工具调用状态。 |
| `internal_agent_handoff(body)` | `body` | `POST /v1/internal/agent/handoff` | 角色交接。 |
| `agent_list_get(params)` | 可选 `params` | `GET /v1/agent/list` | Agent 列表过滤。 |
| `internal_session_context_get(params)` | 须含 `session_id` 等 | `GET /v1/internal/session/context` | 会话上下文摘要。 |
| `internal_eval_ground_truth_get` / `_post` | `params` / `body` | `GET` / `POST /v1/internal/eval/ground-truth` | 评测 ground truth。 |
| `debug_echo(body)` | 任意 JSON | `POST /v1/debug/echo` | **仅 test 构建**注册；生产通常无此路由。 |

### 数据助手 `pyplasmod.data`

| 方法 | 参数 | 地址 | 描述 |
|------|------|------|------|
| `upload(dataset, workspace_id, path, *, client?, base_url?, …)` | `.fbin` 路径、`limit`、`show_progress` 等 | 内部多次 `POST /v1/ingest/events` | 按行读向量并发事件入库。 |
| `build_query_body(query_text, workspace_id, **kwargs)` | 查询串、`workspace_id` 及可选过滤关键字 | — | **仅组装 dict**，不发起 HTTP；查询请 `client.query(...)`。 |

### 顶层二进制编解码（`pyplasmod` 导出）

| 符号 | 参数 | 地址 | 描述 |
|------|------|------|------|
| `encode_ingest_batch` / `encode_query_warm` / `encode_query_warm_batch` | 见源码与 Plasmod framing | — | 组 PLIB / PLQW / PLQB 字节流，供 `request_bytes` 或 `rpc_*` 使用。 |
| `decode_query_warm_response` / `decode_query_warm_batch_response` | 响应 `bytes` | — | 解析 warm 检索二进制响应。 |

## 快速用法

```python
from pyplasmod import EasyPlasmod, PlasmodClient

# 对外演示 / 业务接入：仅健康检查、查询、入库、.fbin、列 memory（进阶用 p.http.*）
p = EasyPlasmod()
p.health()

client = PlasmodClient(base_url="http://127.0.0.1:8080")
# 或与 Plasmod 监听端口对齐：export PLASMOD_BASE_URL=http://127.0.0.1:9090 后可用 PlasmodClient()
client.health()
client.ingest_event({"event_id": "e1", "agent_id": "a", "session_id": "s", "event_type": "t", "payload": {}})
client.query({"query_text": "hello", "top_k": 5, "relation_constraints": []})
```

管理接口（`/v1/admin/*`）在设置了环境变量 **`PLASMOD_ADMIN_API_KEY`** 或 **`ANDB_ADMIN_API_KEY`**（或构造参数 **`admin_key`**）时自动附加 **`X-Admin-Key`**。

二进制 RPC 与帧工具可从子模块导入：

```python
from pyplasmod.http import encode_ingest_batch, PlasmodHttpClient
```

详见 `examples/http_quickstart.py`。

**一行写入数据.fbin（推荐）** — 包内 API 或模块 CLI：

```python
from pyplasmod.data import upload
upload("my_dataset", "w_demo", "/path/to/file.fbin", show_progress=True)
```

```bash
python -m pyplasmod.data upload my_dataset w_demo /path/to/file.fbin --show-progress
python -m pyplasmod.data query "hello" w_demo
# 两参数等价于 query：
python -m pyplasmod.data "hello" w_demo
```

查询（Python）：

```python
from pyplasmod import PlasmodClient
from pyplasmod.data import build_query_body

PlasmodClient().query(build_query_body("test", "w_demo"))
```

（`examples/ingest_fbin.py` 仅为薄封装示例。）

## 异常

- **`PlasmodHttpError`**：HTTP 非成功响应（含 **`status_code`**、**`body`**、**`path`**）。
- **`ConnectError`**：连接级失败（由客户端在收到响应前抛出）。
- **`PlasmodException`**：其它 SDK 基类。

## 许可证

Apache 2.0（见仓库根目录 `LICENSE`）。
