# 网关侧嵌入（Embedding）与 CPU / GPU

> 入门步骤见 [README.md](../README.md) 的 **「网关嵌入」** 一节；本文是嵌入专题说明。

## 1. 模型说明

Plasmod **没有** 独立的 `POST /v1/embed` 接口。文本向量在网关进程内、于以下路径生成：

| 路径 | 何时嵌入 |
|------|----------|
| `POST /v1/ingest/events` | `payload.text` 且无顶层 `embedding_vector` |
| `POST /v1/ingest/document` | 文档分块后由服务端嵌入 |
| `POST /v1/query` | 提供 `query_text` 且未提供 `embedding_vector` |

**CPU / GPU 选择在服务端**：通过环境变量 `PLASMOD_EMBEDDER` 与 `PLASMOD_EMBEDDER_DEVICE`（以及对应 Go 构建标签 `-tags cuda`）。pyplasmod 不本地跑 ONNX/GGUF，只封装配置与 HTTP 调用。

---

## 2. 推荐入口：`PlasmodEmbedding`

```python
from pyplasmod import PlasmodEmbedding

with PlasmodEmbedding.connect() as emb:
    # 查看各 provider 的 cpu / cuda / metal 支持
    print(emb.capabilities())

    # 入库 + 检索（由网关 embedder 算向量）
    emb.ingest("Plasmod 支持混合检索。", workspace_id="w_demo")
    resp = emb.search("混合检索", workspace_id="w_demo", top_k=5)

    # 探测当前网关实际用的 family / dim
    info = emb.runtime(workspace_id="w_demo")
    print(info.family, info.dim)
```

与 `EasyPlasmod` 组合：

```python
from pyplasmod import EasyPlasmod

with EasyPlasmod() as p:
    p.embedding.ingest("hello", workspace_id="w_demo")
    p.embed_search("hello", workspace_id="w_demo")   # 等价简写
```

工厂函数别名：

```python
from pyplasmod import open_embedding

with open_embedding() as emb:
    emb.search("q", workspace_id="w_demo")
```

---

## 3. 部署：CPU / GPU 预设

在 **启动 Plasmod 之前** 写入环境变量（或写入 compose / systemd）：

```python
from pyplasmod import PlasmodEmbedding

emb = PlasmodEmbedding.connect()

# 方式 A：语义化简写
emb.use_cpu("onnx", model_path="/models/model.onnx", dim=384, apply=True)
emb.use_gpu("onnx", model_path="/models/model.onnx", dim=384, apply=True)

# 方式 B：显式预设
emb.use_onnx_cpu(model_path="/models/model.onnx", dim=384, apply=True)
emb.use_onnx_gpu(model_path="/models/model.onnx", dim=384, apply=True)
emb.use_gguf_cpu(model_path="/models/model.gguf", dim=384, apply=True)
emb.use_gguf_gpu(model_path="/models/model.gguf", dim=384, apply=True)
```

| 方法 | 设备 | 对应 Plasmod |
|------|------|----------------|
| `use_onnx_cpu` / `use_cpu("onnx")` | CPU | `onnx_cpu.go` |
| `use_onnx_gpu` / `use_gpu("onnx")` | CUDA | `onnx_cuda.go`（`-tags cuda`） |
| `use_gguf_cpu` | CPU | `gguf_cpu.go` |
| `use_gguf_gpu` | CUDA | `gguf_cuda.go` |
| `use_gpu("tensorrt", ...)` | CUDA only | `tensorrt_cuda.go` |

`apply=True` 会调用 `os.environ` 写入 `PLASMOD_EMBEDDER*`；随后在同一 shell 或 compose 中启动 Plasmod。

也可直接使用 `EmbedderConfig`：

```python
from pyplasmod import EmbedderConfig

cfg = EmbedderConfig.onnx_cuda(model_path="/models/model.onnx", dim=384)
cfg.apply_to_environ()
```

---

## 4. API 对照

### `PlasmodEmbedding`（推荐）

| 方法 | 作用 |
|------|------|
| `capabilities()` | 打印 CPU/GPU 能力表 |
| `config()` | 读本机 `PLASMOD_EMBEDDER*` |
| `runtime(...)` | 探针：query provenance 中的 `embedding_runtime_*` |
| `ingest(text, workspace_id)` | 单条文本入库（服务端嵌入） |
| `ingest_document(text, workspace_id, ...)` | 长文档分块入库 |
| `search(query, workspace_id, top_k=...)` | 语义检索 |
| `use_cpu` / `use_gpu` / `use_onnx_*` | 部署预设 |

### `EasyPlasmod` 简写

| 方法 | 等价 |
|------|------|
| `p.embedding` | `PlasmodEmbedding(easy=p)` |
| `p.embed_ingest(...)` | `p.embedding.ingest(...)` |
| `p.embed_search(...)` | `p.embedding.search(...)` |
| `p.embedding_runtime()` | `p.embedding.runtime()` |

### 低级模块（扩展用）

| 符号 | 说明 |
|------|------|
| `EmbedderConfig` | 环境变量 ↔ 配置对象 |
| `GatewayEmbedding` | 直接包装 `PlasmodHttpClient` |
| `build_query_body(..., embedding_vector=...)` | 自带向量查询 |
| `format_capability_table()` | 能力表字符串 |

---

## 5. 自带向量（跳过网关 embedder）

客户端已有向量时，不要依赖服务端嵌入：

```python
from pyplasmod.data import build_query_body
from pyplasmod import EasyPlasmod

vec = [0.1, 0.2, ...]  # dim 须与网关一致
with EasyPlasmod() as p:
    body = build_query_body("ignored", "w_demo", embedding_vector=vec, top_k=10)
    p.query(body)
```

`.fbin` / `ingest_vectors` 路径见 [SDK.md](SDK.md) §7。

---

## 6. 环境变量（网关进程）

| 变量 | 说明 |
|------|------|
| `PLASMOD_EMBEDDER` | `tfidf` \| `onnx` \| `gguf` \| `tensorrt` \| `openai` \| … |
| `PLASMOD_EMBEDDER_DEVICE` | `cpu` \| `cuda` \| `metal` |
| `PLASMOD_EMBEDDER_DIM` | 向量维度（须与模型一致） |
| `PLASMOD_EMBEDDER_MODEL_PATH` | 本地 `.onnx` / `.gguf` / `.engine` |
| `PLASMOD_ONNX_VOCAB_PATH` | ONNX BERT 词表（可选） |

完整列表见仓库 [`.env.example`](../.env.example) 与 Plasmod `docs/server-migration.md`。

---

## 7. 与 LangChain 的区别

| | `PlasmodEmbedding` | `PlasmodVectorStore` + LangChain `Embeddings` |
|--|-------------------|-----------------------------------------------|
| 嵌入位置 | **网关** | **客户端**（OpenAI 等） |
| CPU/GPU | 服务端 ONNX/GGUF/TensorRT | 取决于你选的 LangChain 模型 |
| 典型用途 | 与 Plasmod 部署配置一致 | 已有 LangChain 嵌入管线 |

---

## 8. 示例与测试

```bash
python examples/embedding_cpu_gpu.py
python -m pytest tests/test_embedding.py -q
```
