# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""High-level :class:`PlasmodClient` (MilvusClient-style entry point)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Union
from urllib.parse import urlparse

import requests

from pyplasmod.data import build_query_body
from pyplasmod.http.client import PlasmodHttpClient
from pyplasmod.http.errors import PlasmodHttpError
from pyplasmod.http.warm_index import WARM_INDEX_HNSW, normalize_warm_index_type

# Published Docker image (split: mgmt 9091, API 19530).
DEFAULT_DOCKER_IMAGE = "oneflybird/plasmod"
DEFAULT_API_URI = "http://127.0.0.1:19530"
DEFAULT_UNIFIED_URI = "http://127.0.0.1:8080"
_PROFILE_SUFFIXES = (".db", ".json")


def _looks_like_url(value: str) -> bool:
    v = value.strip().lower()
    return v.startswith("http://") or v.startswith("https://")


def _looks_like_profile_path(value: str) -> bool:
    v = value.strip()
    if any(v.endswith(s) for s in _PROFILE_SUFFIXES):
        return True
    return "/" in v or "\\" in v or v.startswith(".")


def _resolve_base_url(
  uri: Optional[str],
  *,
  base_url: Optional[str],
) -> tuple[str, Optional[Path]]:
    """
    Return ``(http_base_url, profile_path_or_none)``.

    * Positional / ``uri`` ending in ``.db`` or ``.json`` → load or create a local profile file.
    * HTTP(S) string → remote gateway.
    * Empty → env ``PLASMOD_BASE_URL`` / ``ANDB_BASE_URL``, then :data:`DEFAULT_API_URI`.
    """
    if base_url is not None:
        return str(base_url).rstrip("/"), None

    raw = (uri or "").strip()
    if not raw:
        env = os.environ.get("PLASMOD_BASE_URL") or os.environ.get("ANDB_BASE_URL")
        return (env or DEFAULT_API_URI).rstrip("/"), None

    if _looks_like_url(raw):
        return raw.rstrip("/"), None

    if _looks_like_profile_path(raw):
        return _load_profile_uri(Path(raw)), Path(raw)

    # Bare hostname:port → treat as URI without scheme.
    if "://" not in raw and (":" in raw or raw.startswith("127.0.0.1")):
        return f"http://{raw}".rstrip("/"), None

    return raw.rstrip("/"), None


def _load_profile_uri(path: Path) -> str:
    profile = _read_profile(path)
    uri = str(profile.get("uri") or "").strip()
    if not uri:
        uri = DEFAULT_API_URI
        profile["uri"] = uri
        _write_profile(path, profile)
    return uri.rstrip("/")


