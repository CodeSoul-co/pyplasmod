# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- PyPI packaging metadata (`keywords`, documentation URLs, `py.typed`).
- `NOTICE` for MIT distribution with Apache 2.0–attributed source portions.
- Warm ANN index selection on `PlasmodHttpClient.ingest_vectors` (`index_type`, IVF tuning fields) via `pyplasmod.http.warm_index` helpers and root-package exports (`WARM_INDEX_*`, `normalize_warm_index_type`, `warm_index_ingest_fields`).

## [0.1.0] - TBD

### Added

- HTTP Tier A client (`PlasmodHttpClient` / `PlasmodClient`).
- Binary RPC helpers (PLIB / PLQW / PLQB).
- `EasyPlasmod` convenience API (health, search, ingest, memories, `.fbin` upload).
- Gateway embedding helpers (`PlasmodEmbedding`, CPU/GPU runtime configuration).
- Optional LangChain vector store integration (`pip install pyplasmod[langchain]`).
- CLI and `plasmod_help()` topic index.

[Unreleased]: https://github.com/CodeSoul-co/pyplasmod/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/CodeSoul-co/pyplasmod/releases/tag/v0.1.0
