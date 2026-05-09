# Gateway Tier B HTTP shortcuts (`PlasmodHttpClient`)

- **Created:** 2026-05-08
- **Updated:** 2026-05-09
- **Author(s):** @CodeSoul-co

## Context

Plasmod exposes many JSON routes from `(*Gateway).RegisterRoutes` (see upstream `gateway.go`). Tier A in `pyplasmod-001` already covered ingest/query, a subset of admin, canonical CRUD, the internal memory algorithm bridge, and binary RPC helpers. Remaining routes—extra admin read/ops, internal task/plan/MAS, tool state, agent list, session context, eval ground truth, and test-only debug echo—were only reachable by calling `request_json` with raw paths. Tier B adds first-class methods on `PlasmodHttpClient` for those endpoints.

## Goals / Non-goals

- **Goals:** One thin `request_json` wrapper per remaining JSON route; predictable names aligned with URL semantics; minimal pytest coverage (mocked HTTP) for representative calls.
- **Non-goals:** Heavy request/response dataclasses or OpenAPI-generated clients; SSE / WAL streaming helpers; fixing incomplete local copies of `gateway.go` that may omit a handler implementation.

## Proposal

1. **Naming**  
   - Admin: `admin_{resource}_{action}`, e.g. `admin_topology_get`, `admin_consistency_mode_post`.  
   - Internal: `internal_{area}_{verb}`, consistent with existing `internal_memory_*`.  
   - Exception: `agent_list_get` maps to `GET /v1/agent/list` (not the `/v1/agents` CRUD pair).

2. **HTTP verbs**  
   Match each Plasmod handler: split read/write where the gateway uses both GET and POST (`governance_mode`, `runtime_mode`, `consistency_mode`, `algorithm_profile_mode`).

3. **Optional JSON body**  
   `admin_s3_export` and `admin_s3_snapshot_export` accept `body=None` so callers can POST with no JSON payload where the server allows an empty body.

4. **Tests**  
   In `tests/test_http_sdk.py`, assert method, path, and `json` / `params` for a small set of new APIs (admin topology + admin key header, task start, tool state query string, eval ground-truth GET).

## Alternatives

- **Single generic helper** `admin_request(subpath, ...)`: smaller surface area, but worse discoverability and no per-route docstrings in the IDE.  
- **OpenAPI-generated client**: higher maintenance and misaligned with the “thin HTTP SDK” direction.

## Open questions

- **`POST /v1/admin/s3/snapshot-export`**: If the upstream request schema evolves, document example bodies in release notes or upstream Plasmod docs rather than hard-coding types here.  
- **Admin key**: Today only `/v1/admin/*` receives `X-Admin-Key` automatically; if internal routes ever require auth, extend `_admin_headers` in `client.py` deliberately.

## Implementation status

- **Code:** `PlasmodHttpClient` in `pyplasmod/http/client.py` — section comment `Tier B: remaining Gateway.RegisterRoutes JSON surfaces`.  
- **Tests:** `tests/test_http_sdk.py` — route smoke tests for Tier B admin GET/POST, internal POST, S3 export with `json=None`, session context / eval / agent list GET.  
- **Example:** `examples/http_quickstart.py` — optional `PLASMOD_QUICKSTART_ADMIN=1` + admin key to call `admin_topology_get` against a live server.
