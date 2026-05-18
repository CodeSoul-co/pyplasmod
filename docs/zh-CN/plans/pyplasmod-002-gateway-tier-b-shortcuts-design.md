# pyplasmod Tier B HTTP 快捷方法说明

| 元数据 | 值 |
|--------|-----|
| **文档编号** | pyplasmod-002 |
| **状态** | 已实现 |
| **创建** | 2026-05-08 |
| **更新** | 2026-05-18 |
| **维护方** | [CodeSoul-co](https://github.com/CodeSoul-co) |
| **读者** | 需要调用 Plasmod 扩展 JSON API 的集成开发者 |
| **前置阅读** | [pyplasmod-001-http-sdk-design.md](pyplasmod-001-http-sdk-design.md) |

> **日常入库与检索**请优先使用 [README.md](../../README.md) 中的 `EasyPlasmod` 与 `pyplasmod.data`。  
> **Tier B** 面向运维、多智能体内部协议、评测与调试等**扩展能力**。

---

## 1. 概述

Plasmod 网关在 [`Gateway.RegisterRoutes`](https://github.com/CodeSoul-co/Plasmod/blob/main/src/internal/access/gateway.go) 中注册大量 JSON 路由。**Tier A**（见 001）覆盖 ingest/query、核心 admin、canonical CRUD、部分 internal memory 桥与二进制 RPC。

**Tier B** 指其余仍通过 JSON 访问、但在 Tier A 中未单独列为「核心路径」的路由。pyplasmod 为每条路由提供 **`PlasmodHttpClient` 上的具名方法**，避免调用方手写 `request_json("POST", "/v1/...")` 并改善 IDE 可发现性。

所有 Tier B 方法均为 **`request_json` 的薄封装**：不引入额外业务逻辑，不改变请求语义。

---

## 2. Tier A 与 Tier B 划分

| 维度 | Tier A | Tier B |
|------|--------|--------|
| **典型用途** | 入库、检索、Memory 列表、数据集运维、warm RPC | Admin 读配置、S3 运维、internal task/MAS、agent list、评测、调试 |
| **推荐入口** | `EasyPlasmod` + `pyplasmod.data` | `PlasmodClient` / `EasyPlasmod.http` |
| **文档侧重** | [README.md](../../README.md)、[SDK.md](../SDK.md) §5–7 | 本文 §4 路由索引 |
| **测试** | 单元测试 + 示例脚本 | `tests/test_http_sdk.py` 路由烟测 |

---

## 3. 设计原则

### 3.1 命名规则

| 路由类型 | Python 方法命名 | 示例 |
|----------|-----------------|------|
| Admin 读 | `admin_{resource}_get` | `admin_topology_get` |
| Admin 写 | `admin_{resource}_post` | `admin_consistency_mode_post` |
| Internal | `internal_{area}_{verb}` | `internal_task_start` |
| 特殊列表 | 与 URL 语义一致 | `agent_list_get` → `GET /v1/agent/list`（非 `/v1/agents` CRUD） |

### 3.2 HTTP 动词

与网关 handler 一致：对同时提供 GET/POST 的资源（如 `governance_mode`、`runtime_mode`、`consistency_mode`、`algorithm_profile_mode`），分别提供 `*_get` 与 `*_post`。

### 3.3 请求体

- 必填字段、枚举取值以 **Plasmod `docs/api` 与 `gateway.go`** 为准。
- `admin_s3_export`、`admin_s3_snapshot_export` 允许 `body=None`，在服务端接受空 JSON 时发送无 body POST。

### 3.4 鉴权

当前仅 **`/v1/admin/*`** 在配置 `admin_key` 时自动附加 `X-Admin-Key`。Internal 路由默认不附加；若未来网关要求 internal 鉴权，须在 `client.py` 中**显式扩展** `_admin_headers`，而非隐式猜测。

---

## 4. Tier B 方法索引

下列方法均定义于 `pyplasmod/http/client.py`（注释区块：`Tier B: remaining Gateway.RegisterRoutes JSON surfaces`）。路径为相对网关根 URL 的路径。

### 4.1 Admin 扩展（读 / 配置 / 运维）

| 方法 | HTTP | 说明 |
|------|------|------|
| `admin_topology_get` | `GET /v1/admin/topology` | 拓扑信息 |
| `admin_storage_get` | `GET /v1/admin/storage` | 存储后端配置 |
| `admin_config_effective_get` | `GET /v1/admin/config/effective` | 有效配置快照 |
| `admin_s3_export` | `POST /v1/admin/s3/export` | S3 导出（body 可选） |
| `admin_s3_snapshot_export` | `POST /v1/admin/s3/snapshot-export` | 快照导出（body 可选） |
| `admin_s3_cold_purge` | `POST /v1/admin/s3/cold-purge` | 冷层清理 |
| `admin_data_wipe` | `POST /v1/admin/data/wipe` | **高危**：数据擦除 |
| `admin_rollback` | `POST /v1/admin/rollback` | 回滚 |
| `admin_replay` | `POST /v1/admin/replay` | 重放 |
| `admin_consistency_mode_get` / `_post` | `GET/POST /v1/admin/consistency-mode` | 一致性模式 |
| `admin_metrics_get` | `GET /v1/admin/metrics` | 指标 |
| `admin_governance_mode_get` / `_post` | `GET/POST /v1/admin/governance-mode` | 治理模式 |
| `admin_runtime_mode_get` / `_post` | `GET/POST /v1/admin/runtime-mode` | 运行时模式 |
| `admin_algorithm_profile_mode_get` / `_post` | `GET/POST /v1/admin/algorithm-profile-mode` | 算法 profile 模式 |
| `admin_algorithm_profile_health_get` | `GET /v1/admin/algorithm-profile/health` | 算法 profile 健康 |

> **说明**：`dataset_delete`、`dataset_purge`、`warm_prebuild` 等常用 admin 能力在 Tier A 中已暴露，见 [README.md §5](../../README.md) 与 [003 使用指南](pyplasmod-003-sdk-usage-guide.md)。

### 4.2 Internal — 任务 / 计划 / 多智能体

| 方法 | HTTP |
|------|------|
| `internal_task_start` | `POST /v1/internal/task/start` |
| `internal_task_complete` | `POST /v1/internal/task/complete` |
| `internal_task_tokens` | `POST /v1/internal/task/tokens` |
| `internal_task_claim` | `POST /v1/internal/task/claim` |
| `internal_task_stage` | `POST /v1/internal/task/stage` |
| `internal_plan_step` | `POST /v1/internal/plan/step` |
| `internal_plan_repair` | `POST /v1/internal/plan/repair` |
| `internal_mas_answer_consistency` | `POST /v1/internal/mas/answer-consistency` |
| `internal_mas_aggregate` | `POST /v1/internal/mas/aggregate` |

### 4.3 Internal — 其它

| 方法 | HTTP | 备注 |
|------|------|------|
| `internal_tool_state_get` | `POST /v1/internal/tool/state` | |
| `internal_agent_handoff` | `POST /v1/internal/agent/handoff` | |
| `internal_session_context_get` | `GET /v1/internal/session/context` | **`params` 必填**（含 `session_id` 等） |
| `internal_eval_ground_truth_get` | `GET /v1/internal/eval/ground-truth` | |
| `internal_eval_ground_truth_post` | `POST /v1/internal/eval/ground-truth` | |
| `agent_list_get` | `GET /v1/agent/list` | 可选 query：`role`、`workspace_id`、`tenant_id` |
| `debug_echo` | `POST /v1/debug/echo` | 仅网关 **test 模式**可能注册 |

### 4.4 Tier A 中已覆盖、易与 Tier B 混淆的接口

| 方法 | 说明 |
|------|------|
| `internal_memory_*` | `/v1/internal/memory/*` 算法桥，与 `/v1/memory` CRUD 不同 |
| `memory_get` / `memory_post` | Canonical Memory CRUD |
| `agents_get` / `agents_post` 等 | `/v1/agents` 等资源 CRUD，与 `agent_list_get` 不同 |

---

## 5. 使用示例

### 5.1 读取 Admin 拓扑（需 Admin Key 时）

```python
import os
from pyplasmod import PlasmodClient

with PlasmodClient(
    base_url=os.environ.get("PLASMOD_BASE_URL", "http://127.0.0.1:8080"),
    admin_key=os.environ.get("PLASMOD_ADMIN_API_KEY", ""),
) as client:
    print(client.admin_topology_get())
```

仓库示例 `examples/http_quickstart.py` 在设置 `PLASMOD_QUICKSTART_ADMIN=1` 且配置 `PLASMOD_ADMIN_API_KEY` 时会调用 `admin_topology_get`。

### 5.2 Internal 任务阶段（字段以网关为准）

```python
from pyplasmod import PlasmodClient

session_id = "sess_demo"
agent_id = "agent_demo"

with PlasmodClient() as client:
    client.internal_task_start(
        {
            "session_id": session_id,
            "task_type": "demo",
            "goal": "smoke test",
            "agent_id": agent_id,
        }
    )
    client.internal_task_stage(
        {
            "session_id": session_id,
            "agent_id": agent_id,
            "stage": "outline",
            "stage_index": 0,
            "total_stages": 1,
            "description": "step 0",
        }
    )
```

### 5.3 会话上下文

```python
client.internal_session_context_get(
    {"session_id": "sess_demo", "agent_id": "agent_demo", "last_n": 10}
)
```

---

## 6. 非目标与限制

- **不**为 Tier B 引入请求/响应 dataclass 或 OpenAPI 代码生成。
- **不**在本文维护每个 body 字段的完整 schema（以 Plasmod 官方 API 文档为准）。
- **不**包含 WAL SSE（`iter_wal_stream_events` 在 Tier A 传输层实现，见 [SDK.md](../SDK.md)）。
- 本地 `gateway.go` 副本若与运行中网关版本不一致，以**实际部署**注册的路由为准。

---

## 7. 质量保障

| 项 | 位置 |
|----|------|
| 路由与 header 烟测 | `tests/test_http_sdk.py` |
| 可选 live admin 调用 | `examples/http_quickstart.py` |
| 综合联调参考 | `examples/test.py`（含 Tier B 与 internal 片段） |

---

## 8. 相关文档

| 文档 | 说明 |
|------|------|
| [pyplasmod-001-http-sdk-design.md](pyplasmod-001-http-sdk-design.md) | 总体架构与 Tier 定义 |
| [pyplasmod-003-sdk-usage-guide.md](pyplasmod-003-sdk-usage-guide.md) | 参数、排错与 Tier B 调用注意 |
| [docs/SDK.md](../SDK.md) | 全量方法列表（含 Tier A） |
| [Plasmod gateway.go](https://github.com/CodeSoul-co/Plasmod/blob/main/src/internal/access/gateway.go) | 路由权威注册表 |

---

## 9. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-05-08 | 首版：Tier B 命名规则与实现说明 |
| 2026-05-09 | 补充测试与 quickstart 引用 |
| 2026-05-18 | 对外规范化：完整 Tier B 路由索引表、与 README 分工说明 |
