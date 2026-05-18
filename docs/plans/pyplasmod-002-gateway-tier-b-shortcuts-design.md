# pyplasmod Tier B HTTP shortcut methods

| Metadata | Value |
|----------|-------|
| **Document ID** | pyplasmod-002 |
| **Status** | Implemented |
| **Created** | 2026-05-08 |
| **Updated** | 2026-05-18 |
| **Maintainer** | [CodeSoul-co](https://github.com/CodeSoul-co) |
| **Audience** | Integrators calling Plasmod extended JSON APIs |
| **Prerequisites** | [pyplasmod-001-http-sdk-design.md](pyplasmod-001-http-sdk-design.md) |

> **Day-to-day ingest and retrieval:** prefer `EasyPlasmod` and `pyplasmod.data` in [README.md](../../README.md).  
> **Tier B** covers **extended** operations: ops, multi-agent internal protocols, evaluation, and debugging.

---

## 1. Overview

The Plasmod gateway registers many JSON routes in [`Gateway.RegisterRoutes`](https://github.com/CodeSoul-co/Plasmod/blob/main/src/internal/access/gateway.go). **Tier A** (see 001) covers ingest/query, core admin, canonical CRUD, parts of the internal memory bridge, and binary RPC.

**Tier B** refers to remaining JSON routes not listed as “core paths” in Tier A. pyplasmod exposes a **named method on `PlasmodHttpClient`** for each route so callers avoid hand-writing `request_json("POST", "/v1/...")` and gain IDE discoverability.

All Tier B methods are **thin wrappers over `request_json`**: no extra business logic, no change to request semantics.

---

## 2. Tier A vs Tier B

| Dimension | Tier A | Tier B |
|-----------|--------|--------|
| **Typical use** | Ingest, retrieval, Memory listing, dataset ops, warm RPC | Admin config reads, S3 ops, internal task/MAS, agent list, eval, debug |
| **Recommended entry** | `EasyPlasmod` + `pyplasmod.data` | `PlasmodClient` / `EasyPlasmod.http` |
| **Documentation focus** | [README.md](../../README.md), [SDK.md](../SDK.md) §5–7 | This document §4 route index |
| **Testing** | Unit tests + example scripts | `tests/test_http_sdk.py` route smoke tests |

---

## 3. Design principles

### 3.1 Naming rules

| Route type | Python method naming | Example |
|------------|---------------------|---------|
| Admin read | `admin_{resource}_get` | `admin_topology_get` |
| Admin write | `admin_{resource}_post` | `admin_consistency_mode_post` |
| Internal | `internal_{area}_{verb}` | `internal_task_start` |
| Special list | Match URL semantics | `agent_list_get` → `GET /v1/agent/list` (not `/v1/agents` CRUD) |

### 3.2 HTTP verbs

Match gateway handlers: for resources with both GET and POST (e.g. `governance_mode`, `runtime_mode`, `consistency_mode`, `algorithm_profile_mode`), provide separate `*_get` and `*_post` methods.

### 3.3 Request bodies

- Required fields and enum values follow **Plasmod `docs/api` and `gateway.go`**.
- `admin_s3_export` and `admin_s3_snapshot_export` allow `body=None`; when the server accepts empty JSON, the client sends a POST with no body.

### 3.4 Authentication

Currently only **`/v1/admin/*`** automatically attaches `X-Admin-Key` when `admin_key` is configured. Internal routes do not attach it by default; if the gateway later requires internal auth, **explicitly extend** `_admin_headers` in `client.py` — do not guess implicitly.

---

## 4. Tier B method index

All methods are defined in `pyplasmod/http/client.py` (comment block: `Tier B: remaining Gateway.RegisterRoutes JSON surfaces`). Paths are relative to the gateway base URL.

### 4.1 Extended Admin (read / config / operations)

| Method | HTTP | Description |
|--------|------|-------------|
| `admin_topology_get` | `GET /v1/admin/topology` | Topology information |
| `admin_storage_get` | `GET /v1/admin/storage` | Storage backend configuration |
| `admin_config_effective_get` | `GET /v1/admin/config/effective` | Effective configuration snapshot |
| `admin_s3_export` | `POST /v1/admin/s3/export` | S3 export (optional body) |
| `admin_s3_snapshot_export` | `POST /v1/admin/s3/snapshot-export` | Snapshot export (optional body) |
| `admin_s3_cold_purge` | `POST /v1/admin/s3/cold-purge` | Cold-tier purge |
| `admin_data_wipe` | `POST /v1/admin/data/wipe` | **High risk:** data wipe |
| `admin_rollback` | `POST /v1/admin/rollback` | Rollback |
| `admin_replay` | `POST /v1/admin/replay` | Replay |
| `admin_consistency_mode_get` / `_post` | `GET/POST /v1/admin/consistency-mode` | Consistency mode |
| `admin_metrics_get` | `GET /v1/admin/metrics` | Metrics |
| `admin_governance_mode_get` / `_post` | `GET/POST /v1/admin/governance-mode` | Governance mode |
| `admin_runtime_mode_get` / `_post` | `GET/POST /v1/admin/runtime-mode` | Runtime mode |
| `admin_algorithm_profile_mode_get` / `_post` | `GET/POST /v1/admin/algorithm-profile-mode` | Algorithm profile mode |
| `admin_algorithm_profile_health_get` | `GET /v1/admin/algorithm-profile/health` | Algorithm profile health |

> **Note:** Common admin operations such as `dataset_delete`, `dataset_purge`, and `warm_prebuild` are exposed in Tier A — see [README.md §5](../../README.md) and the [003 usage guide](pyplasmod-003-sdk-usage-guide.md).

### 4.2 Internal — task / plan / multi-agent

| Method | HTTP |
|--------|------|
| `internal_task_start` | `POST /v1/internal/task/start` |
| `internal_task_complete` | `POST /v1/internal/task/complete` |
| `internal_task_tokens` | `POST /v1/internal/task/tokens` |
| `internal_task_claim` | `POST /v1/internal/task/claim` |
| `internal_task_stage` | `POST /v1/internal/task/stage` |
| `internal_plan_step` | `POST /v1/internal/plan/step` |
| `internal_plan_repair` | `POST /v1/internal/plan/repair` |
| `internal_mas_answer_consistency` | `POST /v1/internal/mas/answer-consistency` |
| `internal_mas_aggregate` | `POST /v1/internal/mas/aggregate` |

### 4.3 Internal — other

| Method | HTTP | Notes |
|--------|------|-------|
| `internal_tool_state_get` | `POST /v1/internal/tool/state` | |
| `internal_agent_handoff` | `POST /v1/internal/agent/handoff` | |
| `internal_session_context_get` | `GET /v1/internal/session/context` | **`params` required** (includes `session_id`, etc.) |
| `internal_eval_ground_truth_get` | `GET /v1/internal/eval/ground-truth` | |
| `internal_eval_ground_truth_post` | `POST /v1/internal/eval/ground-truth` | |
| `agent_list_get` | `GET /v1/agent/list` | Optional query: `role`, `workspace_id`, `tenant_id` |
| `debug_echo` | `POST /v1/debug/echo` | Registered only when gateway is in **test** mode |

### 4.4 Tier A coverage easily confused with Tier B

| Method | Notes |
|--------|-------|
| `internal_memory_*` | `/v1/internal/memory/*` algorithm bridge — distinct from `/v1/memory` CRUD |
| `memory_get` / `memory_post` | Canonical Memory CRUD |
| `agents_get` / `agents_post`, etc. | `/v1/agents` resource CRUD — distinct from `agent_list_get` |

---

## 5. Usage examples

### 5.1 Read Admin topology (when Admin key is required)

```python
import os
from pyplasmod import PlasmodClient

with PlasmodClient(
    base_url=os.environ.get("PLASMOD_BASE_URL", "http://127.0.0.1:8080"),
    admin_key=os.environ.get("PLASMOD_ADMIN_API_KEY", ""),
) as client:
    print(client.admin_topology_get())
```

The repository example `examples/http_quickstart.py` calls `admin_topology_get` when `PLASMOD_QUICKSTART_ADMIN=1` and `PLASMOD_ADMIN_API_KEY` are set.

### 5.2 Internal task staging (fields per gateway contract)

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

### 5.3 Session context

```python
client.internal_session_context_get(
    {"session_id": "sess_demo", "agent_id": "agent_demo", "last_n": 10}
)
```

---

## 6. Non-goals and limitations

- **No** request/response dataclasses or OpenAPI codegen for Tier B.
- **No** full per-field body schemas in this document (see Plasmod official API docs).
- **No** WAL SSE here (`iter_wal_stream_events` is Tier A transport — see [SDK.md](../SDK.md)).
- If a local `gateway.go` copy differs from the deployed gateway, **the running deployment** is authoritative for registered routes.

---

## 7. Quality assurance

| Item | Location |
|------|----------|
| Route and header smoke tests | `tests/test_http_sdk.py` |
| Optional live admin call | `examples/http_quickstart.py` |
| End-to-end reference | `examples/test.py` (includes Tier B and internal fragments) |

---

## 8. Related documentation

| Document | Description |
|----------|-------------|
| [pyplasmod-001-http-sdk-design.md](pyplasmod-001-http-sdk-design.md) | Overall architecture and tier definitions |
| [pyplasmod-003-sdk-usage-guide.md](pyplasmod-003-sdk-usage-guide.md) | Parameters, troubleshooting, Tier B call notes |
| [docs/SDK.md](../SDK.md) | Full method list (including Tier A) |
| [Plasmod gateway.go](https://github.com/CodeSoul-co/Plasmod/blob/main/src/internal/access/gateway.go) | Authoritative route registry |

---

## 9. Revision history

| Date | Notes |
|------|-------|
| 2026-05-08 | Initial version: Tier B naming rules and implementation notes |
| 2026-05-09 | Added test and quickstart references |
| 2026-05-18 | Public documentation pass: full Tier B route index, README scope split |
