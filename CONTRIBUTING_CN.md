# 参与贡献 pyplasmod

> English version: [CONTRIBUTING.md](CONTRIBUTING.md)

**文档语言：** 仓库默认文档为英文（[README.md](README.md)、[docs/README.md](docs/README.md)）。可选中文见 [README.zh-CN.md](README.zh-CN.md) 与 [docs/zh-CN/](docs/zh-CN/)。新增面向用户的文档请优先写英文，并视需要同步更新中文译本。

**pyplasmod** 是 [Plasmod](https://github.com/CodeSoul-co/Plasmod) 的 Python **HTTP** 客户端仓库，刻意保持精简：Tier A JSON 接口 + 二进制 RPC 帧（`PLIB` / `PLQW` / `PLQB`）。本仓库**不包含** gRPC 栈或 collection/schema 类 ORM。

服务端侧的契约说明（路由、字段、OpenAPI 子集）以官方文档为准：

- [Plasmod HTTP API 文档（`docs/api`）](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api) — 入口见 [`overview.md`](https://github.com/CodeSoul-co/Plasmod/blob/main/docs/api/overview.md)

欢迎提交：缺陷修复、文档、测试，以及在**与上述契约一致**前提下的功能扩展。

## 如何贡献

1. 改动较大时，先在仓库提 [Issue](https://github.com/CodeSoul-co/pyplasmod/issues/new/choose) 讨论。
2. Fork 后从 **`dev`** 分支（或维护者指定的分支）创建功能分支。
3. PR 尽量聚焦，说明**改了什么**、**为什么**。
4. 本地通过 **`make unittest`** 与 **`make lint`**（见下）。

## 开发环境

环境要求：**Python 3.8+**。

```bash
pip install -e ".[dev]"
make unittest    # pytest，对 pyplasmod 做覆盖率
make lint        # black --check + ruff
```

可选一键格式化：

```bash
make format      # 会先 pip install -e ".[dev]"，再 black + ruff --fix
```

## 目录结构

| 路径 | 说明 |
|------|------|
| `pyplasmod/` | 包根目录（`http/` 客户端、二进制编解码、异常）。 |
| `pyplasmod/http/` | `PlasmodHttpClient`、`PlasmodHttpError`、PLIB/PLQW/PLQB 工具函数。 |
| `tests/` | 单元测试（`pytest`）。 |
| `examples/` | 可运行示例（如 HTTP 快速上手）。 |
| `docs/` | 可选设计备忘（`docs/plans/` 可能过时，以实现与服务端契约为准）。 |
| `pyproject.toml` | 项目元数据、运行时依赖（`requests`）、开发依赖 `[project.optional-dependencies] dev`。 |
| `Makefile` | `unittest`、`lint`、`format`、`install`。 |
| `OWNERS` | 部分流程下的 reviewer / approver 提示（若组织仍在使用）。 |

## 代码风格

- 与现有代码风格一致；提交前可用 **`make format`**。
- HTTP 路径与请求/响应形状尽量与服务端契约文档一致。
- 行为变更请补充或更新测试。

## PR 说明

- 有关联 Issue 时请写上链接。
- 避免在同一 PR 里夹杂无关的大范围重构。

### Commit message

建议使用清晰的中文或英文主题行；若团队采用 [Conventional Commits](https://www.conventionalcommits.org/)，便于浏览历史（例如 `fix(http): handle empty JSON body`）。

## 可选自动化

若启用 `.github/workflows/auto-cherrypick.yml` 且配置了密钥，合并后的 PR 可通过 `backport-to-<branch>` 等标签做自动 backport。若未使用该工作流，可忽略本节。

## 许可证

参与贡献即表示你同意将贡献内容以本仓库相同协议授权发布（**MIT License**，见根目录 `LICENSE`）。
