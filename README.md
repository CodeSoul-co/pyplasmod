# pyplasmod

面向 **[Plasmod](https://github.com/CodeSoul-co/Plasmod)** 的 Python **HTTP** 客户端：在本地或你自己的服务地址上，完成**上传向量、检索、按数据集删除/清理、健康检查、看大概条数**等常见操作。服务端需已启动；字段细节以 Plasmod **[HTTP API 文档](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api)** 为准。

**Plasmod 是什么**  
Plasmod 面向多智能体系统，将认知对象存储、事件驱动的物化与结构化证据检索整合在可运行的系统中。


| 方法 | 路径 | 参数 | 描述 |
|------|------|------|------|
| `p.health()` | `GET /healthz` | 无 | 服务是否存活 |
| `p.system_mode()` | `GET /v1/system/mode` | 无 | 读取系统模式等 |
| `p.search(query_text, workspace_id, **kwargs)` | `POST /v1/query` | 查询句、`workspace_id`；`kwargs` 传给 `build_query_body`（如 `top_k`、`dataset_name`） | 一步完成「拼查询体 + 检索」 |
| `p.query(body)` | `POST /v1/query` | `body`：查询 JSON（可用 `build_query_body(...)` 生成） | 完全自控查询字段 |
| `build_query_body(...)` | — | `query_text`、`workspace_id`；可选 `dataset_name`、`ingest_fbin_path`、`top_k` 等 | **只拼 dict、不发起 HTTP**；再交给 `p.query` |
| `upload(dataset, workspace_id, path, **kwargs)` | `POST /v1/ingest/events`（每行一次） | 逻辑数据集名、`workspace_id`、`.fbin` 路径；常用 `client=p.http`、`limit`、`show_progress` | 向量文件按行入库 |
| `p.upload_fbin(dataset, workspace_id, path, **kwargs)` | 同上 | 同上（内部固定使用 `p.http`） | 与 `upload` 等价，写法更短 |
| `p.ingest_document(body)` | `POST /v1/ingest/document` | `body`：至少含 `text`；通常还有 `workspace_id`、`agent_id`、`session_id`、`title` 等 | 长文档分块写入 |
| `p.memories(workspace_id, **params)` | `GET /v1/memory` | `workspace_id` 写入 query；其余合并到 `params` | 列出该 workspace 下 memory，便于估计条数 |
| `p.http.dataset_delete(body)` | `POST /v1/admin/dataset/delete` | `body`：`workspace_id`、`dataset_name` 等（以服务端为准） | 按数据集**软删** |
| `p.http.dataset_purge(body)` | `POST /v1/admin/dataset/purge` | `body`：`workspace_id`、`dataset_name`；建议先 `dry_run: True` | **硬清理**匹配数据 |
| `p.http.dataset_purge_task(task_id)` | `GET /v1/admin/dataset/purge/task` | 查询参数 `task_id` | 查询异步 purge 任务状态 |
| `plasmod_help(topic=None)` | — | `topic`：`easy` / `client` / `upload` / `querybody` / `env` / `errors` / `binary`；省略则打印索引 | 包内主题帮助；完整签名见 `help(...)`；命令行：`python -m pyplasmod [topic]` |

`PlasmodClient()`（即 `PlasmodHttpClient`）与 `p.http` 上还有其它方法；完整列表见 [docs/plans/pyplasmod-003-sdk-usage-guide.md](docs/plans/pyplasmod-003-sdk-usage-guide.md)。

---

## 1. 安装与环境

**Python 3.8+**

```bash
pip install pyplasmod
```

可选安装 LangChain 适配（`PlasmodVectorStore` 等）：`pip install pyplasmod[langchain]`。

**指向你的 Plasmod 地址**（不设则默认 `http://127.0.0.1:8080`）：

```bash
export PLASMOD_BASE_URL=http://127.0.0.1:8080   # 或 ANDB_BASE_URL
```

**管理类接口**（删除数据集、purge 等走 `/v1/admin/*`）需要 Admin Key，任选其一：

```bash
export PLASMOD_ADMIN_API_KEY=你的密钥    # 或 ANDB_ADMIN_API_KEY
```

也可以在代码里传入 `admin_key="..."`（见下文）。

---

## 2. 健康检查

确认服务能连上：

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod()
print(p.health())          # GET /healthz
# print(p.system_mode())   # 可选：系统模式
```

---

## 3. 上传数据（暂时`.fbin` 向量文件）

`.fbin` 格式：文件头 8 字节为 `uint32` 行数、`uint32` 维度，后面按行存放 **little-endian float32** 向量；向量维度须与服务端配置一致。

**Python（推荐共用同一个客户端，便于后续查询带同一 base_url）：**

```python
from pyplasmod import EasyPlasmod
from pyplasmod.data import upload

p = EasyPlasmod(admin_key="你的AdminKey或留空")
n = upload(
    "我的数据集名",           # 逻辑名，会写进事件里，查询时可按数据集过滤
    "w_demo",                 # workspace_id，按你环境修改
    "/path/to/vectors.fbin",
    client=p.http,
    limit=0,                  # 0 = 全部行；调试可设 limit=100
    show_progress=True,
)
print("已写入行数:", n)
```

**命令行（会按环境变量自己建连接）：**

```bash
python -m pyplasmod.data upload 我的数据集名 w_demo /path/to/vectors.fbin --show-progress
```

---

## 4. 查询（自然语言检索）

**最简单**（内部会拼好查询体并 `POST /v1/query`）：

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod()
r = p.search("你的问题", "w_demo", top_k=10)
print(r)
```

**按「上传时用的数据集名」过滤**（与 `upload(..., dataset=...)` 一致），并让会话与上传默认规则对齐时，用 `build_query_body`：

```python
from pyplasmod import EasyPlasmod
from pyplasmod.data import build_query_body

p = EasyPlasmod()
body = build_query_body(
    "你的问题",
    "w_demo",
    top_k=20,
    dataset_name="我的数据集名",
    ingest_fbin_path="/path/to/vectors.fbin",  # 与上传时同一文件名即可对齐 session
)
r = p.query(body)
print(r)
```

返回结构以服务端为准；常见用法里 **`r.get("objects")` 或 `r.get("hits")`** 即为候选结果列表（键名随版本可能不同，以实际 JSON 为准）。

---

## 5. 查「大概多少条」

没有单独「COUNT」接口时，可以用下面两种方式之一（数值为近似/当前页，**`top_k` 要够大**才接得住总量）：

**A. 用检索结果条数（偏业务对象）**

```python
from pyplasmod import EasyPlasmod
from pyplasmod.data import build_query_body

p = EasyPlasmod()
r = p.query(build_query_body(".", "w_demo", top_k=5000))  # "." 仅作占位 query_text
objs = r.get("objects") or []
print("本查询返回条数:", len(objs))
```

**B. 列当前 workspace 下的 memory 行数**

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod()
rows = p.memories("w_demo")  # 内部 GET /v1/memory?workspace_id=...
print("memory 条数:", len(rows or []))
```

---

## 6. 按数据集删除（软删）与清理（硬删 / purge）

这些属于 **管理接口**，必须配置好 **`PLASMOD_ADMIN_API_KEY`**（或构造时传入 `admin_key`）。

**软删某个数据集**（具体语义以服务端为准，一般为标记不活跃等）：

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod(admin_key="你的AdminKey")
print(p.http.dataset_delete({
    "workspace_id": "w_demo",
    "dataset_name": "我的数据集名",
}))
```

**硬清理（purge）**：会按 body 里条件删除匹配数据；务必先用 **`dry_run: True`** 看一眼影响，再改为 `False` 执行。

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod(admin_key="你的AdminKey")
# 演练，不落真实删除
print(p.http.dataset_purge({
    "workspace_id": "w_demo",
    "dataset_name": "我的数据集名",
    "dry_run": True,
}))
# 若服务端默认只清 inactive，需要清「仍活跃」数据时，可能要加 only_if_inactive 等字段，以网关为准，例如：
# print(p.http.dataset_purge({
#     "workspace_id": "w_demo",
#     "dataset_name": "我的数据集名",
#     "only_if_inactive": False,
#     "dry_run": False,
# }))
```

**异步 purge 任务状态**（若服务端返回了 `task_id`）：

```python
from pyplasmod import EasyPlasmod

p = EasyPlasmod(admin_key="你的AdminKey")
print(p.http.dataset_purge_task("任务返回的 task_id"))
```

---

## 7. 进阶说明（可选读）

- **主题帮助**：`from pyplasmod import plasmod_help; plasmod_help()` 打印索引；`plasmod_help("easy")` 等查看单主题；与内置 `help(EasyPlasmod)`、`help(PlasmodHttpClient)` 配合。命令行：`python -m pyplasmod` 或 `python -m pyplasmod easy`。
- **`EasyPlasmod`**：封装了健康检查、检索、上传、列 memory 等常用路径；**其它所有 HTTP 能力**（更多 admin、内部接口等）都在 **`p.http`** 上，类型为 **`PlasmodHttpClient`**，与 `from pyplasmod import PlasmodClient` 相同。
- **完整方法列表、参数表、异常类型**：见仓库内 **[docs/plans/pyplasmod-003-sdk-usage-guide.md](docs/plans/pyplasmod-003-sdk-usage-guide.md)**（偏开发与排障）。
- **示例脚本**：`examples/http_quickstart.py`、`examples/ingest_fbin.py`；联调全流程可参考 `examples/try.py`（需本地环境变量指向你的数据路径）。

开发安装与跑测试：

```bash
pip install -e ".[dev]"
make unittest
```

---

## 8. 契约、迁移、批量与 LangChain

- **路由与字段映射**：[Plasmod `docs/sdk/README.md`](https://github.com/CodeSoul-co/Plasmod/blob/main/docs/sdk/README.md)；OpenAPI 以服务端导出为准。
- **Milvus 迁移对照**：[docs/integrations/milvus_plasmod_mapping.md](docs/integrations/milvus_plasmod_mapping.md)。
- **底层 `PlasmodClient`（即 `PlasmodHttpClient`）**：`health`、`ingest_event`、`query` 等；**批量向量 / 事件**见 `ingest_batch`、`ingest_events`、`add_vectors`，示例 **`examples/batch_ingest.py`**。
- **LangChain**：安装 `pyplasmod[langchain]` 后见 **`examples/langchain_quickstart.py`**；二进制帧工具见 **`from pyplasmod.http import encode_ingest_batch`** 等。
- **异常**：`PlasmodHttpError`、`ConnectError`、`PlasmodException`；详见 [docs/plans/pyplasmod-003-sdk-usage-guide.md](docs/plans/pyplasmod-003-sdk-usage-guide.md)。

## 许可证

MIT（见仓库根目录 `LICENSE`）。
