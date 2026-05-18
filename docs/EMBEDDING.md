# Gateway-side embedding (CPU / GPU)

> **中文** | [zh-CN/EMBEDDING.md](zh-CN/EMBEDDING.md)  
> Quick start: [README.md](../README.md) § Gateway embedding.

## 1. Model

Plasmod has **no** standalone `POST /v1/embed` route. Vectors are produced **inside the gateway** on these paths:

| Route | When embedding runs |
|-------|---------------------|
| `POST /v1/ingest/events` | `payload.text` present and no top-level `embedding_vector` |
| `POST /v1/ingest/document` | After server-side chunking |
| `POST /v1/query` | `query_text` set and `embedding_vector` omitted |

**CPU vs GPU** is chosen on the **server** via `PLASMOD_EMBEDDER` and `PLASMOD_EMBEDDER_DEVICE` (and Go build tags such as `-tags cuda`). pyplasmod does not run ONNX/GGUF locally; it documents env vars and HTTP helpers.

---

## 2. Recommended entry: `PlasmodEmbedding`

```python
from pyplasmod import PlasmodEmbedding

with PlasmodEmbedding.connect() as emb:
    print(emb.capabilities())

    emb.ingest("Plasmod supports hybrid retrieval.", workspace_id="w_demo")
    resp = emb.search("hybrid retrieval", workspace_id="w_demo", top_k=5)

    info = emb.runtime(workspace_id="w_demo")
    print(info.family, info.dim)
```

With `EasyPlasmod`:

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
    p.embedding.ingest("hello", workspace_id="w_demo")
    p.embed_search("hello", workspace_id="w_demo")
```

Alias factory:

```python
from pyplasmod import open_embedding

with open_embedding() as emb:
    emb.search("q", workspace_id="w_demo")
```

---

## 3. Deploy: CPU / GPU presets

Set environment variables **before starting Plasmod** (or in compose / systemd):

```python
from pyplasmod import PlasmodEmbedding

emb = PlasmodEmbedding.connect()
emb.use_onnx_cpu(model_path="/models/model.onnx", dim=384, apply=True)
emb.use_onnx_gpu(model_path="/models/model.onnx", dim=384, apply=True)
```

| Method | Device | Plasmod backend |
|--------|--------|-----------------|
| `use_onnx_cpu` / `use_cpu("onnx")` | CPU | `onnx_cpu.go` |
| `use_onnx_gpu` / `use_gpu("onnx")` | CUDA | `onnx_cuda.go` (`-tags cuda`) |
| `use_gguf_cpu` | CPU | `gguf_cpu.go` |
| `use_gguf_gpu` | CUDA | `gguf_cuda.go` |
| `use_gpu("tensorrt", ...)` | CUDA only | `tensorrt_cuda.go` |

`apply=True` writes `PLASMOD_EMBEDDER*` into `os.environ`; start Plasmod in the same shell or compose service.

Or use `EmbedderConfig` directly:

```python
from pyplasmod import EmbedderConfig

EmbedderConfig.onnx_cuda(model_path="/models/model.onnx", dim=384).apply_to_environ()
```

**Model path:** ONNX/GGUF on CPU **requires** a real file on the **gateway host** (`PLASMOD_EMBEDDER_MODEL_PATH`). Default dev embedder **tfidf** needs no model file.

---

## 4. API map

### `PlasmodEmbedding`

| Method | Role |
|--------|------|
| `capabilities()` | Print CPU/GPU capability table |
| `config()` | Read local `PLASMOD_EMBEDDER*` |
| `runtime(...)` | Probe `embedding_runtime_*` from query provenance |
| `ingest(text, workspace_id)` | Text ingest (server embeds) |
| `ingest_document(...)` | Chunked document ingest |
| `search(query, workspace_id, top_k=...)` | Semantic search |
| `use_cpu` / `use_gpu` / `use_onnx_*` | Deployment presets |

### `EasyPlasmod` shortcuts

| Method | Equivalent |
|--------|------------|
| `p.embedding` | `PlasmodEmbedding(easy=p)` |
| `p.embed_ingest(...)` | `p.embedding.ingest(...)` |
| `p.embed_search(...)` | `p.embedding.search(...)` |
| `p.embedding_runtime()` | `p.embedding.runtime()` |

### Lower-level modules

| Symbol | Role |
|--------|------|
| `EmbedderConfig` | Env ↔ config object |
| `GatewayEmbedding` | Thin wrapper over `PlasmodHttpClient` |
| `build_query_body(..., embedding_vector=...)` | Query with client vector |
| `format_capability_table()` | Capability table string |

---

## 5. Client-supplied vectors

When you already have embeddings, skip the gateway embedder:

```python
from pyplasmod.data import build_query_body
from pyplasmod import EasyPlasmod

vec = [0.1, 0.2, ...]  # dim must match gateway
with EasyPlasmod() as p:
    p.query(build_query_body("ignored", "w_demo", embedding_vector=vec, top_k=10))
```

See [SDK.md](SDK.md) §7 for `.fbin` / `ingest_vectors`.

---

## 6. Environment variables (gateway process)

| Variable | Meaning |
|----------|---------|
| `PLASMOD_EMBEDDER` | `tfidf` \| `onnx` \| `gguf` \| `tensorrt` \| `openai` \| … |
| `PLASMOD_EMBEDDER_DEVICE` | `cpu` \| `cuda` \| `metal` |
| `PLASMOD_EMBEDDER_DIM` | Vector dimension |
| `PLASMOD_EMBEDDER_MODEL_PATH` | Local `.onnx` / `.gguf` / engine path |
| `PLASMOD_ONNX_VOCAB_PATH` | Optional BERT vocab for ONNX |

See [`.env.example`](../.env.example) and Plasmod server docs.

---

## 7. vs LangChain

| | `PlasmodEmbedding` | `PlasmodVectorStore` + LangChain `Embeddings` |
|--|-------------------|-----------------------------------------------|
| Where embed runs | **Gateway** | **Client** (OpenAI, etc.) |
| CPU/GPU | Server ONNX/GGUF/TensorRT | Depends on LangChain model |
| Typical use | Match Plasmod deployment | Existing LangChain pipelines |

---

## 8. Examples and tests

```bash
python examples/embedding_cpu_gpu.py
python -m pytest tests/test_embedding.py -q
```
