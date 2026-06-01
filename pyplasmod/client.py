# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""High-level :class:`PlasmodClient` (MilvusClient-style entry point)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Union
from urllib.parse import urlparse

from pyplasmod.data import build_query_body
from pyplasmod.exceptions import ConnectError
from pyplasmod.http.client import PlasmodHttpClient
from pyplasmod.http.deploy import resolve_mgmt_base_url
from pyplasmod.http.warm_index import WARM_INDEX_HNSW, normalize_warm_index_type
from pyplasmod.embedded import WarmVectorStore, create_warm_store
from pyplasmod.embedded.milvus_compat import format_insert_result, format_search_results
from pyplasmod.profile_store import (
    ensure_profile_layout,
    is_profile_path,
    profile_uri,
    read_profile,
    write_profile,
)
from pyplasmod.runtime.docker_bootstrap import (
    DEFAULT_CONTAINER_NAME,
    DEFAULT_DOCKER_IMAGE,
    auto_start_enabled,
    ensure_docker_gateway,
    gateway_is_healthy,
    is_local_gateway_url,
)
from pyplasmod.runtime.embedded_server import (
    embedded_enabled,
    ensure_embedded_server,
    find_plasmod_server_binary,
    release_embedded_server,
)
from pyplasmod.embedded.manifest import drop_collection_data
from pyplasmod.runtime.retrieval_probe import gateway_has_vector_retrieval

# Published Docker image (split: mgmt 9091, API 19530); re-exported from runtime.docker_bootstrap.
DEFAULT_API_URI = "http://127.0.0.1:19530"
DEFAULT_UNIFIED_URI = "http://127.0.0.1:8080"


def _looks_like_url(value: str) -> bool:
    v = value.strip().lower()
    return v.startswith("http://") or v.startswith("https://")


def _looks_like_profile_path(value: str) -> bool:
    return is_profile_path(value)


def _resolve_base_url(
  uri: Optional[str],
  *,
  base_url: Optional[str],
) -> tuple[str, Optional[Path], Optional[Path], Optional[Path]]:
    """
    Return ``(http_base_url, user_profile_path, profile_json_path, data_dir)``.

    * ``*.db`` / ``*.json`` path → local profile (see :mod:`pyplasmod.profile_store`).
    * HTTP(S) → remote gateway only.
    """
    if base_url is not None:
        return str(base_url).rstrip("/"), None, None, None

    raw = (uri or "").strip()
    if not raw:
        env = os.environ.get("PLASMOD_BASE_URL") or os.environ.get("ANDB_BASE_URL")
        return (env or DEFAULT_API_URI).rstrip("/"), None, None, None

    if _looks_like_url(raw):
        return raw.rstrip("/"), None, None, None

    if _looks_like_profile_path(raw):
        user_path = Path(raw)
        profile_json, data_dir = ensure_profile_layout(user_path)
        resolved = profile_uri(read_profile(profile_json))
        return resolved, user_path, profile_json, data_dir

    if "://" not in raw and (":" in raw or raw.startswith("127.0.0.1")):
        return f"http://{raw}".rstrip("/"), None, None, None

    return raw.rstrip("/"), None, None, None


def _embedded_store_root(user_path: Optional[Path], data_dir: Optional[Path]) -> Optional[Path]:
    if user_path is None:
        return None
    if user_path.is_dir():
        return user_path
    if data_dir is not None:
        return data_dir.parent
    return user_path.parent / user_path.stem


def _coerce_query_vectors(
    data: Sequence[Any],
) -> list[list[float]]:
    if not data:
        raise ValueError("search data must be non-empty")
    if isinstance(data[0], (int, float)):
        return [list(map(float, data))]
    return [list(map(float, row)) for row in data]


def _profile_auto_start_default(
    profile_json: Optional[Path],
    embedded: Optional[bool],
    auto_start: Optional[bool],
) -> Optional[bool]:
    """Local ``*.db`` profiles default to pip-only embedded mode (no Docker)."""
    if auto_start is not None:
        return auto_start
    if profile_json is not None and embedded_enabled(embedded):
        return False
    return None


