# pyplasmod

**pyplasmod** 是面向 **[Plasmod](https://github.com/CodeSoul-co/Plasmod)** 的 Python **HTTP 客户端库**：通过标准 HTTP（及部分二进制 RPC）访问已部署的 Plasmod 网关，完成向量入库、检索、Memory 列举、数据集运维与健康检查等操作。

**Plasmod** 面向多智能体场景，将认知对象存储、事件驱动的物化与结构化证据检索集成在可运行系统中。  
请求路径、字段与语义以 Plasmod 官方 **[HTTP API 文档](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api)** 为准；本 README 仅说明本仓库提供的封装与典型用法。

包内主题索引：`from pyplasmod import plasmod_help; plasmod_help()`；命令行：`python -m pyplasmod [topic]`。

---

## 前置条件

1. **已部署并启动 Plasmod 网关**（监听地址须与本客户端配置的 `base_url` 一致，常见为 `http://127.0.0.1:8080`）。  
2. **Python 3.8 及以上**。  
3. 使用 **`.fbin` 向量文件** 时：文件格式须符合 SDK 约定（见 **第 2 节「上传数据」**）；向量维度须与网关侧配置一致。

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
| `p.http.dataset_delete(body)` | `POST /v1/admin/dataset/delete` | 数据集软删除（`body` 字段以服务端为准） |
| `p.http.dataset_purge(body)` | `POST /v1/admin/dataset/purge` | 数据集硬清理；执行前应使用 `dry_run: True` 评估影响 |
| `p.http.dataset_purge_task(task_id)` | `GET /v1/admin/dataset/purge/task` | 查询异步 purge 任务状态 |

其余 HTTP 与 RPC 接口均位于 **`PlasmodHttpClient`** 实例上。`EasyPlasmod` 通过属性 **`http`** 暴露该实例。类型别名 **`PlasmodClient`** 与 **`PlasmodHttpClient`** 指向同一类。完整方法名列表见 [docs/SDK.md](docs/SDK.md)。

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

## 2. 上传数据（`.fbin` 向量文件）

**文件格式**：前 8 字节为 little-endian `uint32` 行数、`uint32` 维度；随后为按行排列的 **little-endian `float32`** 向量。当前 `upload` **仅支持** 后缀名为 `.fbin` 的文件；其他后缀将抛出 `ValueError` 并提示暂不支持。

**推荐**：与后续查询共用同一 `EasyPlasmod` 实例，以保证 `base_url` 与连接配置一致。

```python
from pyplasmod import EasyPlasmod
from pyplasmod.data import upload

p = EasyPlasmod(admin_key=None)  # 若网关要求管理密钥，请传入有效 admin_key 或配置环境变量
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
| `examples/http_quickstart.py` | HTTP 快速示例 |
| `examples/ingest_fbin.py` | `.fbin` 入库示例 |
| `examples/batch_ingest.py` | 批量向量 / 事件 |
| `examples/langchain_quickstart.py` | LangChain 集成（需安装可选依赖） |
| `examples/try.py` | 较完整联调脚本（依赖本地数据路径与环境变量） |

- **路由与字段映射**：[Plasmod `docs/sdk/README.md`](https://github.com/CodeSoul-co/Plasmod/blob/main/docs/sdk/README.md)  
- **Milvus 迁移对照**：[docs/integrations/milvus_plasmod_mapping.md](docs/integrations/milvus_plasmod_mapping.md)  
- **二进制帧工具**：`from pyplasmod.http import encode_ingest_batch` 等（多数场景可直接使用 `PlasmodHttpClient.rpc_*`）  
- **异常类型**：`PlasmodHttpError`、`PlasmodException` 等，详见 [docs/plans/pyplasmod-003-sdk-usage-guide.md](docs/plans/pyplasmod-003-sdk-usage-guide.md)

---

## 许可证

MIT（见仓库根目录 `LICENSE`）。
