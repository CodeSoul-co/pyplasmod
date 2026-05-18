# Copyright (C) 2019-2021 Zilliz. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.

"""HTTP client for Plasmod (Tier A + Tier B JSON + binary RPC helpers)."""

from __future__ import annotations

import json
import os
from typing import Any, Iterator, List, Mapping, MutableMapping, Optional, Sequence
from urllib.parse import quote

import requests

from pyplasmod.batch import (
    DEFAULT_BATCH_SIZE,
    BatchResult,
    iter_batches,
    validate_batch_size,
)
from pyplasmod.exceptions import PlasmodException

from pyplasmod.http.binary import (
    decode_query_warm_batch_response,
    decode_query_warm_response,
    encode_ingest_batch,
    encode_query_warm,
    encode_query_warm_batch,
)
from pyplasmod.http.errors import PlasmodHttpError


def _iter_wal_sse_json_events(response: requests.Response) -> Iterator[dict[str, Any]]:
    """
    Parse Plasmod WAL SSE from ``handleWALStream`` (``event: wal`` + ``data:`` JSON lines).
    Comment heartbeats (``: ...``) are skipped.
    """
    event_type: Optional[str] = None
    data_parts: list[str] = []
    for line in response.iter_lines(decode_unicode=True):
        if line is None:
            continue
        line_str = line if isinstance(line, str) else line.decode("utf-8", errors="replace")
        if line_str == "":
            if event_type == "wal" and data_parts:
                payload = "\n".join(data_parts)
                try:
                    yield json.loads(payload)
                except ValueError:
                    yield {"_parse_error": True, "_raw": payload}
            event_type = None
            data_parts = []
            continue
        if line_str.startswith(":"):
            continue
        if line_str.startswith("event:"):
            event_type = line_str[6:].strip()
        elif line_str.startswith("data:"):
            data_parts.append(line_str[5:].lstrip())


def _merge_headers(
    base: Mapping[str, str],
    extra: Optional[Mapping[str, str]],
) -> dict[str, str]:
    out = dict(base)
    if extra:
        out.update(extra)
    return out


