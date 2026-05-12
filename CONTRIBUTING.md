# Contributing to pyplasmod

> Chinese version: [CONTRIBUTING_CN.md](CONTRIBUTING_CN.md)

**pyplasmod** is the Python **HTTP** client for [Plasmod](https://github.com/CodeSoul-co/Plasmod). This repository intentionally stays small: JSON Tier A routes plus binary RPC framing (`PLIB` / `PLQW` / `PLQB`). There is **no** gRPC stack or Milvus-compatible ORM here.

The authoritative API contract lives in the server repo:

- [Plasmod HTTP API docs (`docs/api`)](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api) — start with [`overview.md`](https://github.com/CodeSoul-co/Plasmod/blob/main/docs/api/overview.md)

Contributions are welcome: bug fixes, docs, tests, and careful extensions that stay aligned with that contract.

## How to contribute

1. Open an [issue](https://github.com/CodeSoul-co/pyplasmod/issues/new/choose) for bugs or feature discussion when the change is non-trivial.
2. Fork the repo and create a branch from **`dev`** (or the branch maintainers ask you to target).
3. Keep PRs focused; describe **what** changed and **why**.
4. Ensure **`make unittest`** and **`make lint`** pass (see below).

## Development setup

Requirements: **Python 3.8+**.

```bash
pip install -e ".[dev]"
make unittest    # pytest + coverage on pyplasmod
make lint        # black --check + ruff
```

Auto-format (optional):

```bash
make format      # pip install -e ".[dev]" then black + ruff --fix
```

## Repository layout

| Path | Purpose |
|------|---------|
| `pyplasmod/` | Package root (`http/` client, binary codecs, exceptions). |
| `pyplasmod/http/` | `PlasmodHttpClient`, `PlasmodHttpError`, PLIB/PLQW/PLQB helpers. |
| `tests/` | Unit tests (`pytest`). |
| `examples/` | Runnable samples (e.g. HTTP quickstart). |
| `docs/` | Optional design notes (`docs/plans/` may be outdated—prefer server contract doc). |
| `pyproject.toml` | Project metadata, runtime deps (`requests`), optional `[project.optional-dependencies] dev`. |
| `Makefile` | `unittest`, `lint`, `format`, `install`. |
| `OWNERS` | Reviewer / approver hints for some workflows (if used by your org). |

## Style

- Match existing formatting; **`make format`** should leave the tree clean.
- Prefer explicit HTTP paths and types consistent with the server contract doc.
- Add or update tests for behavior changes.

## Pull requests

- Link related issues when applicable.
- Avoid unrelated drive-by refactors in the same PR.

### Commit messages

Clear, imperative subject line (e.g. `fix(http): handle empty JSON body`). Optional [Conventional Commits](https://www.conventionalcommits.org/) style helps changelog scanning.

## Optional automation

If `.github/workflows/auto-cherrypick.yml` is enabled and secrets are configured, backports may use `backport-to-<branch>` labels on merged PRs. If that workflow is unused, ignore this section.

## License

By contributing, you agree your contributions are under the same license as this project (**MIT License**—see `LICENSE`).
