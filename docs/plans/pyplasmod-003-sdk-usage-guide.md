# pyplasmod SDK usage guide

| Metadata | Value |
|----------|-------|
| **Document ID** | pyplasmod-003 |
| **Status** | Current release |
| **Created** | 2026-05-06 |
| **Updated** | 2026-05-18 |
| **Maintainer** | [CodeSoul-co](https://github.com/CodeSoul-co) |
| **Audience** | Application developers integrating Plasmod via pyplasmod |

> **First-time users** — recommended reading order:  
> 1. [README.md](../../README.md) — install, start the gateway, 5-minute quick start  
> 2. This guide — parameter meanings, recommended values, copy-paste examples  
> 3. [docs/SDK.md](../SDK.md) — architecture and full API index  
>  
> Architecture background: [pyplasmod-001-http-sdk-design.md](pyplasmod-001-http-sdk-design.md)  
> Tier B extended APIs: [pyplasmod-002-gateway-tier-b-shortcuts-design.md](pyplasmod-002-gateway-tier-b-shortcuts-design.md)

**Server contract:** JSON fields and routes follow the [Plasmod HTTP API](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api); this guide matches the current `pyplasmod` codebase.

---

## 1. Installation and prerequisites

### 1.1 Install the client

```bash
pip install pyplasmod
```

Optional LangChain integration:

```bash
pip install pyplasmod[langchain]
```

Development install from source:

```bash
pip install -e ".[dev]"
make unittest
```

### 1.2 Runtime prerequisites

| Requirement | Notes |
|-------------|-------|
| Python | 3.8 or newer |
| Plasmod gateway | Running and reachable (default `http://127.0.0.1:8080`) |
| Network | `curl $PLASMOD_BASE_URL/healthz` succeeds |

The gateway is **not** bundled in pyplasmod. Start options (`make dev`, Docker Compose, etc.) are in [README.md — Start the Plasmod gateway](../../README.md#start-the-plasmod-gateway).

### 1.3 In-package help

```python
from pyplasmod import plasmod_help, plasmod_topics

plasmod_help()           # topic index
plasmod_help("easy")     # EasyPlasmod details
plasmod_help("env")      # environment variables
```

Command line: `python -m pyplasmod [topic]`. Full signatures: `help(EasyPlasmod)`, etc.

---

## 2. Environment variables

| Variable | Purpose |
|----------|---------|
| `PLASMOD_BASE_URL` / `ANDB_BASE_URL` | HTTP root URL; default `http://127.0.0.1:8080` |
| `PLASMOD_HTTP_TIMEOUT` / `ANDB_HTTP_TIMEOUT` | Timeout in seconds; default `30` |
| `PLASMOD_ADMIN_API_KEY` / `ANDB_ADMIN_API_KEY` | Sets `X-Admin-Key` for `/v1/admin/*` |

Constructor arguments `base_url`, `timeout`, and `admin_key` **override** environment variables.  
Copy [`.env.example`](../../.env.example) to `.env` for local tooling (pyplasmod reads `os.environ` directly and does not require dotenv).

---

## 3. Choosing a client entry point

| Entry | Use when |
|-------|----------|
| **`EasyPlasmod`** | Health checks, text search, `ingest_document`, `.fbin` upload, `memories` |
| **`PlasmodClient`** (= `PlasmodHttpClient`) | Admin, binary RPC, `ingest_vectors`, Tier B internal, WAL SSE |
| **`pyplasmod.data`** | `build_query_body`, `upload` (pass `client=` to reuse connections) |
| **`PlasmodVectorStore`** | LangChain (optional extra) |

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
    p.health()
    p.http.dataset_delete({...})  # full API via .http
```

### 3.1 Core concepts

| Concept | Description |
|---------|-------------|
| `workspace_id` | Workspace isolation key; usually required for ingest and query (e.g. `w_demo`) |
| `dataset_name` | Logical dataset; pairs with `upload(..., dataset=...)` |
| `session_id` / `agent_id` | Session and agent; **must match between ingest and query** |
| Memory | Materialized gateway memory; `p.memories(workspace_id)` lists rows |

---

## 4. Data ingest

### 4.1 Long text and documents — `ingest_document`

The gateway **chunks** `text` into multiple memory events automatically; the client does not split sentences.

**Required / strongly recommended fields**

| Field | Description |
|-------|-------------|
| `text` | Body (required) |
| `workspace_id` | Workspace |
| `agent_id` | Agent ID |
| `session_id` | Session ID (reuse at query time) |
| `title` | Document title (recommended) |

**Optional:** `chunk_size`, `overlap`, `importance`, etc. (semantics per gateway).

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
                "text": "Content to ingest.",
                "workspace_id": workspace,
                "agent_id": agent_id,
                "session_id": session_id,
                "title": "Example document",
                "chunk_size": 500,
                "overlap": 50,
            }
        )
    )
    print(
        p.query(
            build_query_body(
                "What is this document about?",
                workspace,
                session_id=session_id,
                agent_id=agent_id,
                top_k=5,
            )
        )
    )
```

**From a file:**

```python
from pathlib import Path

text = Path("/path/to/manual.md").read_text(encoding="utf-8")
# Put text in ingest_document's "text" field; title can be path.name
```

### 4.2 Single short text — `ingest_event`

For one structured event, custom `payload`, or an attached `embedding_vector`.

```python
with EasyPlasmod() as p:
    p.ingest_event(
        {
            "event_id": "evt_unique_001",
            "workspace_id": "w_demo",
            "agent_id": "pyplasmod_data",
            "session_id": "notes_session",
            "event_type": "observation",
            "payload": {"text": "A note"},
            "source": "my_application",
            "version": 1,
        }
    )
```

For multiple events, loop calls or use `p.http.ingest_events(events, batch_size=...)`.

### 4.3 Vector files — `upload` / `upload_fbin`

`.fbin` format: 8-byte header (`uint32` row count + `uint32` dimension) + little-endian `float32` per row.

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

Command line:

```bash
python -m pyplasmod.data upload my_dataset w_demo /path/to/vectors.fbin --show-progress
```

### 4.4 JSON vectors and binary batch

| Method | When to use |
|--------|-------------|
| `client.ingest_vectors([[...], ...])` | Medium-sized JSON matrices; **warm ANN index type** (`index_type`, IVF fields) |
| `client.ingest_batch(segment_id, vectors, batch_size=500)` | Large scale; internal PLIB RPC with automatic chunking (**no `index_type`**) |
| `client.rpc_ingest_batch(...)` | Low-level RPC; you control batching |

Vector dimension must match gateway warm segment / embedder configuration.

**Warm segment ANN index** (build-time, `POST /v1/ingest/vectors` only):

| `index_type` | Notes |
|--------------|-------|
| `HNSW` | Default when omitted |
| `IVF_FLAT` / `IVF_PQ` / `IVF_SQ8` | Optional `ivf_nlist`, `ivf_nprobe`, `ivf_m`, `ivf_nbits`, `ivf_sq_type` |
| `DISKANN` | Disk-oriented large scale |

```python
from pyplasmod import PlasmodClient, WARM_INDEX_IVF_FLAT

with PlasmodClient() as c:
    c.ingest_vectors(
        [[0.1, 0.2, ...]],
        segment_id="demo.ivf",
        index_type=WARM_INDEX_IVF_FLAT,
        ivf_nlist=128,
        ivf_nprobe=32,
    )
```

Use the same `segment_id` (or `warm_segment_id` in queries) that was built with that index. For non-default indexes at very large scale, prefer repeated `ingest_vectors` calls until PLIB ingest supports index metadata. Details: [SDK.md](../SDK.md) §10.

### 4.5 Gateway embedding and CPU / GPU — `PlasmodEmbedding`

Plasmod has **no** `/v1/embed`; plain text is embedded server-side via ONNX / GGUF / TF-IDF, etc. Recommended entry:

```python
from pyplasmod import PlasmodEmbedding, EasyPlasmod

# Standalone facade
with PlasmodEmbedding.connect() as emb:
    print(emb.capabilities())
    emb.ingest("text to ingest", workspace_id="w_demo")
    print(emb.search("query terms", workspace_id="w_demo", top_k=5))
    print(emb.runtime())

# Or on EasyPlasmod
with EasyPlasmod() as p:
    p.embed_ingest("text to ingest", workspace_id="w_demo")
    print(p.embed_search("query terms", workspace_id="w_demo"))
```

**Before starting Plasmod**, configure CPU or GPU (`PLASMOD_EMBEDDER*`):

```python
emb = PlasmodEmbedding.connect()
emb.use_onnx_cpu(model_path="/models/model.onnx", dim=384, apply=True)
# emb.use_onnx_gpu(model_path="/models/model.onnx", dim=384, apply=True)
```

See **[docs/EMBEDDING.md](../EMBEDDING.md)** (recommended entry and CPU/GPU presets) and [docs/SDK.md](../SDK.md) (module index when available).

---

## 5. Query and retrieval

### 5.1 Simple search — `search`

```python
with EasyPlasmod() as p:
    r = p.search("example question", "w_demo", top_k=10)
```

Internally: `build_query_body` then `POST /v1/query`.

### 5.2 Explicit request body — `build_query_body` + `query`

| Parameter | Description |
|-----------|-------------|
| `query_text` | Query string |
| `embedding_vector` | Optional; skips gateway embedder when set |
| `workspace_id` | Workspace; also written to `query_scope` |
| `session_id` | If empty: when both `dataset_name` and `ingest_fbin_path` are set → `ingest_{dataset}_{filename}`; else `query_{workspace_id}` |
| `agent_id` | Default `pyplasmod_data`; must match ingest |
| `dataset_name` | Filter by dataset |
| `ingest_fbin_path` | Used only to derive default `session_id` |
| `extra` | Merge to override any field |

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

Response shape varies by server version; common keys include `objects`, `hits`.

### 5.3 List Memory

```python
rows = p.memories("w_demo", limit=100)
```

Equivalent to `GET /v1/memory` with `workspace_id` query parameter.

---

## 6. `PlasmodHttpClient` reference

### 6.1 Construction

```python
from pyplasmod import PlasmodHttpClient, PlasmodHttpError

client = PlasmodHttpClient(
    base_url=None,      # env → http://127.0.0.1:8080
    timeout=None,
    admin_key=None,
    session=None,       # optional requests.Session reuse
)

with PlasmodHttpClient() as c:
    ...
```

### 6.2 Generic methods

| Method | Description |
|--------|-------------|
| `request_json(method, path, *, json_body=..., params=..., headers=...)` | Any JSON API |
| `request_bytes(method, path, *, data=..., headers=...)` | Binary body; returns `(status, bytes, headers)` |

### 6.3 Tier A JSON shortcuts (common)

| Method | HTTP |
|--------|------|
| `health()` | `GET /healthz` |
| `system_mode()` | `GET /v1/system/mode` |
| `ingest_event(event)` | `POST /v1/ingest/events` |
| `ingest_vectors(vectors, *, segment_id=..., object_ids=..., index_type=..., ivf_*=...)` | `POST /v1/ingest/vectors` |
| `ingest_document(body)` | `POST /v1/ingest/document` |
| `query(body)` | `POST /v1/query` |
| `query_batch(body)` | `POST /v1/query/batch` |
| `memory_get(params)` / `memory_post(body)` | `GET/POST /v1/memory` |
| `dataset_delete(body)` | `POST /v1/admin/dataset/delete` |
| `dataset_purge(body)` | `POST /v1/admin/dataset/purge` |
| `dataset_purge_task(task_id)` | `GET /v1/admin/dataset/purge/task` |
| `warm_prebuild()` | `POST /v1/admin/warm/prebuild` |
| `warm_segment_register(body)` | `POST /v1/internal/warm-segment/register` |

### 6.4 Binary RPC

| Method | Description |
|--------|-------------|
| `rpc_ingest_batch(segment_id, vectors, object_ids=None, wire_version=1\|2)` | PLIB batch ingest |
| `rpc_query_warm(segment_id, top_k, vector)` | PLQW single-vector search |
| `rpc_query_warm_batch` / `rpc_query_warm_batch_raw` | PLQB batch search |
| `rpc_unload_segment` / `rpc_register_warm` | Segment unload / register |

Non-200 responses raise `PlasmodHttpError`. Prefer `rpc_*` over manual `encode_*` in most cases.

### 6.5 Canonical CRUD and internal memory

- CRUD: `agents_get/post`, `sessions_get/post`, `states_get/post`, `artifacts_get/post`, `edges_get/post`, `policies_get/post`, `share_contracts_get/post`
- Tracing: `traces_get(object_id)`
- Algorithm bridge: `internal_memory_recall`, `internal_memory_ingest`, etc. (`/v1/internal/memory/*` — **not** `/v1/memory` CRUD)

### 6.6 Tier B

Extended Admin, internal task/MAS, `agent_list_get`, `internal_session_context_get`, `debug_echo`, etc. — see [pyplasmod-002](pyplasmod-002-gateway-tier-b-shortcuts-design.md) §4.

**Dataset purge example** (use `dry_run` first):

```python
p.http.dataset_purge(
    {"workspace_id": "w_demo", "dataset_name": "my_dataset", "dry_run": True}
)
```

---

## 7. `EasyPlasmod` method summary

| Method | Behavior |
|--------|----------|
| `health()` / `system_mode()` | Same as `http.*` |
| `query(body)` | `POST /v1/query` |
| `search(query_text, workspace_id, **kwargs)` | `build_query_body` + `query` |
| `ingest_event` / `ingest_document` | Same as `http.*` |
| `upload_fbin(dataset, workspace_id, path, **kwargs)` | `data.upload(..., client=self.http)` |
| `memories(workspace_id, **params)` | `GET /v1/memory` |
| `http` | Full `PlasmodHttpClient` |

---

## 8. Error handling and troubleshooting

### 8.1 Catching HTTP errors

```python
from pyplasmod import PlasmodClient, PlasmodHttpError

try:
    PlasmodClient().query({"query_text": "x", "workspace_id": "w_demo"})
except PlasmodHttpError as e:
    print(e.status_code, e.path, (e.body or "")[:500])
```

| Attribute | Meaning |
|-----------|---------|
| `status_code` | HTTP status; often `0` on connection failure |
| `path` | Request path |
| `body` | Response body text |

### 8.2 Common issues

| Symptom | Likely cause | Suggestion |
|---------|--------------|------------|
| `status_code=0`, connection error | Gateway down or wrong URL/port | Check `PLASMOD_BASE_URL`, `curl .../healthz` |
| 401/403 on `/v1/admin/*` | Missing Admin key | Set `PLASMOD_ADMIN_API_KEY` or `admin_key=` |
| No query hits | `session_id` / `agent_id` mismatch vs ingest | Align ingest and `build_query_body` |
| Vector ingest failure | Dimension mismatch | Confirm `.fbin` dim and embedder config |
| Nothing after `ingest_document` | Missing same `session_id` at query | Pass ingest `session_id` in query body |
| RPC warm failure | Segment not registered or wrong dim | Check `warm_segment_register` and `segment_id` |

---

## 9. Examples and further reading

| Resource | Description |
|----------|-------------|
| [README.md](../../README.md) | Quick start, scenario examples |
| [docs/SDK.md](../SDK.md) | Architecture, implementation, API index |
| `examples/http_quickstart.py` | Minimal HTTP example |
| `examples/ingest_fbin.py` | `.fbin` ingest |
| `examples/batch_ingest.py` | Batch vectors |
| `examples/langchain_quickstart.py` | LangChain |
| `examples/test.py` | End-to-end (ingest, query, admin, Tier B) |
| [Plasmod docs/api](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api) | Authoritative server API |

---

## 10. Revision history

| Date | Notes |
|------|-------|
| 2026-05-06 | Initial version: parameters, Tier A/B, EasyPlasmod, data, error handling |
| 2026-05-18 | Public documentation pass: README ingest alignment, gateway prerequisites, troubleshooting table, cross-links |