def _read_profile(path: Path) -> dict[str, Any]:
    if path.is_file():
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("collections", {})
            return data
    profile: dict[str, Any] = {
        "uri": DEFAULT_API_URI,
        "token": "",
        "collections": {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_profile(path, profile)
    return profile


def _write_profile(path: Path, profile: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
        f.write("\n")


class PlasmodClient:
    """
    MilvusClient-style entry point for Plasmod.

    Connect to a running gateway (Docker image :data:`DEFAULT_DOCKER_IMAGE` or your own deploy)::

        from pyplasmod import PlasmodClient

        client = PlasmodClient(uri="http://127.0.0.1:19530")

    Persist connection defaults in a local profile file (JSON, ``.db`` suffix like Milvus Lite)::

        client = PlasmodClient("plasmod_demo.db")

    **Collections** map to Plasmod ``workspace_id`` + warm segment ``warm.<name>``.
  Low-level HTTP/RPC remains on :attr:`http` (:class:`~pyplasmod.http.client.PlasmodHttpClient`).
    """

    __slots__ = ("http", "_profile_path", "_collections", "_mgmt_base_url")

    def __init__(
        self,
        uri: str = "",
        *,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        admin_key: Optional[str] = None,
        session: Optional[Any] = None,
    ) -> None:
        """
        :param uri: Gateway URL, or path to a local profile (``*.db`` / ``*.json``).
        :param token: Optional credential; stored in profile files and passed as ``admin_key`` when set.
        :param base_url: Alias for ``uri`` when connecting over HTTP (backward compatible).
        """
        resolved, profile_path = _resolve_base_url(uri or None, base_url=base_url)
        key = admin_key
        if key is None and token:
            key = token

        if profile_path is not None:
            profile = _read_profile(profile_path)
            if token:
                profile["token"] = token
                _write_profile(profile_path, profile)
            elif not key and profile.get("token"):
                key = str(profile["token"])
            stored_uri = str(profile.get("uri") or "").strip()
            if stored_uri:
                resolved = stored_uri.rstrip("/")

        self._profile_path = profile_path
        self._collections: dict[str, dict[str, Any]] = {}
        if profile_path is not None:
            prof = _read_profile(profile_path)
            cols = prof.get("collections")
            if isinstance(cols, dict):
                self._collections = {str(k): dict(v) for k, v in cols.items() if isinstance(v, dict)}

        self.http = PlasmodHttpClient(
            base_url=resolved,
            timeout=timeout,
            admin_key=key,
            session=session,
        )
        self._mgmt_base_url = _mgmt_url_from_api(self.http.base_url)

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> PlasmodClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _persist_collections(self) -> None:
        if self._profile_path is None:
            return
        profile = _read_profile(self._profile_path)
        profile["uri"] = self.http.base_url
        profile["collections"] = self._collections
        _write_profile(self._profile_path, profile)

    def _warm_segment_id(self, collection_name: str) -> str:
        meta = self._collections.get(collection_name) or {}
        seg = str(meta.get("warm_segment_id") or f"warm.{collection_name}")
        return seg

    def health(self) -> Any:
        """``GET /healthz`` — uses mgmt port (9091) when API is on 19530 (split deploy)."""
        if self._mgmt_base_url:
            url = f"{self._mgmt_base_url.rstrip('/')}/healthz"
            try:
                resp = self.http._session.get(url, timeout=self.http.timeout)
            except requests.RequestException as exc:
                raise PlasmodHttpError(0, reason=f"GET {url} failed: {exc}") from exc
            if not resp.ok:
                raise PlasmodHttpError(
                    resp.status_code,
                    reason=f"GET {url} failed",
                    body=resp.text,
                    path="/healthz",
                )
            if not resp.text.strip():
                return None
            return resp.json()
        return self.http.health()

    def has_collection(self, collection_name: str) -> bool:
        return collection_name in self._collections

    def list_collections(self) -> list[str]:
        return sorted(self._collections.keys())

    def create_collection(
        self,
        collection_name: str,
        dimension: int,
        *,
        index_type: str = WARM_INDEX_HNSW,
        metric_type: str = "COSINE",
        **kwargs: Any,
    ) -> None:
        """
        Register a logical collection (workspace + warm segment metadata).

        Does not call the server until :meth:`insert` / :meth:`search`. ``metric_type`` is
        recorded for client-side documentation; the gateway warm index uses server defaults.
        """
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        idx = normalize_warm_index_type(index_type)
        meta: dict[str, Any] = {
            "dimension": int(dimension),
            "index_type": idx,
            "metric_type": str(metric_type).upper(),
            "warm_segment_id": kwargs.pop("warm_segment_id", f"warm.{collection_name}"),
            "workspace_id": kwargs.pop("workspace_id", collection_name),
        }
        for k in ("ivf_nlist", "ivf_nprobe", "ivf_m", "ivf_nbits", "ivf_sq_type"):
            if k in kwargs:
                meta[k] = kwargs.pop(k)
        if kwargs:
            meta["extra"] = kwargs
        self._collections[collection_name] = meta
        self._persist_collections()

    def drop_collection(self, collection_name: str) -> None:
        self._collections.pop(collection_name, None)
        self._persist_collections()

    def describe_collection(self, collection_name: str) -> dict[str, Any]:
        if collection_name not in self._collections:
            raise ValueError(f"collection {collection_name!r} not found; call create_collection first")
        return dict(self._collections[collection_name])

    def insert(
        self,
        collection_name: str,
        data: Union[Sequence[Sequence[float]], Sequence[Mapping[str, Any]]],
        *,
        object_ids: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Insert vectors into a collection.

        * ``data`` as list of float rows → ``POST /v1/ingest/vectors``.
        * ``data`` as list of dicts → each dict may include ``vector`` / ``id`` / ``text``;
          rows with ``vector`` are batched to warm ingest; dicts with only ``text`` are sent as events.
        """
        meta = self._collections.get(collection_name)
        if meta is None:
            raise ValueError(f"unknown collection {collection_name!r}; call create_collection first")

        if data and isinstance(data[0], Mapping):
            return self._insert_records(collection_name, data, meta=meta, **kwargs)

        vectors = [list(map(float, row)) for row in data]  # type: ignore[arg-type]
        ids = list(object_ids) if object_ids is not None else None
        ivf_keys = ("ivf_nlist", "ivf_nprobe", "ivf_m", "ivf_nbits", "ivf_sq_type")
        ivf = {k: meta[k] for k in ivf_keys if k in meta}
        ivf.update({k: kwargs[k] for k in ivf_keys if k in kwargs})
        return self.http.ingest_vectors(
            vectors,
            segment_id=kwargs.get("segment_id", meta["warm_segment_id"]),
            object_ids=ids,
            index_type=meta.get("index_type"),
            **ivf,
        )

    def _insert_records(
        self,
        collection_name: str,
        data: Sequence[Mapping[str, Any]],
        *,
        meta: Mapping[str, Any],
        **kwargs: Any,
    ) -> Any:
        workspace_id = str(kwargs.get("workspace_id", meta.get("workspace_id", collection_name)))
        vectors: list[list[float]] = []
        ids: list[str] = []
        text_rows: list[Mapping[str, Any]] = []
        for i, row in enumerate(data):
            item = dict(row)
            vec = item.pop("vector", None)
            if vec is not None:
                vectors.append(list(map(float, vec)))
                ids.append(str(item.pop("id", item.pop("object_id", f"{collection_name}_{i}"))))
            elif item.get("text"):
                text_rows.append(item)
        results: list[Any] = []
        if vectors:
            results.append(
                self.http.ingest_vectors(
                    vectors,
                    segment_id=str(kwargs.get("segment_id", meta["warm_segment_id"])),
                    object_ids=ids,
                    index_type=meta.get("index_type"),
                )
            )
        for row in text_rows:
            body = {
                "workspace_id": workspace_id,
                "text": row["text"],
                **{k: v for k, v in row.items() if k != "text"},
            }
            results.append(self.http.ingest_document(body))
        return results[0] if len(results) == 1 else results

    def search(
        self,
        collection_name: str,
        data: Union[str, Sequence[float], Sequence[Sequence[float]]],
        *,
        limit: int = 10,
        filter: str = "",
        output_fields: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Vector or text search.

        * ``data`` str → natural-language ``POST /v1/query``.
        * one vector (``list[float]``) → ``embedding_vector`` query.
        * matrix (``list[list[float]]``) → ``POST /v1/query/batch`` on the warm segment.
        """
        meta = self._collections.get(collection_name)
        workspace_id = str(
            kwargs.pop("workspace_id", (meta or {}).get("workspace_id", collection_name))
        )
        warm_segment_id = str(
            kwargs.pop("warm_segment_id", (meta or {}).get("warm_segment_id", f"warm.{collection_name}"))
        )

        if isinstance(data, str):
            body = build_query_body(
                data,
                workspace_id,
                top_k=limit,
                extra={"filter_expr": filter} if filter else None,
                **kwargs,
            )
            return self.http.query(body)

        if data and isinstance(data[0], (int, float)):
            vec = list(map(float, data))  # type: ignore[arg-type]
            extra: dict[str, Any] = {"warm_segment_id": warm_segment_id}
            if filter:
                extra["filter_expr"] = filter
            body = build_query_body(
                "vector_query",
                workspace_id,
                top_k=limit,
                embedding_vector=vec,
                extra=extra,
                **kwargs,
            )
            return self.http.query(body)

        vectors = [list(map(float, row)) for row in data]  # type: ignore[arg-type]
        batch_body: dict[str, Any] = {
            "warm_segment_id": warm_segment_id,
            "vectors": vectors,
            "top_k": limit,
            "agent_mode": kwargs.pop("agent_mode", "single_agent"),
        }
        if filter:
            batch_body["filter_expr"] = filter
        batch_body.update(kwargs)
        return self.http.query_batch(batch_body)

    @staticmethod
    def docker_run_hint(
        image: str = DEFAULT_DOCKER_IMAGE,
        *,
        split: bool = True,
    ) -> str:
        """Shell one-liner to start the published image (split ports by default)."""
        if split:
            return (
                f"docker run -d --name plasmod -p 9091:9091 -p 19530:19530 {image}"
            )
        return f"docker run -d --name plasmod -p 8080:8080 {image}"


def _mgmt_url_from_api(api_url: str) -> Optional[str]:
    parsed = urlparse(api_url)
    if parsed.port == 19530:
        host = parsed.hostname or "127.0.0.1"
        scheme = parsed.scheme or "http"
        return f"{scheme}://{host}:9091"
    return None


__all__ = [
    "DEFAULT_API_URI",
    "DEFAULT_DOCKER_IMAGE",
    "DEFAULT_UNIFIED_URI",
    "PlasmodClient",
]
