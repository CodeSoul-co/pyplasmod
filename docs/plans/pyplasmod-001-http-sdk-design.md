# HTTP SDK (Tier A + binary RPC)

- **Created:** 2026-05-06
- **Updated:** 2026-05-06
- **Author(s):** @CodeSoul-co

## Context

`pyplasmod` is a small Python client for [Plasmod](https://github.com/CodeSoul-co/Plasmod) over **HTTP only**. The server contract (routes, JSON fields) is documented under Plasmod [`docs/api`](https://github.com/CodeSoul-co/Plasmod/tree/main/docs/api) (see [`overview.md`](https://github.com/CodeSoul-co/Plasmod/blob/main/docs/api/overview.md)); binary RPC frame layouts live in server source (for example `src/internal/transport/framing.go`). Those remain the source of truth. This design records how the Python package maps to that contract.

## Goals / Non-goals

- **Goals:**
  - Expose a single high-level client (`PlasmodHttpClient`, aliased as `PlasmodClient`) for Tier A JSON endpoints and selected `/v1/internal/rpc/*` calls.
  - Provide reusable **PLIB / PLQW / PLQB** encode and decode helpers aligned with `src/internal/transport/framing.go` on the server.
  - Keep the install surface minimal: runtime dependency on `requests` only.
- **Non-goals:**
  - gRPC, Milvus-compatible ORM, or collection/schema management APIs.
  - Duplicating the full OpenAPI; link to Plasmod `docs/api` instead.

**Implemented in client (evolving):** P0 `system_mode`, `ingest_document`, `rpc_query_warm_batch_raw`; P1 canonical CRUD `*_get` / `*_post` for agents, sessions, memory, states, artifacts, edges, policies, share-contracts; P2 `traces_get` plus `internal_memory_*` for `/v1/internal/memory/*` (Agent bridge). `milvus_compat` remains out of scope for the slim client.

## Proposal

### Module layout

| Module | Responsibility |
|--------|------------------|
| `pyplasmod.http.client` | `PlasmodHttpClient`: `request_json`, `request_bytes`, Tier A shortcuts, `rpc_*` methods. |
| `pyplasmod.http.binary` | Wire encoders/decoders for ingest batch and warm query batch paths. |
| `pyplasmod.http.errors` | `PlasmodHttpError` for failed HTTP or pre-response transport errors. |
| `pyplasmod.exceptions` | Shared base and typed errors for future use. |
| `pyplasmod` (package `__init__`) | Re-exports client, errors, and binary helpers; `__version__` from package metadata. |

### Configuration

- **Base URL:** constructor `base_url` (default `http://127.0.0.1:8080`).
- **Timeout:** `PLASMOD_HTTP_TIMEOUT` or `ANDB_HTTP_TIMEOUT` (seconds), overridable by `timeout=`.
- **Admin:** `PLASMOD_ADMIN_API_KEY` or `ANDB_ADMIN_API_KEY`, or `admin_key=`; applied as `X-Admin-Key` for paths under `/v1/admin/`.

### Error model

Failures from `requests` before a normal response, non-2xx JSON responses, and non-200 responses from selected binary RPC helpers raise **`PlasmodHttpError`** with `status_code`, `path`, and optional `body`.

## Alternatives

- **Generated OpenAPI client:** More boilerplate and churn; rejected until the contract stabilizes and codegen is maintained in CI.
- **Keeping gRPC alongside HTTP:** Conflicts with HTTP-only Plasmod deployment story; removed from this repository.

## Open questions

- Whether to map certain HTTP statuses to `ConnectError` / `PlasmodUnavailableException` automatically for ergonomics.
- Whether to add optional `httpx` / async client behind an extra.