def _bootstrap_local_gateway(
    resolved: str,
    *,
    profile_json: Optional[Path],
    user_path: Optional[Path],
    data_dir: Optional[Path],
    embedded: Optional[bool],
    auto_start: Optional[bool],
    docker_image: Optional[str],
    docker_container_name: Optional[str],
) -> tuple[str, Optional[str], Optional[WarmVectorStore], bool]:
    """
    Return ``(base_url, embedded_mode, warm_store, owns_embedded_server)``.

    * ``embedded_mode="embedded"`` — bundled ``faiss-cpu`` (default after ``pip install pyplasmod``).
    * ``embedded_mode="native"`` — optional ``libplasmod_retrieval`` (Plasmod C++ stack).
    * ``embedded_mode="server"`` — optional child ``plasmod-server`` (not required for local ``*.db``).
    """
    warm_store: Optional[WarmVectorStore] = None
    owns_server = False
    mode: Optional[str] = None
    store_root = _embedded_store_root(user_path, data_dir)

    if profile_json is None or not embedded_enabled(embedded):
        if auto_start_enabled(auto_start) and is_local_gateway_url(resolved):
            if not gateway_is_healthy(resolved):
                ensure_docker_gateway(
                    resolved,
                    image=docker_image,
                    container_name=docker_container_name,
                    data_dir=data_dir,
                )
        return resolved, mode, warm_store, owns_server

    persist_dir = data_dir or (store_root / "data" if store_root else None)

    # Milvus Lite–like: local profile prefers in-process vectors before HTTP/Docker.
    if store_root is not None:
        warm_store, store_mode = create_warm_store(store_root)
        if warm_store is not None and store_mode is not None:
            return resolved, store_mode, warm_store, owns_server

    if find_plasmod_server_binary() and persist_dir is not None:
        try:
            candidate = ensure_embedded_server(persist_dir)
            if gateway_has_vector_retrieval(candidate):
                return candidate, "server", None, True
            release_embedded_server()
        except ConnectError:
            pass

    if gateway_is_healthy(resolved) and gateway_has_vector_retrieval(resolved):
        return resolved, mode, warm_store, owns_server

    if auto_start_enabled(auto_start):
        ensure_docker_gateway(
            resolved,
            image=docker_image,
            container_name=docker_container_name,
            data_dir=data_dir,
        )

    return resolved, mode, warm_store, owns_server


