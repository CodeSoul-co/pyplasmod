# PyPlasmod — Python SDK for [Plasmod](https://github.com/CodeSoul-co/Plasmod)

PyPlasmod 是本仓库对 **[PyPlasmod](https://github.com/plasmod-io/pyplasmod)** 的衍生发行：包名与导入路径已统一为 **`pyplasmod`**，面向 **[Plasmod](https://github.com/CodeSoul-co/Plasmod)** 多智能体原生数据库项目的 SDK 演进。

**Plasmod 是什么**  
Plasmod 面向多智能体系统，将认知对象存储、事件驱动的物化与结构化证据检索整合在可运行的系统中。

**当前 SDK 状态说明**

- 代码主体仍沿用 **Plasmod gRPC / plasmod-proto** 生成的客户端栈（`pyplasmod/grpc_gen/plasmod_pb2*.py`），可与 **Plasmod 2.x** 等同协议的服务端通信。
- 向 **Plasmod 原生 HTTP API**（如 `README-Plasmod.md` 中的 `/v1/ingest/events`、`/v1/query` 等）迁移的工作可在后续迭代中逐步替换本层实现；本次变更重点是 **命名空间与品牌** 与默认文档对齐。

## 安装

需要 **Python 3.8+**。

```bash
pip install pyplasmod
pip install "pyplasmod[model]"       # 可选：安装 PyPI ``plasmod-model``（导入仍为 ``pyplasmod.model.*``，待上游提供 pyplasmod 命名空间后可对齐）
pip install "pyplasmod[bulk_writer]"
pip install "pyplasmod[plasmod_lite]"  # 可选：本地 plasmod-lite（非 Windows）
```

从源码安装：

```bash
git clone <你的 pyplasmod 仓库 URL>
cd pyplasmod
pip install -e ".[dev]"
```

## 环境变量（连接默认值）

优先使用 **`PLASMOD_*`**，并兼容旧的 **`MILVUS_*`**（便于从 pyplasmod 迁移）：

| 变量 | 含义 |
|------|------|
| `PLASMOD_URI` / `PLASMOD_URI` | 默认连接 URI |
| `PLASMOD_CONN_ALIAS` / `MILVUS_CONN_ALIAS` | 默认连接别名 |
| `PLASMOD_CONN_TIMEOUT` / `MILVUS_CONN_TIMEOUT` | 连接超时（秒） |

## 快速示例

```python
from pyplasmod import PlasmodClient

client = PlasmodClient(uri="http://127.0.0.1:19530")
# 其余 Collection / 向量检索 API 与 pyplasmod 时代用法一致，仅导入改为 pyplasmod
```

异步客户端：`from pyplasmod import AsyncPlasmodClient`。

异常类型：`PlasmodException`、`PlasmodUnavailableException`。

## 开发与测试

```bash
make install    # pip install -e .
make lint
make format
make unittest
```

生成 proto（需初始化 submodule）：

```bash
git submodule update --init
make gen_proto
```

Proto 来源仍为 [plasmod-io/plasmod-proto](https://github.com/plasmod-io/plasmod-proto)；生成脚本位于 `pyplasmod/grpc_gen/python_gen.sh`。

## 文档与路线图

- **Plasmod 服务端与架构**：<https://github.com/CodeSoul-co/Plasmod>  
- **本仓库详细产品说明**：[`README-Plasmod.md`](README-Plasmod.md)  

## 许可证

沿用上游 pyplasmod 的开源许可证（见仓库根目录 `LICENSE`）。