class PlasmodHttpClient:
    """
    Plasmod HTTP SDK client.

    **Tier A:** ingest/query, ``POST /v1/query/batch`` (warm batch ANN), core admin
    (warm prebuild, dataset delete,
    ``dataset_purge`` / ``admin_dataset_purge``, task status
    ``dataset_purge_task`` / ``admin_dataset_purge_task``,
    ``admin_memory_delete_by_source`` / ``admin_memory_purge_by_source``), warm-segment register,
    canonical CRUD, traces, internal memory algorithm
    bridge, and ``/v1/internal/rpc/*`` binary helpers.

    **Batch helpers:** ``ingest_batch``, ``add_vectors``, ``ingest_events``, and
    ``batch_query`` split large inputs using :mod:`pyplasmod.batch`.

    **Transport:** ``GET /v1/wal/stream`` (SSE) via :meth:`iter_wal_stream_events`.

    **Tier B:** remaining ``Gateway.RegisterRoutes`` JSON surfaces (extra admin
    read/write, internal task/plan/MAS, tool-state, agent list, session context,
    eval ground-truth, test-only ``/v1/debug/echo``).

    Admin routes ``/v1/admin/*`` automatically receive ``X-Admin-Key`` when
    ``admin_key`` or env ``PLASMOD_ADMIN_API_KEY`` / ``ANDB_ADMIN_API_KEY`` is set.

    When ``base_url`` is omitted, the client reads env ``PLASMOD_BASE_URL`` or
    ``ANDB_BASE_URL``, then falls back to ``http://127.0.0.1:8080`` (so the Plasmod
    process can listen on any host/port while callers only set the env).
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        timeout: Optional[float] = None,
        admin_key: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        if base_url is None:
            base_url = (
                os.environ.get("PLASMOD_BASE_URL")
                or os.environ.get("ANDB_BASE_URL")
                or "http://127.0.0.1:8080"
            )
        self.base_url = str(base_url).rstrip("/")
        env_timeout = os.environ.get("PLASMOD_HTTP_TIMEOUT") or os.environ.get(
            "ANDB_HTTP_TIMEOUT",
            "30",
        )
        self.timeout = float(timeout) if timeout is not None else float(env_timeout)
        self.admin_key = (
            admin_key
            if admin_key is not None
            else (
                os.environ.get("PLASMOD_ADMIN_API_KEY")
                or os.environ.get("ANDB_ADMIN_API_KEY")
                or ""
            )
        )
        self._session = session or requests.Session()
        self._owns_session = session is None

    def close(self) -> None:
        if self._owns_session:
            self._session.close()

    def __enter__(self) -> PlasmodHttpClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def _admin_headers(self, path: str, headers: Optional[Mapping[str, str]]) -> dict[str, str]:
        h = _merge_headers({}, headers)
        if path.startswith("/v1/admin/") and self.admin_key:
            h.setdefault("X-Admin-Key", self.admin_key)
        return h

    def request_json(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        """Send a JSON request; return parsed JSON or ``None`` for empty body."""
        hdrs = self._admin_headers(path, headers)
        hdrs.setdefault("Accept", "application/json")
        if json_body is not None:
            hdrs.setdefault("Content-Type", "application/json")
        url = self._url(path)
        try:
            resp = self._session.request(
                method.upper(),
                url,
                json=json_body,
                params=dict(params) if params is not None else None,
                headers=hdrs,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise PlasmodHttpError(
                0,
                reason=str(exc),
                body="",
                path=path,
            ) from exc

        return self._finish_json(resp, path)

    def request_bytes(
        self,
        method: str,
        path: str,
        *,
        data: bytes,
        headers: Optional[MutableMapping[str, str]] = None,
    ) -> tuple[int, bytes, Any]:
        """POST binary body; returns ``(status_code, response_body, response_headers)``."""
        hdrs: MutableMapping[str, str] = dict(headers or {})
        hdrs = self._admin_headers(path, hdrs)
        url = self._url(path)
        try:
            resp = self._session.request(
                method.upper(),
                url,
                data=data,
                headers=hdrs,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise PlasmodHttpError(
                0,
                reason=str(exc),
                body="",
                path=path,
            ) from exc
        return resp.status_code, resp.content, resp.headers

    def _finish_json(self, resp: requests.Response, path: str) -> Any:
        body_text = ""
        try:
            body_text = resp.text or ""
        except Exception:
            body_text = ""

        if not resp.ok:
            raise PlasmodHttpError(
                resp.status_code,
                reason=resp.reason or "",
                body=body_text,
                path=path,
                response_headers=resp.headers,
            )

        if not body_text.strip():
            return None
        ctype = (resp.headers.get("Content-Type") or "").lower()
        if "json" in ctype:
            return resp.json()
        try:
            return resp.json()
        except ValueError:
            return body_text

    # --- Tier A shortcuts -------------------------------------------------

    def health(self) -> Any:
        return self.request_json("GET", "/healthz")

    def system_mode(self) -> Any:
        """GET ``/v1/system/mode`` — ``app_mode``, ``debug_enabled``."""
        return self.request_json("GET", "/v1/system/mode")

    def ingest_event(self, event: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/ingest/events", json_body=dict(event))

    def ingest_vectors(
        self,
        vectors: Sequence[Sequence[float]],
        *,
        segment_id: str = "warm.default",
        object_ids: Optional[Sequence[str]] = None,
    ) -> Any:
        body: dict[str, Any] = {"segment_id": segment_id, "vectors": [list(row) for row in vectors]}
        if object_ids is not None:
            body["object_ids"] = list(object_ids)
        return self.request_json("POST", "/v1/ingest/vectors", json_body=body)

    def ingest_document(self, body: Mapping[str, Any]) -> Any:
        """
        POST ``/v1/ingest/document`` — chunk long text into episodic memory events.

        Fields mirror gateway: ``agent_id``, ``session_id``, ``workspace_id``, ``title``,
        ``text`` (required), ``chunk_size``, ``overlap``, ``importance``,
        ``upload_batch_id``, ``segment_index``, ``segment_total``.
        """
        return self.request_json("POST", "/v1/ingest/document", json_body=dict(body))

    def query(self, body: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/query", json_body=dict(body))

    def fetch_embedding_runtime(self, **kwargs: Any) -> Any:
        """
        Probe gateway embedding backend via a minimal ``POST /v1/query``.

        Returns :class:`~pyplasmod.embedding.runtime.EmbeddingRuntimeInfo`.
        Keyword args are forwarded to
        :func:`pyplasmod.embedding.runtime.fetch_embedding_runtime`
        (e.g. ``workspace_id``, ``query_text``).
        """
        from pyplasmod.embedding.runtime import fetch_embedding_runtime

        return fetch_embedding_runtime(self, **kwargs)

    def query_batch(self, body: Mapping[str, Any]) -> Any:
        """
        POST ``/v1/query/batch`` — warm-segment batch ANN over a vector matrix.

        JSON body matches Plasmod ``VectorWarmBatchQueryRequest``:

        - ``warm_segment_id`` (required), ``vectors`` (rows, same dim),
        - ``top_k`` (optional, default server 10),
        - ``agent_mode``: ``\"single_agent\"`` or ``\"multi_agent\"`` (required),
        - optional ``source_ids``, ``row_lineage``, ``search_raw``.

        Response shape: ``status``, ``rows``, ``by_source``, etc.
        """
        payload = dict(body)
        if "vectors" in payload:
            payload["vectors"] = [list(map(float, row)) for row in payload["vectors"]]
        return self.request_json("POST", "/v1/query/batch", json_body=payload)

    def admin_memory_delete_by_source(self, body: Mapping[str, Any]) -> Any:
        """
        POST ``/v1/admin/memory/delete-by-source`` — soft-delete memories whose
        ``source_event_ids`` matches ``reference_id`` / ``event_id`` / ``memory_id``.

        Body requires ``workspace_id`` and one of ``reference_id``, ``event_id``, ``memory_id``.
        Optional ``dry_run``.
        """
        return self.request_json(
            "POST",
            "/v1/admin/memory/delete-by-source",
            json_body=dict(body),
        )

    def admin_memory_purge_by_source(self, body: Mapping[str, Any]) -> Any:
        """
        POST ``/v1/admin/memory/purge-by-source`` — hard-delete / async purge by source ref.

        Body requires ``workspace_id`` and one of ``reference_id``, ``event_id``, ``memory_id``.
        Optional: ``dry_run``, ``only_if_inactive``, ``include_memory_ids``, ``async``,
        ``idempotency_key`` (see Plasmod ``handleMemoryPurgeBySource``).
        """
        return self.request_json(
            "POST",
            "/v1/admin/memory/purge-by-source",
            json_body=dict(body),
        )

    def iter_wal_stream_events(
        self,
        *,
        from_lsn: int = 0,
        heartbeat: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Iterator[dict[str, Any]]:
        """
        GET ``/v1/wal/stream`` — Server-Sent Events (``text/event-stream``).

        Yields decoded JSON objects from each ``event: wal`` frame (typically
        ``{\"lsn\": int, \"event\": ...}``). Heartbeat comment lines are ignored.

        Query params: ``from_lsn`` (optional), ``heartbeat`` (optional Go duration
        string, e.g. ``\"30s\"``).

        Uses streaming read with ``timeout=(connect_timeout, None)`` so long-lived
        tails are not cut by the default read timeout. The HTTP connection is
        closed when the iterator is exhausted or garbage-collected after ``close()``
        on the underlying response (consume or break out of the loop and ``close``).

        Yields:
            dict: Parsed ``data`` payload per WAL event.

        Raises:
            PlasmodHttpError: If the HTTP status is not successful before streaming.
        """
        path = "/v1/wal/stream"
        params: dict[str, str] = {}
        if from_lsn > 0:
            params["from_lsn"] = str(from_lsn)
        if heartbeat is not None and str(heartbeat).strip() != "":
            params["heartbeat"] = str(heartbeat)

        hdrs = self._admin_headers(path, headers)
        hdrs.setdefault("Accept", "text/event-stream")
        url = self._url(path)
        try:
            resp = self._session.get(
                url,
                params=params or None,
                headers=hdrs,
                stream=True,
                timeout=(self.timeout, None),
            )
        except requests.RequestException as exc:
            raise PlasmodHttpError(
                0,
                reason=str(exc),
                body="",
                path=path,
            ) from exc

        if not resp.ok:
            body_text = ""
            try:
                body_text = resp.text or ""
            except Exception:
                body_text = ""
            try:
                resp.close()
            except Exception:
                pass
            raise PlasmodHttpError(
                resp.status_code,
                reason=resp.reason or "",
                body=body_text,
                path=path,
                response_headers=resp.headers,
            )

        try:
            yield from _iter_wal_sse_json_events(resp)
        finally:
            try:
                resp.close()
            except Exception:
                pass

    def warm_prebuild(self) -> Any:
        return self.request_json("POST", "/v1/admin/warm/prebuild")

    def dataset_delete(self, body: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/admin/dataset/delete", json_body=dict(body))

    def dataset_purge(self, body: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/admin/dataset/purge", json_body=dict(body))

    def dataset_purge_task(self, task_id: str) -> Any:
        return self.request_json(
            "GET",
            "/v1/admin/dataset/purge/task",
            params={"task_id": task_id},
        )

    def admin_dataset_purge(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/admin/dataset/purge`` — same as :meth:`dataset_purge`."""
        return self.dataset_purge(body)

    def admin_dataset_purge_task(self, task_id: str) -> Any:
        """GET ``/v1/admin/dataset/purge/task`` — same as :meth:`dataset_purge_task`."""
        return self.dataset_purge_task(task_id)

    def warm_segment_register(self, body: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/internal/warm-segment/register", json_body=dict(body))

    def rpc_ingest_batch(
        self,
        segment_id: str,
        vectors: Sequence[Sequence[float]],
        object_ids: Optional[Sequence[str]] = None,
        *,
        wire_version: int = 1,
    ) -> Any:
        payload = encode_ingest_batch(
            segment_id,
            vectors,
            object_ids,
            wire_version=wire_version,
        )
        status, raw, _hdrs = self.request_bytes(
            "POST",
            "/v1/internal/rpc/ingest_batch",
            data=payload,
            headers={"Content-Type": "application/octet-stream"},
        )
        path = "/v1/internal/rpc/ingest_batch"
        body_text = raw.decode("utf-8", errors="replace") if raw else ""
        if status != 200:
            raise PlasmodHttpError(
                status,
                reason="ingest_batch failed",
                body=body_text,
                path=path,
            )
        if not raw.strip():
            return None
        try:
            return json.loads(body_text)
        except ValueError:
            return body_text

    def rpc_query_warm(self, segment_id: str, top_k: int, vector: Sequence[float]) -> Any:
        payload = encode_query_warm(segment_id, top_k, vector)
        status, raw, _ = self.request_bytes(
            "POST",
            "/v1/internal/rpc/query_warm",
            data=payload,
            headers={"Content-Type": "application/octet-stream"},
        )
        if status != 200:
            raise PlasmodHttpError(
                status,
                reason="query_warm failed",
                body=raw.decode("utf-8", errors="replace"),
                path="/v1/internal/rpc/query_warm",
            )
        return decode_query_warm_response(raw)

    def _rpc_query_warm_batch_response(
        self,
        path: str,
        payload: bytes,
        *,
        error_label: str,
    ) -> tuple[int, int, list[int], list[float]]:
        status, raw, _ = self.request_bytes(
            "POST",
            path,
            data=payload,
            headers={"Content-Type": "application/octet-stream"},
        )
        if status != 200:
            raise PlasmodHttpError(
                status,
                reason=error_label,
                body=raw.decode("utf-8", errors="replace"),
                path=path,
            )
        return decode_query_warm_batch_response(raw)

    def rpc_query_warm_batch(
        self,
        segment_id: str,
        top_k: int,
        queries: Sequence[Sequence[float]],
    ) -> tuple[int, int, list[int], list[float]]:
        payload = encode_query_warm_batch(segment_id, top_k, queries)
        return self._rpc_query_warm_batch_response(
            "/v1/internal/rpc/query_warm_batch",
            payload,
            error_label="query_warm_batch failed",
        )

    def rpc_query_warm_batch_raw(
        self,
        segment_id: str,
        top_k: int,
        queries: Sequence[Sequence[float]],
    ) -> tuple[int, int, list[int], list[float]]:
        """
        POST ``/v1/internal/rpc/query_warm_batch_raw`` — same PLQB body as ``query_warm_batch``;
        server uses ``SearchWarmSegmentBatchRaw`` (no plugin path).
        """
        payload = encode_query_warm_batch(segment_id, top_k, queries)
        return self._rpc_query_warm_batch_response(
            "/v1/internal/rpc/query_warm_batch_raw",
            payload,
            error_label="query_warm_batch_raw failed",
        )

    def rpc_unload_segment(self, segment_id: str) -> Any:
        return self.request_json(
            "POST",
            "/v1/internal/rpc/unload_segment",
            json_body={"segment_id": segment_id},
        )

    def rpc_register_warm(self, body: Mapping[str, Any]) -> Any:
        return self.request_json(
            "POST",
            "/v1/internal/rpc/register_warm",
            json_body=dict(body),
        )

    # --- Canonical CRUD (GET list / filter + POST create or replace) -------

    def agents_get(self, params: Optional[Mapping[str, Any]] = None) -> Any:
        return self.request_json("GET", "/v1/agents", params=params)

    def agents_post(self, body: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/agents", json_body=dict(body))

    def sessions_get(self, params: Optional[Mapping[str, Any]] = None) -> Any:
        return self.request_json("GET", "/v1/sessions", params=params)

    def sessions_post(self, body: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/sessions", json_body=dict(body))

    def memory_get(self, params: Optional[Mapping[str, Any]] = None) -> Any:
        return self.request_json("GET", "/v1/memory", params=params)

    def memory_post(self, body: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/memory", json_body=dict(body))

    def states_get(self, params: Optional[Mapping[str, Any]] = None) -> Any:
        return self.request_json("GET", "/v1/states", params=params)

    def states_post(self, body: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/states", json_body=dict(body))

    def artifacts_get(self, params: Optional[Mapping[str, Any]] = None) -> Any:
        return self.request_json("GET", "/v1/artifacts", params=params)

    def artifacts_post(self, body: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/artifacts", json_body=dict(body))

    def edges_get(self, params: Optional[Mapping[str, Any]] = None) -> Any:
        return self.request_json("GET", "/v1/edges", params=params)

    def edges_post(self, body: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/edges", json_body=dict(body))

    def policies_get(self, params: Optional[Mapping[str, Any]] = None) -> Any:
        return self.request_json("GET", "/v1/policies", params=params)

    def policies_post(self, body: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/policies", json_body=dict(body))

    def share_contracts_get(self, params: Optional[Mapping[str, Any]] = None) -> Any:
        return self.request_json("GET", "/v1/share-contracts", params=params)

    def share_contracts_post(self, body: Mapping[str, Any]) -> Any:
        return self.request_json("POST", "/v1/share-contracts", json_body=dict(body))

    # --- P2: traces + Agent internal memory bridge -------------------------

    def traces_get(self, object_id: str) -> Any:
        """
        GET ``/v1/traces/{object_id}`` — assembled proof trace (JSON).

        ``object_id`` is URL-encoded as a single path segment (slashes etc.).
        """
        enc = quote(object_id, safe="")
        return self.request_json("GET", f"/v1/traces/{enc}")

    def internal_memory_recall(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/memory/recall``."""
        return self.request_json("POST", "/v1/internal/memory/recall", json_body=dict(body))

    def internal_memory_ingest(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/memory/ingest``."""
        return self.request_json("POST", "/v1/internal/memory/ingest", json_body=dict(body))

    def internal_memory_compress(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/memory/compress``."""
        return self.request_json("POST", "/v1/internal/memory/compress", json_body=dict(body))

    def internal_memory_summarize(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/memory/summarize``."""
        return self.request_json("POST", "/v1/internal/memory/summarize", json_body=dict(body))

    def internal_memory_decay(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/memory/decay``."""
        return self.request_json("POST", "/v1/internal/memory/decay", json_body=dict(body))

    def internal_memory_share(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/memory/share``."""
        return self.request_json("POST", "/v1/internal/memory/share", json_body=dict(body))

    def internal_memory_conflict_resolve(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/memory/conflict/resolve``."""
        return self.request_json(
            "POST",
            "/v1/internal/memory/conflict/resolve",
            json_body=dict(body),
        )

    def internal_memory_stale(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/memory/stale`` — mark memory stale (lifecycle)."""
        return self.request_json("POST", "/v1/internal/memory/stale", json_body=dict(body))

    def internal_memory_conflict_inject(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/memory/conflict/inject`` — test / MAS conflict synthesis."""
        return self.request_json(
            "POST",
            "/v1/internal/memory/conflict/inject",
            json_body=dict(body),
        )

    # --- Tier B: remaining ``Gateway.RegisterRoutes`` JSON surfaces ---------

    def admin_topology_get(self) -> Any:
        """GET ``/v1/admin/topology`` — runtime topology JSON."""
        return self.request_json("GET", "/v1/admin/topology")

    def admin_storage_get(self) -> Any:
        """GET ``/v1/admin/storage`` — resolved storage backend snapshot."""
        return self.request_json("GET", "/v1/admin/storage")

    def admin_config_effective_get(self) -> Any:
        """GET ``/v1/admin/config/effective`` — effective algorithm-related config."""
        return self.request_json("GET", "/v1/admin/config/effective")

    def admin_s3_export(self, body: Optional[Mapping[str, Any]] = None) -> Any:
        """POST ``/v1/admin/s3/export`` — dev S3 round-trip sample (optional JSON body)."""
        return self.request_json(
            "POST",
            "/v1/admin/s3/export",
            json_body=None if body is None else dict(body),
        )

    def admin_s3_snapshot_export(self, body: Optional[Mapping[str, Any]] = None) -> Any:
        """POST ``/v1/admin/s3/snapshot-export``."""
        return self.request_json(
            "POST",
            "/v1/admin/s3/snapshot-export",
            json_body=None if body is None else dict(body),
        )

    def admin_s3_cold_purge(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/admin/s3/cold-purge`` — requires ``confirm`` per gateway."""
        return self.request_json("POST", "/v1/admin/s3/cold-purge", json_body=dict(body))

    def admin_data_wipe(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/admin/data/wipe`` — destructive; ``confirm`` must match server token."""
        return self.request_json("POST", "/v1/admin/data/wipe", json_body=dict(body))

    def admin_rollback(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/admin/rollback`` — reactivate / deactivate a single memory."""
        return self.request_json("POST", "/v1/admin/rollback", json_body=dict(body))

    def admin_replay(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/admin/replay`` — WAL replay preview or apply (see Plasmod gateway)."""
        return self.request_json("POST", "/v1/admin/replay", json_body=dict(body))

    def admin_consistency_mode_get(self) -> Any:
        """GET ``/v1/admin/consistency-mode``."""
        return self.request_json("GET", "/v1/admin/consistency-mode")

    def admin_consistency_mode_post(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/admin/consistency-mode`` — set ``mode`` JSON field."""
        return self.request_json("POST", "/v1/admin/consistency-mode", json_body=dict(body))

    def admin_metrics_get(self, params: Optional[Mapping[str, Any]] = None) -> Any:
        """GET ``/v1/admin/metrics`` — optional ``storage=true`` query param."""
        return self.request_json("GET", "/v1/admin/metrics", params=params)

    def admin_governance_mode_get(self) -> Any:
        """GET ``/v1/admin/governance-mode``."""
        return self.request_json("GET", "/v1/admin/governance-mode")

    def admin_governance_mode_post(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/admin/governance-mode`` — ``{"enabled": bool}`` toggles enforcement."""
        return self.request_json("POST", "/v1/admin/governance-mode", json_body=dict(body))

    def admin_runtime_mode_get(self) -> Any:
        """GET ``/v1/admin/runtime-mode``."""
        return self.request_json("GET", "/v1/admin/runtime-mode")

    def admin_runtime_mode_post(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/admin/runtime-mode`` — vector_only / minimal / governance flags."""
        return self.request_json("POST", "/v1/admin/runtime-mode", json_body=dict(body))

    def admin_algorithm_profile_mode_get(self) -> Any:
        """GET ``/v1/admin/memory/providers/mode`` — memory backend profile mode."""
        return self.request_json("GET", "/v1/admin/memory/providers/mode")

    def admin_algorithm_profile_mode_post(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/admin/memory/providers/mode``."""
        return self.request_json("POST", "/v1/admin/memory/providers/mode", json_body=dict(body))

    def admin_algorithm_profile_health_get(self) -> Any:
        """GET ``/v1/admin/memory/providers/health``."""
        return self.request_json("GET", "/v1/admin/memory/providers/health")

    def internal_task_start(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/task/start``."""
        return self.request_json("POST", "/v1/internal/task/start", json_body=dict(body))

    def internal_task_complete(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/task/complete``."""
        return self.request_json("POST", "/v1/internal/task/complete", json_body=dict(body))

    def internal_task_tokens(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/task/tokens``."""
        return self.request_json("POST", "/v1/internal/task/tokens", json_body=dict(body))

    def internal_task_claim(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/task/claim``."""
        return self.request_json("POST", "/v1/internal/task/claim", json_body=dict(body))

    def internal_task_stage(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/task/stage`` — multi-stage report progress."""
        return self.request_json("POST", "/v1/internal/task/stage", json_body=dict(body))

    def internal_plan_step(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/plan/step``."""
        return self.request_json("POST", "/v1/internal/plan/step", json_body=dict(body))

    def internal_plan_repair(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/plan/repair``."""
        return self.request_json("POST", "/v1/internal/plan/repair", json_body=dict(body))

    def internal_mas_answer_consistency(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/mas/answer-consistency``."""
        return self.request_json(
            "POST",
            "/v1/internal/mas/answer-consistency",
            json_body=dict(body),
        )

    def internal_mas_aggregate(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/mas/aggregate``."""
        return self.request_json("POST", "/v1/internal/mas/aggregate", json_body=dict(body))

    def internal_tool_state_get(self, params: Optional[Mapping[str, Any]] = None) -> Any:
        """GET ``/v1/internal/tool-state`` — optional ``agent_id`` / ``session_id`` query params."""
        return self.request_json(
            "GET",
            "/v1/internal/tool-state",
            params=dict(params) if params is not None else None,
        )

    def internal_agent_handoff(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/agent/handoff``."""
        return self.request_json("POST", "/v1/internal/agent/handoff", json_body=dict(body))

    def agent_list_get(self, params: Optional[Mapping[str, Any]] = None) -> Any:
        """GET ``/v1/agent/list`` — optional ``role``, ``workspace_id``, ``tenant_id`` filters."""
        return self.request_json("GET", "/v1/agent/list", params=params)

    def internal_session_context_get(self, params: Mapping[str, Any]) -> Any:
        """GET ``/v1/internal/session/context`` — requires ``session_id``; optional ``agent_id``, ``last_n``."""
        return self.request_json("GET", "/v1/internal/session/context", params=dict(params))

    def internal_eval_ground_truth_get(self, params: Optional[Mapping[str, Any]] = None) -> Any:
        """GET ``/v1/internal/eval/ground-truth`` — optional ``task_id``; omit to list all."""
        return self.request_json("GET", "/v1/internal/eval/ground-truth", params=params)

    def internal_eval_ground_truth_post(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/internal/eval/ground-truth`` — register expected answer for eval harness."""
        return self.request_json(
            "POST",
            "/v1/internal/eval/ground-truth",
            json_body=dict(body),
        )

    def debug_echo(self, body: Mapping[str, Any]) -> Any:
        """POST ``/v1/debug/echo`` — only registered when Plasmod runs in test mode."""
        return self.request_json("POST", "/v1/debug/echo", json_body=dict(body))

    # --- Batch ingestion with automatic splitting -----------------------------------

    def ingest_batch(
        self,
        segment_id: str,
        vectors: Sequence[Sequence[float]],
        object_ids: Optional[Sequence[str]] = None,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
        wire_version: int = 1,
        raise_on_error: bool = True,
    ) -> BatchResult:
        """
        Ingest vectors in batches, automatically splitting large inputs.

        This method wraps ``rpc_ingest_batch`` and splits the input into smaller
        batches to avoid memory issues when ingesting large amounts of data.

        Args:
            segment_id: Target segment identifier.
            vectors: Sequence of vectors to ingest.
            object_ids: Optional sequence of object IDs (must match vectors length).
            batch_size: Maximum number of vectors per batch. Defaults to 500.
            wire_version: Binary wire protocol version (1 or 2).
            raise_on_error: If True, raise exception on first batch failure.
                           If False, collect errors and continue.

        Returns:
            BatchResult containing total_count, accepted_count, failed_count,
            batch_count, memory_ids, and errors.

        Raises:
            PlasmodException: If raise_on_error is True and any batch fails.
            ValueError: If batch_size < 1 or object_ids length doesn't match vectors.
        """
        batch_size = validate_batch_size(batch_size)
        n = len(vectors)

        if n == 0:
            return BatchResult(total_count=0, batch_count=0)

        if object_ids is not None and len(object_ids) != n:
            raise ValueError("object_ids length must match vectors length")

        result = BatchResult(total_count=n)

        for batch_idx, batch_vectors in enumerate(iter_batches(vectors, batch_size)):
            batch_start = batch_idx * batch_size
            batch_end = batch_start + len(batch_vectors)

            batch_ids: Optional[List[str]] = None
            if object_ids is not None:
                batch_ids = list(object_ids[batch_start:batch_end])

            try:
                resp = self.rpc_ingest_batch(
                    segment_id,
                    batch_vectors,
                    batch_ids,
                    wire_version=wire_version,
                )
                result.batch_count += 1
                result.accepted_count += len(batch_vectors)

                # Extract memory_ids from response if available
                if isinstance(resp, dict):
                    if "memory_ids" in resp:
                        result.memory_ids.extend(resp["memory_ids"])
                    elif "object_ids" in resp:
                        result.memory_ids.extend(resp["object_ids"])

            except Exception as e:
                result.batch_count += 1
                result.failed_count += len(batch_vectors)
                error_info = {
                    "batch_index": batch_idx,
                    "batch_start": batch_start,
                    "batch_end": batch_end,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                result.errors.append(error_info)

                if raise_on_error:
                    raise PlasmodException(
                        f"Batch {batch_idx} failed (items {batch_start}-{batch_end}): {e}"
                    ) from e

        return result

    def add_vectors(
        self,
        vectors: Sequence[Sequence[float]],
        *,
        segment_id: str = "warm.default",
        object_ids: Optional[Sequence[str]] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        raise_on_error: bool = True,
    ) -> BatchResult:
        """
        Add vectors to a segment with automatic batching.

        This is a convenience wrapper around ``ingest_batch`` that provides
        a simpler interface for adding vectors.

        Args:
            vectors: Sequence of vectors to add.
            segment_id: Target segment identifier. Defaults to "warm.default".
            object_ids: Optional sequence of object IDs.
            batch_size: Maximum number of vectors per batch.
            raise_on_error: If True, raise exception on first batch failure.

        Returns:
            BatchResult with ingestion statistics.
        """
        return self.ingest_batch(
            segment_id,
            vectors,
            object_ids,
            batch_size=batch_size,
            raise_on_error=raise_on_error,
        )

    def ingest_events(
        self,
        events: Sequence[Mapping[str, Any]],
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
        raise_on_error: bool = True,
    ) -> BatchResult:
        """
        Ingest multiple events in batches.

        Args:
            events: Sequence of event dictionaries to ingest.
            batch_size: Maximum number of events per batch.
            raise_on_error: If True, raise exception on first event failure.

        Returns:
            BatchResult with ingestion statistics.
        """
        batch_size = validate_batch_size(batch_size)
        n = len(events)

        if n == 0:
            return BatchResult(total_count=0, batch_count=0)

        result = BatchResult(total_count=n)

        for batch_idx, batch_events in enumerate(iter_batches(events, batch_size)):
            batch_start = batch_idx * batch_size

            for event_idx, event in enumerate(batch_events):
                try:
                    resp = self.ingest_event(event)
                    result.accepted_count += 1

                    # Extract memory_id from response if available
                    if isinstance(resp, dict):
                        if "memory_id" in resp:
                            result.memory_ids.append(resp["memory_id"])
                        elif "event_id" in resp:
                            result.memory_ids.append(resp["event_id"])

                except Exception as e:
                    result.failed_count += 1
                    error_info = {
                        "batch_index": batch_idx,
                        "event_index": batch_start + event_idx,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                    result.errors.append(error_info)

                    if raise_on_error:
                        raise PlasmodException(
                            f"Event {batch_start + event_idx} failed: {e}"
                        ) from e

            result.batch_count += 1

        return result

    def batch_query(
        self,
        queries: Sequence[Mapping[str, Any]],
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> List[Any]:
        """
        Execute multiple queries in batches.

        Args:
            queries: Sequence of query dictionaries.
            batch_size: Maximum number of queries per batch.

        Returns:
            List of query results in the same order as input queries.
        """
        batch_size = validate_batch_size(batch_size)
        results: List[Any] = []

        for batch_queries in iter_batches(queries, batch_size):
            for query in batch_queries:
                resp = self.query(query)
                results.append(resp)

        return results
