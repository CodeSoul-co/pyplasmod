# pyplasmod

> **[中文](https://github.com/CodeSoul-co/pyplasmod/blob/main/README.zh-CN.md)** 

**pyplasmod** is a Python **HTTP client library** for **[Plasmod](https://github.com/CodeSoul-co/Plasmod)**: it talks to a deployed Plasmod gateway over standard HTTP (and some binary RPC) for vector ingest, search, Memory listing, dataset operations, and health checks.

**Plasmod** targets multi-agent workloads by combining cognitive object storage, event-driven materialization, and structured evidence retrieval in a runnable system.  
Request paths, fields, and semantics follow the official Plasmod **[HTTP API documentation](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api)**; this README only describes what this repository wraps and typical usage.

In-package topic index: `from pyplasmod import plasmod_help; plasmod_help()`. CLI: `python -m pyplasmod [topic]`.  
SDK architecture and implementation details: **[docs/SDK.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/SDK.md)**; gateway embedding (CPU/GPU): **[docs/EMBEDDING.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/EMBEDDING.md)**.

---

## Quick start (~5 minutes)

The steps below assume Plasmod is running. For `docker compose up -d` (split), the SDK default is `http://127.0.0.1:19530` and health is on port `9091`; unified / `go run` uses `8080`. See **[Start the Plasmod gateway](#start-the-plasmod-gateway)**.

| Step | What to do | Command / code |
|------|------------|----------------|
| 0 | Confirm the gateway is up | split: `curl -sS http://127.0.0.1:9091/healthz`; unified: `curl -sS http://127.0.0.1:8080/healthz` |
| 1 | Install this client | `pip install pyplasmod` |
| 2 | Configure gateway URL (optional) | split: `export PLASMOD_BASE_URL=http://127.0.0.1:19530`; unified: `http://127.0.0.1:8080` (see [`.env.example`](.env.example)) |
| 3 | Health check | See Python snippet below |
| 4 | (Optional) Upload data | Text/docs **§2.1**; `.fbin` **§2.3**; JSON matrix + ANN index **§2.4**; skip if no data yet |
| 5 | Search | `p.search("your question", "w_demo", top_k=10)` |
| 6 | API details | `plasmod_help("easy")` or read [docs/SDK.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/SDK.md) |

**Steps 3 + 5 minimal example** (verifies connectivity without your own data; `search` returns hits only when data exists):

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
    print("health:", p.health())                    # gateway JSON
    print("search:", p.search("hello", "w_demo"))  # empty store may yield no objects/hits
```

Example script in the [repository](https://github.com/CodeSoul-co/pyplasmod/blob/main/examples/http_quickstart.py) (clone the repo or copy the script; it is not installed via `pip`):

```bash
export PLASMOD_BASE_URL=http://127.0.0.1:19530
python examples/http_quickstart.py
```

---

## Start the Plasmod gateway

**pyplasmod only calls a running Plasmod HTTP service**; it does not ship the server binary. Default entry points:

| Deployment | Health | `PLASMOD_BASE_URL` (SDK) |
|------------|--------|---------------------------|
| `docker compose up -d` (split) | `http://127.0.0.1:9091/healthz` | `http://127.0.0.1:19530` (client default) |
| `docker compose -f docker-compose.unified.yml` or `make dev` / `go run` | `http://127.0.0.1:8080/healthz` | `http://127.0.0.1:8080` |

### Option A: Local dev from Plasmod source (recommended for debugging)

In the [Plasmod](https://github.com/CodeSoul-co/Plasmod) repo root:

```bash
# Requires Go, Python 3, etc.; see Plasmod README
make dev
```

Verify after startup:

```bash
curl -sS http://127.0.0.1:8080/healthz
curl -sS http://127.0.0.1:8080/v1/system/mode
```

More (HNSW build, `make build`, seed data, `scripts/run_demo.py`) is in the Plasmod README **Quick start / Run** section.

### Option B: Docker Compose full stack (split, default)

In the Plasmod repo:

```bash
docker compose up -d
export PLASMOD_BASE_URL=http://127.0.0.1:19530
curl -sS http://127.0.0.1:9091/healthz
```

Single-port unified:

```bash
docker compose -f docker-compose.unified.yml up -d
export PLASMOD_BASE_URL=http://127.0.0.1:8080
```

Switch prod/test with `APP_MODE=prod` / `APP_MODE=test`, etc.; see Plasmod docs.

### Option C: Client-only validation

If you do not have Plasmod yet, `pip install pyplasmod` and run `python -c "from pyplasmod import plasmod_help; plasmod_help()"` for help; **any HTTP call (`health`, `search`, `upload`, …) needs a reachable gateway**.

### Checklist aligned with the client

| Check | Notes |
|-------|--------|
| URL match | `PLASMOD_BASE_URL` (or `base_url=` in code) matches the gateway |
| Port reachable | `curl $PLASMOD_BASE_URL/healthz` returns 2xx |
| Admin APIs | Set `PLASMOD_ADMIN_API_KEY` for `/v1/admin/*`; dev may skip validation if unset (enable in production) |
| Vector dimension | `.fbin` or `ingest_vectors` dimension must match gateway embedder config |

---

## Choose a client entry and built-in help

### Which class?

| Entry | When to use |
|-------|-------------|
| **`EasyPlasmod`** | Day-to-day: health, `search`/`query`, `.fbin` upload, `ingest_document`, `memories` |
| **`PlasmodEmbedding`** | **Gateway-side embedding** (CPU/GPU presets, `ingest`/`search`, runtime probe); also via `p.embedding` |
| **`PlasmodClient`** (= `PlasmodHttpClient`) | Full HTTP/RPC: admin ops, `ingest_vectors`, binary `rpc_*`, internal task/MAS, WAL SSE, etc. |
| **`pyplasmod.data.upload` / `build_query_body`** | Helpers decoupled from HTTP; pass `client=` to reuse connections |
| **`PlasmodVectorStore`** | LangChain (`pip install pyplasmod[langchain]`); embedding runs on the **client** |

Relationship: `EasyPlasmod` holds a **`PlasmodHttpClient`**; use **`p.http`** for the full API. Most examples use `with EasyPlasmod() as p:` to close connections.

```python
from pyplasmod import EasyPlasmod, PlasmodClient

# Convenience entry
with EasyPlasmod() as p:
    p.health()
    p.http.dataset_delete({...})   # admin via .http

# Or the full client directly
with PlasmodClient(base_url="http://127.0.0.1:8080", admin_key="...") as c:
    c.ingest_vectors([[0.1, 0.2, ...]])
```

### Core concepts (primer)

| Concept | Meaning |
|---------|---------|
| **`workspace_id`** | Workspace/tenant boundary; ingest and query usually require it (e.g. `w_demo`) |
| **`dataset_name`** | Logical dataset for bulk imports; matches `upload(..., dataset=...)` |
| **`session_id` / `agent_id`** | Session and agent IDs; **query values must match ingest** or recent writes may not appear |
| **Memory** | Materialized memory objects on the gateway; list with `p.memories(workspace_id)` |
| **`.fbin`** | Bulk vector file format supported by the SDK (see §2) |
| **Gateway embedding** | No `/v1/embed`; text vectors are produced at ingest/query on the server (ONNX/GGUF/TF-IDF, etc.); CPU/GPU via `PLASMOD_EMBEDDER_DEVICE` |

`upload` defaults `session_id` to `ingest_{dataset}_{filename}`; `build_query_body` aligns that session when you pass the same `dataset_name` and `ingest_fbin_path`.

### `plasmod_help()` topics

```python
from pyplasmod import plasmod_help, plasmod_topics

plasmod_help()              # print topic index
print(plasmod_topics())     # [..., 'embedding', 'env', ...]
plasmod_help("embedding")   # PlasmodEmbedding / CPU·GPU
plasmod_help("easy")        # EasyPlasmod + full built-in help()
plasmod_help("env")         # environment variables only
```

CLI equivalents: `python -m pyplasmod`, `python -m pyplasmod upload`, `python -m pyplasmod client`.  
Single topics embed full signatures such as `help(EasyPlasmod)`; for `client`, prefer `help(PlasmodHttpClient)` in a REPL.

---

## Prerequisites

1. **Plasmod gateway deployed and running** (see **[Start the Plasmod gateway](#start-the-plasmod-gateway)**).  
2. **Python 3.8+**.  
3. For **`.fbin` vector files**: format per SDK (see **§2.3**); dimensions must match gateway configuration.

---

## Install

```bash
pip install pyplasmod
```

Optional (LangChain `PlasmodVectorStore`, etc.):

```bash
pip install pyplasmod[langchain]
```

Editable install and tests from this repo:

```bash
pip install -e ".[dev]"
make unittest
```

---

## Environment variables and client configuration

Read at construct time by `PlasmodHttpClient` / `EasyPlasmod` (constructor args override env).

| Variable | Purpose |
|----------|---------|
| `PLASMOD_BASE_URL` or `ANDB_BASE_URL` | Gateway root URL; default `http://127.0.0.1:19530` (split compose). Use `http://127.0.0.1:8080` for unified. |
| `PLASMOD_HTTP_TIMEOUT` or `ANDB_HTTP_TIMEOUT` | HTTP timeout (seconds); default `30`. |
| `PLASMOD_ADMIN_API_KEY` or `ANDB_ADMIN_API_KEY` | `X-Admin-Key` header for `/v1/admin/*`. |

**Gateway embedding (Plasmod process, not the pyplasmod client)** — set via `PlasmodEmbedding.use_cpu` / `use_gpu` or `EmbedderConfig`:

| Variable | Purpose |
|----------|---------|
| `PLASMOD_EMBEDDER` | `tfidf` \| `onnx` \| `gguf` \| `tensorrt` \| `openai` \| … |
| `PLASMOD_EMBEDDER_DEVICE` | `cpu` \| `cuda` \| `metal` (local ONNX/GGUF dual path) |
| `PLASMOD_EMBEDDER_DIM` | Vector dimension |
| `PLASMOD_EMBEDDER_MODEL_PATH` | Local model path |

See **[docs/EMBEDDING.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/EMBEDDING.md)** and [`.env.example`](https://github.com/CodeSoul-co/pyplasmod/blob/main/.env.example).

Equivalent to `PLASMOD_ADMIN_API_KEY`: `EasyPlasmod(..., admin_key="...")` or `PlasmodHttpClient(..., admin_key="...")`. Whether Admin Key is enforced depends on gateway deployment.

```bash
export PLASMOD_BASE_URL=http://127.0.0.1:19530
# export PLASMOD_ADMIN_API_KEY=...   # only when calling admin APIs
```

---

## Common API vs HTTP path

**`p`** means an **`EasyPlasmod`** instance. `upload` and `build_query_body` live in **`pyplasmod.data`** (import separately; see §§2–3).

| Method | HTTP | Notes |
|--------|------|-------|
| `p.health()` | `GET /healthz` | Liveness |
| `p.system_mode()` | `GET /v1/system/mode` | System mode, etc. |
| `p.search(query_text, workspace_id, **kwargs)` | `POST /v1/query` | Builds body via `build_query_body`, then queries; `kwargs` are optional `build_query_body` args (`top_k`, `dataset_name`, …) |
| `p.query(body)` | `POST /v1/query` | Full query JSON; `body` from `build_query_body(...)` |
| `build_query_body(...)` | — | Builds `dict` only, **no** HTTP; pass result to `p.query` |
| `upload(dataset, workspace_id, path, **kwargs)` | `POST /v1/ingest/events` (per line) | `.fbin` line ingest; use `client=p.http` to reuse connection |
| `p.upload_fbin(...)` | same | Same as `upload`, uses `p.http` |
| `p.ingest_document(body)` | `POST /v1/ingest/document` | Long document chunks; `body` needs at least `text`, usually `workspace_id`, `agent_id`, `session_id`, `title` |
| `p.memories(workspace_id, **params)` | `GET /v1/memory` | List Memory in `workspace_id` |
| `p.embedding.ingest(text, workspace_id)` | `POST /v1/ingest/events` | Text ingest, **server** embedding (CPU/GPU from gateway env) |
| `p.embed_search(query, workspace_id, **kw)` | `POST /v1/query` | Semantic search shorthand |
| `p.embedding.runtime(...)` | `POST /v1/query` (probe) | Parse `embedding_runtime_family` / `dim` from `provenance` |
| `PlasmodEmbedding.use_onnx_cpu/gpu(..., apply=True)` | — (writes `os.environ`) | CPU/GPU presets **before** starting Plasmod |
| `p.http.dataset_delete(body)` | `POST /v1/admin/dataset/delete` | Soft delete (`body` per server) |
| `p.http.dataset_purge(body)` | `POST /v1/admin/dataset/purge` | Hard purge; use `dry_run: True` first |
| `p.http.dataset_purge_task(task_id)` | `GET /v1/admin/dataset/purge/task` | Async purge task status |

Other HTTP/RPC methods are on **`PlasmodHttpClient`**; **`EasyPlasmod.http`** exposes it. **`PlasmodClient`** is an alias for **`PlasmodHttpClient`**. Full method list: [docs/SDK.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/SDK.md).

---

## 1. Health check

Confirm network reachability and a healthy gateway process:

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
    print(p.health())
    # print(p.system_mode())
```

---

## 2. Upload data

Choose ingest by shape: **long text/documents** → `ingest_document` (§2.1); **pre-vectorized or per-event control** → `.fbin` / `ingest_event` (§2.2–2.3); **in-memory JSON matrices with ANN index choice** → `ingest_vectors` (§2.4). Reuse the same `EasyPlasmod` for later `search`; keep **`workspace_id`, `session_id`, and `agent_id` consistent between ingest and query**.

### 2.1 Text and long documents (`ingest_document`)

Gateway `POST /v1/ingest/document` splits **`text`** into episodic memory events (server-side chunking).

| Field | Required | Notes |
|-------|----------|-------|
| `text` | **yes** | Body string |
| `workspace_id` | strongly recommended | e.g. `w_demo` |
| `agent_id` | strongly recommended | must match at query time |
| `session_id` | strongly recommended | must match at query time |
| `title` | recommended | document title |
| `chunk_size` | optional | chunk size (semantics per gateway) |
| `overlap` | optional | overlap between chunks |
| `importance` | optional | weight if supported |

**Write a string directly**:

```python
from pyplasmod import EasyPlasmod

workspace = "w_demo"
session_id = "my_doc_session"   # reuse same session_id when querying
agent_id = "pyplasmod_data"

with EasyPlasmod() as p:
    r = p.ingest_document(
        {
            "text": "Body text to ingest: notes, meeting minutes, or RAG corpus.",
            "workspace_id": workspace,
            "agent_id": agent_id,
            "session_id": session_id,
            "title": "Example document",
            "chunk_size": 500,   # optional chunk granularity
            "overlap": 50,       # optional overlap
        }
    )
    print("ingest_document:", r)
```

**Read a local file then upload** (`.txt`, `.md`, plain text):

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
    # query with the same session_id / agent_id
    hits = p.query(
        build_query_body(
            "What does the document say?",
            workspace,
            session_id=session_id,
            agent_id=agent_id,
            top_k=5,
        )
    )
    print(hits)
```

`ingest_document` does **not** require a local `.fbin` or `embedding_vector` (embedding is on the gateway). Good for RAG corpora, docs, and conversation notes.

Or use the embedding facade (gateway embed + later `search`):

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
    p.embedding.ingest_document(
        "Long document body…",
        workspace_id="w_demo",
        title="Handbook",
        session_id="doc_session",
    )
```

### 2.2 Single short text (`ingest_event`)

For **one** structured event (custom `payload`, optional vector), use `POST /v1/ingest/events`:

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
  p.ingest_event(
      {
          "event_id": "evt_note_001",       # globally unique recommended
          "workspace_id": "w_demo",
          "agent_id": "pyplasmod_data",
          "session_id": "notes_session",
          "event_type": "observation",
          "payload": {"text": "A short observation or note"},
          "source": "my_app",
          "version": 1,
          # If the gateway requires vectors: embedding_vector: [0.1, 0.2, ...]
      }
  )
```

Loop `ingest_event` for many rows, or `p.http.ingest_events([...])` for batch. Full field list: [Plasmod HTTP API](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api).

### 2.3 Vector files (`.fbin`)

**Format**: first 8 bytes are little-endian `uint32` row count, `uint32` dimension; then row-major **little-endian `float32`** vectors. `upload` **only** accepts `.fbin` suffix; others raise `ValueError`.

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

CLI equivalent:

```bash
python -m pyplasmod.data upload my_dataset w_demo /path/to/vectors.fbin --show-progress
```

For **JSON vector matrices** (not `.fbin`), use `p.http.ingest_vectors` or `p.http.ingest_batch` (PLIB) at large scale. To pick the warm-segment ANN index type, see **§2.4**.

### 2.4 JSON vectors and warm ANN index (`ingest_vectors`)

`POST /v1/ingest/vectors` builds a warm segment from caller-supplied vectors. The ANN index is fixed at **ingest time**; queries must use the same `segment_id` (or `warm_segment_id` in the query body).

| `index_type` | When to consider |
|--------------|------------------|
| `HNSW` | **Default** (omit `index_type`) |
| `IVF_FLAT` / `IVF_PQ` / `IVF_SQ8` | Large corpora; tune `ivf_nlist`, `ivf_nprobe`, etc. |
| `DISKANN` | Very large scale, disk-friendly |

**Note:** Only `ingest_vectors` supports `index_type`;

```python
from pyplasmod import PlasmodClient, WARM_INDEX_IVF_FLAT

with PlasmodClient() as c:
    c.ingest_vectors(
        [[0.1, 0.2, ...]],  # dim must match gateway warm segment / embedder config
        segment_id="demo.ivf",
        index_type=WARM_INDEX_IVF_FLAT,  # or "IVF_FLAT"
        ivf_nlist=128,
        ivf_nprobe=32,
    )
```

Omitting `index_type` uses server default **HNSW**. Pass other constants or strings for `IVF_PQ`, `DISKANN`, and so on. Full fields and comparison with `ingest_batch`: [docs/SDK.md](docs/SDK.md) §10.

---

## 3. Query (natural-language search)

**Simple** (builds body and `POST /v1/query`):

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod()
r = p.search("example question", "w_demo", top_k=10)
print(r)
```

**Same dataset name as `upload` and aligned session rules** — pass `dataset_name` and `ingest_fbin_path` (path should match the uploaded `.fbin`, including filename):

```python
from pyplasmod import EasyPlasmod
from pyplasmod.data import build_query_body

p = EasyPlasmod()
body = build_query_body(
    "example question",
    "w_demo",
    top_k=20,
    dataset_name="my_dataset",
    ingest_fbin_path="/path/to/vectors.fbin",
)
r = p.query(body)
print(r)
```

Response shape depends on server version. Common keys include **`objects`** or **`hits`**; treat the live JSON as authoritative.

---

## 3.1 Gateway embedding and CPU / GPU (`PlasmodEmbedding`)

Plasmod has **no** standalone embed HTTP route; vectors are produced at **ingest / query** by the gateway embedder. pyplasmod wraps this with **`PlasmodEmbedding`** and maps Plasmod’s **CPU / GPU dual paths** (ONNX, GGUF, TensorRT, etc.).

**Minimal** (text ingest + search + runtime family):

```python
from pyplasmod import PlasmodEmbedding

with PlasmodEmbedding.connect() as emb:
    emb.ingest("Sentence to store", workspace_id="w_demo")
    print(emb.search("search terms", workspace_id="w_demo", top_k=5))
    print(emb.runtime())  # family / dim from query provenance
```

**Same on `EasyPlasmod`**:

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
    p.embed_ingest("Sentence to store", workspace_id="w_demo")
    print(p.embed_search("search terms", workspace_id="w_demo"))
```

**Pick CPU or GPU before deploy** (env vars, then start Plasmod):

```python
from pyplasmod import PlasmodEmbedding

emb = PlasmodEmbedding.connect()
emb.use_onnx_cpu(model_path="/models/model.onnx", dim=384, apply=True)   # CPU
# emb.use_onnx_gpu(model_path="/models/model.onnx", dim=384, apply=True)  # CUDA
print(emb.capabilities())  # cpu/cuda/metal per provider
```

Topic guide: **[docs/EMBEDDING.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/EMBEDDING.md)**. Architecture: [docs/SDK.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/SDK.md) §8.

---

## 4. Approximate counts

Plasmod may not expose a dedicated COUNT API. Options below give **approximate or page-limited** counts (set `top_k` or Memory `limit` high enough).

**Option A: length of query result list**

```python
from pyplasmod import EasyPlasmod
from pyplasmod.data import build_query_body

p = EasyPlasmod()
r = p.query(build_query_body(".", "w_demo", top_k=5000))
objs = r.get("objects") or []
print("objects in response:", len(objs))
```

**Option B: length of Memory list response**

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod()
rows = p.memories("w_demo")
print("memories in response:", len(rows or []))
```

---

## 5. Dataset delete and purge (admin)

These are **`/v1/admin/*`**. If the gateway enforces keys, set `PLASMOD_ADMIN_API_KEY` or pass `admin_key` at construct time.

**Soft delete** (semantics per server):

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod(admin_key="...")
print(p.http.dataset_delete({"workspace_id": "w_demo", "dataset_name": "my_dataset"}))
```

**Hard purge**: run with **`dry_run: True`** first, then execute for real.

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod(admin_key="...")
print(
    p.http.dataset_purge(
        {"workspace_id": "w_demo", "dataset_name": "my_dataset", "dry_run": True}
    )
)
```

**Async purge task** (when the server returns `task_id`):

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod(admin_key="...")
print(p.http.dataset_purge_task("<task_id>"))
```

---

## 6. Example scripts and further reading

| Path | Contents |
|------|----------|
| `examples/http_quickstart.py` | HTTP quickstart (`python examples/http_quickstart.py`) |
| `examples/ingest_fbin.py` | `.fbin` ingest |
| `examples/batch_ingest.py` | Batch vectors / events |
| `examples/langchain_quickstart.py` | LangChain (`pip install pyplasmod[langchain]`) |
| `examples/embedding_cpu_gpu.py` | Gateway embedding, CPU/GPU presets, `PlasmodEmbedding` |

- **Gateway embedding (CPU/GPU):** [docs/EMBEDDING.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/EMBEDDING.md)  
- **SDK architecture and implementation:** [docs/SDK.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/SDK.md)  
- **SDK usage guide** (parameters, samples, troubleshooting): [docs/plans/pyplasmod-003-sdk-usage-guide.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/plans/pyplasmod-003-sdk-usage-guide.md)  
- **HTTP SDK architecture:** [docs/plans/pyplasmod-001-http-sdk-design.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/plans/pyplasmod-001-http-sdk-design.md)  
- **Tier B extension APIs:** [docs/plans/pyplasmod-002-gateway-tier-b-shortcuts-design.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/plans/pyplasmod-002-gateway-tier-b-shortcuts-design.md)  
- **Documentation index:** [docs/README.md](https://github.com/CodeSoul-co/pyplasmod/blob/main/docs/README.md)  
- **Routes and field mapping:** [Plasmod `docs/sdk/README.md`](https://github.com/CodeSoul-co/Plasmod/blob/main/docs/sdk/README.md)  
- **Binary frame helpers:** `from pyplasmod.http import encode_ingest_batch`, etc. (most cases: `PlasmodHttpClient.rpc_*`)

---

## License

MIT (see `LICENSE` at the repository root).