class PlasmodClient:
    """
    MilvusClient-style entry point for Plasmod.

    On a **local** default URL (``http://127.0.0.1:19530``), the client can auto-start the
    published Docker image :data:`DEFAULT_DOCKER_IMAGE` when the gateway is down (disable with
    ``auto_start=False`` or ``PLASMOD_AUTO_START=0``)::

        from pyplasmod import PlasmodClient

        client = PlasmodClient(uri="http://127.0.0.1:19530")

    Remote gateways are never auto-started; pass an explicit URL or set ``PLASMOD_BASE_URL``.

    Persist connection defaults in a local profile path (MilvusClient-style ``*.db``)::

        client = PlasmodClient("plasmod_demo.db")

    **Embedded mode (Milvus Lite–like)** — default for ``*.db`` profiles; ``pip install pyplasmod`` only:

    * **Embedded vectors** — bundled ``faiss-cpu`` HNSW; data under ``foo.db/collections/``.
    * **Native vectors** — optional ``libplasmod_retrieval`` when built from Plasmod source.
    * **Remote gateway** — pass ``uri="http://..."`` or disable ``embedded=False`` for full Plasmod HTTP APIs.
    * Docker auto-start is **off** for local ``*.db`` profiles (enable with ``auto_start=True``).

    Legacy single-file ``plasmod_demo.db`` (JSON) is still supported.
    **Collections** map to Plasmod ``workspace_id`` + warm segment ``warm.<name>``.
    Low-level HTTP/RPC remains on :attr:`http` (:class:`~pyplasmod.http.client.PlasmodHttpClient`).
    """

    __slots__ = (
        "http",
        "_profile_user_path",
        "_profile_json_path",
        "_profile_data_dir",
        "_collections",
        "_mgmt_base_url",
        "_embedded_mode",
        "_embedded_store",
        "_owns_embedded_server",
    )

    def __init__(
        self,
        uri: str = "",
        *,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        admin_key: Optional[str] = None,
        session: Optional[Any] = None,
        auto_start: Optional[bool] = None,
        embedded: Optional[bool] = None,
        docker_image: Optional[str] = None,
        docker_container_name: Optional[str] = None,
    ) -> None:
        """
        :param uri: Gateway URL, or path to a local profile (``*.db`` / ``*.json``).
        :param token: Optional credential; stored in profile files and passed as ``admin_key`` when set.
        :param base_url: Alias for ``uri`` when connecting over HTTP (backward compatible).
        :param auto_start: Docker fallback when embedded/local gateway is down (``PLASMOD_AUTO_START``).
        :param embedded: In-process / subprocess embedded Plasmod (default on for ``*.db`` profiles).
        :param docker_image: Image for Docker fallback (env ``PLASMOD_DOCKER_IMAGE``).
        :param docker_container_name: Container name (env ``PLASMOD_DOCKER_CONTAINER``).
        """
        resolved, user_path, profile_json, data_dir = _resolve_base_url(uri or None, base_url=base_url)
        key = admin_key
        if key is None and token:
            key = token

        if profile_json is not None:
            profile = read_profile(profile_json)
            if token:
                profile["token"] = token
                write_profile(profile_json, profile)
            elif not key and profile.get("token"):
                key = str(profile["token"])
            stored_uri = profile_uri(profile)
            if stored_uri:
                resolved = stored_uri

        resolved, embedded_mode, warm_store, owns_server = _bootstrap_local_gateway(
            resolved,
            profile_json=profile_json,
            user_path=user_path,
            data_dir=data_dir,
            embedded=embedded,
            auto_start=_profile_auto_start_default(profile_json, embedded, auto_start),
            docker_image=docker_image,
            docker_container_name=docker_container_name,
        )

        self._profile_user_path = user_path
        self._profile_json_path = profile_json
        self._profile_data_dir = data_dir
        self._embedded_mode = embedded_mode
        self._embedded_store = warm_store
        self._owns_embedded_server = owns_server
        self._collections: dict[str, dict[str, Any]] = {}
        if profile_json is not None:
            prof = read_profile(profile_json)
            cols = prof.get("collections")
            if isinstance(cols, dict):
                self._collections = {str(k): dict(v) for k, v in cols.items() if isinstance(v, dict)}
            prof["uri"] = resolved
            if embedded_mode:
                prof["embedded_mode"] = embedded_mode
            write_profile(profile_json, prof)

        self.http = PlasmodHttpClient(
            base_url=resolved,
            timeout=timeout,
            admin_key=key,
            session=session,
        )
        self._mgmt_base_url = resolve_mgmt_base_url(self.http.base_url)

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to :attr:`http` (``PlasmodHttpClient`` compatibility)."""
        return getattr(self.http, name)

    def close(self) -> None:
        if self._owns_embedded_server:
            release_embedded_server()
        self.http.close()

    def __enter__(self) -> PlasmodClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _persist_collections(self) -> None:
        if self._profile_json_path is None:
            return
        profile = read_profile(self._profile_json_path)
        profile["uri"] = self.http.base_url
        profile["collections"] = self._collections
        write_profile(self._profile_json_path, profile)

    @property
    def profile_path(self) -> Optional[Path]:
        """User-facing profile path (``*.db`` directory or legacy JSON file)."""
        return self._profile_user_path

    @property
    def profile_data_dir(self) -> Optional[Path]:
        """Host ``data/`` directory mounted into Docker when auto-start uses a profile folder."""
        return self._profile_data_dir

    @property
    def embedded_mode(self) -> Optional[str]:
        """``"vectors"`` (in-process C++), ``"server"`` (child plasmod-server), or ``None``."""
        return self._embedded_mode

    def _warm_segment_id(self, collection_name: str) -> str:
        meta = self._collections.get(collection_name) or {}
        seg = str(meta.get("warm_segment_id") or f"warm.{collection_name}")
        return seg

    def health(self) -> Any:
        """``GET /healthz`` — split deploy uses mgmt :9091 via :attr:`http`."""
        return self.http.health()

    def has_collection(self, collection_name: str) -> bool:
        return collection_name in self._collections

    def list_collections(self) -> list[str]:
        return sorted(self._collections.keys())

    def has_collection(self, collection_name: str) -> bool:
        return collection_name in self._collections

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
        if self._embedded_store is not None:
            self._embedded_store.drop_collection(collection_name)
        elif self._profile_user_path is not None:
            root = _embedded_store_root(self._profile_user_path, self._profile_data_dir)
            if root is not None:
                drop_collection_data(root, collection_name)
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
        segment_id = str(kwargs.get("segment_id", meta["warm_segment_id"]))
        if self._embedded_store is not None:
            if ids is None:
                ids = [f"{collection_name}_{i}" for i in range(len(vectors))]
            raw = self._embedded_store.insert(
                collection_name,
                segment_id=segment_id,
                object_ids=ids,
                vectors=vectors,
                index_type=str(meta.get("index_type") or WARM_INDEX_HNSW),
                metric_type=str(meta.get("metric_type") or "COSINE"),
                ivf=ivf,
            )
            return format_insert_result(object_ids=ids, insert_count=len(vectors), extra={"embedded_mode": self._embedded_mode})
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
        entities: list[dict[str, Any]] = []
        text_rows: list[Mapping[str, Any]] = []
        for i, row in enumerate(data):
            item = dict(row)
            vec = item.pop("vector", None)
            if vec is not None:
                vectors.append(list(map(float, vec)))
                oid = str(item.pop("id", item.pop("object_id", f"{collection_name}_{i}")))
                ids.append(oid)
                entity = dict(item)
                entity.setdefault("id", oid)
                entities.append(entity)
            elif item.get("text"):
                text_rows.append(item)
        results: list[Any] = []
        if vectors:
            segment_id = str(kwargs.get("segment_id", meta["warm_segment_id"]))
            if self._embedded_store is not None:
                self._embedded_store.insert(
                    collection_name,
                    segment_id=segment_id,
                    object_ids=ids,
                    vectors=vectors,
                    entities=entities,
                    index_type=str(meta.get("index_type") or WARM_INDEX_HNSW),
                    metric_type=str(meta.get("metric_type") or "COSINE"),
                )
                results.append(
                    format_insert_result(
                        object_ids=ids,
                        insert_count=len(vectors),
                        extra={"embedded_mode": self._embedded_mode},
                    )
                )
            else:
                results.append(
                    self.http.ingest_vectors(
                        vectors,
                        segment_id=segment_id,
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

        Embedded ``*.db`` profiles return pymilvus-shaped results::

            [[{"id": 1, "distance": 0.01, "entity": {...}}, ...], ...]

        * ``data`` str → natural-language ``POST /v1/query`` (remote gateway).
        * ``list[float]`` or ``list[list[float]]`` → vector search (Milvus-compatible).
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

        queries = _coerce_query_vectors(data)
        if self._embedded_store is not None:
            batch = self._embedded_store.search(
                collection_name,
                segment_id=warm_segment_id,
                query_vectors=queries,
                top_k=limit,
                output_fields=output_fields,
            )
            return format_search_results(batch)

        if len(queries) == 1:
            extra: dict[str, Any] = {"warm_segment_id": warm_segment_id}
            if filter:
                extra["filter_expr"] = filter
            body = build_query_body(
                "vector_query",
                workspace_id,
                top_k=limit,
                embedding_vector=queries[0],
                extra=extra,
                **kwargs,
            )
            return self.http.query(body)

        batch_body: dict[str, Any] = {
            "warm_segment_id": warm_segment_id,
            "vectors": queries,
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


__all__ = [
    "DEFAULT_API_URI",
    "DEFAULT_CONTAINER_NAME",
    "DEFAULT_DOCKER_IMAGE",
    "DEFAULT_UNIFIED_URI",
    "PlasmodClient",
]
