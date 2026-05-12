# pyplasmod

面向 **[Plasmod](https://github.com/CodeSoul-co/Plasmod)** 的 Python **HTTP** SDK：用 `PlasmodClient` / `EasyPlasmod` 访问网关上的写入、检索与管理接口。服务端需已运行；请求与响应字段以 Plasmod **[HTTP API 文档](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api)** 为准。

Plasmod 面向多智能体场景，侧重事件化写入、物化检索与溯源；本包只做客户端封装，不包含服务端。

更完整的用法、方法表与排障说明见 **[docs/plans/pyplasmod-003-sdk-usage-guide.md](docs/plans/pyplasmod-003-sdk-usage-guide.md)**；示例见 **`examples/`**（如 `http_quickstart.py`、`ingest_fbin.py`、`batch_ingest.py`、`langchain_quickstart.py`）。

---

## 安装与环境

**要求：Python 3.8+**

```bash
pip install pyplasmod
```

可选依赖（LangChain `PlasmodVectorStore` 等）：

```bash
pip install pyplasmod[langchain]
```

**服务地址**（不设时客户端默认 `http://127.0.0.1:8080`）：

```bash
export PLASMOD_BASE_URL=http://127.0.0.1:8080   # 或 ANDB_BASE_URL
```

**管理接口**（`/v1/admin/*` 等）如需密钥，可用环境变量或在构造客户端时传入 `admin_key`：

```bash
export PLASMOD_ADMIN_API_KEY=你的密钥   # 或 ANDB_ADMIN_API_KEY
```

**请求超时（秒）**（可选）：

```bash
export PLASMOD_HTTP_TIMEOUT=30   # 或 ANDB_HTTP_TIMEOUT
```

**包内主题帮助**（终端快速查看常用 API 摘要）：

```bash
python -m pyplasmod              # 或: python -m pyplasmod easy
```

或在代码中：`from pyplasmod import plasmod_help; plasmod_help()`。

**本地开发**（克隆仓库后）：

```bash
pip install -e ".[dev]"
make unittest
```

---

## 相关链接

| 说明 | 链接 |
|------|------|
| SDK 与路由说明（Plasmod 仓库） | [docs/sdk/README.md](https://github.com/CodeSoul-co/Plasmod/blob/main/docs/sdk/README.md) |
| 本仓库用法与排障（长文档） | [docs/plans/pyplasmod-003-sdk-usage-guide.md](docs/plans/pyplasmod-003-sdk-usage-guide.md) |

## 许可证

MIT（见仓库根目录 `LICENSE`）。
