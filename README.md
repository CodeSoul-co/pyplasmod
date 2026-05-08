# pyplasmod

面向 **[Plasmod](https://github.com/CodeSoul-co/Plasmod)** 的 **Python HTTP SDK**：对齐服务端 **`docs/sdk/README.md`** 中的 **Tier A JSON** 与 **`/v1/internal/rpc/*`** 二进制帧（PLIB / PLQW / PLQB）；产品能力与路由总览见 **Plasmod 根目录 README**（链接见下）。

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
- **SDK / HTTP 契约（Tier A、二进制 RPC、OpenAPI 子集）**：[docs/sdk/README.md](https://github.com/CodeSoul-co/Plasmod/blob/main/docs/sdk/README.md)
- **本仓库已实现能力与测试说明**：[docs/SDK.md](docs/SDK.md)

## 快速用法

```python
from pyplasmod import PlasmodClient

client = PlasmodClient(base_url="http://127.0.0.1:8080")
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

## 异常

- **`PlasmodHttpError`**：HTTP 非成功响应（含 **`status_code`**、**`body`**、**`path`**）。
- **`ConnectError`**：连接级失败（由客户端在收到响应前抛出）。
- **`PlasmodException`**：其它 SDK 基类。

## 许可证

Apache 2.0（见仓库根目录 `LICENSE`）。
