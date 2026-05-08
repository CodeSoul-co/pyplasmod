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

"""HTTP client for Plasmod (Tier A JSON + binary RPC helpers)."""

from __future__ import annotations

import json
import os
from typing import Any, Mapping, MutableMapping, Optional, Sequence

import requests

from pyplasmod.http.binary import (
    decode_query_warm_batch_response,
    decode_query_warm_response,
    encode_ingest_batch,
    encode_query_warm,
    encode_query_warm_batch,
)
from pyplasmod.http.errors import PlasmodHttpError


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
    Plasmod HTTP SDK client (JSON ingest/query/admin + optional binary RPC).

    Admin routes ``/v1/admin/*`` automatically receive ``X-Admin-Key`` when
    ``admin_key`` or env ``PLASMOD_ADMIN_API_KEY`` / ``ANDB_ADMIN_API_KEY`` is set.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        *,
        timeout: Optional[float] = None,
        admin_key: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
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
