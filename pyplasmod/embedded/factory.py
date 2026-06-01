# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from pyplasmod.embedded.faiss_store import FaissWarmStore
from pyplasmod.embedded.hnsw_store import HnswlibWarmStore
from pyplasmod.embedded.simple_store import SimpleWarmStore
from pyplasmod.embedded.warm_store import EmbeddedWarmStore


@runtime_checkable
class WarmVectorStore(Protocol):
    def insert(self, collection_name: str, *, segment_id: str, object_ids, vectors, **kwargs) -> dict[str, Any]: ...

    def search(
        self,
        collection_name: str,
        *,
        segment_id: str,
        query_vectors,
        top_k: int = 10,
        output_fields=None,
    ) -> list[list[dict[str, Any]]]: ...

    def drop_collection(self, collection_name: str) -> None: ...


def create_warm_store(profile_root: Path) -> tuple[Optional[WarmVectorStore], Optional[str]]:
    """
    Return ``(store, mode)`` for pip-only in-process vector insert/search.

    Priority:

    1. ``native`` — optional ``libplasmod_retrieval`` (Plasmod C++ stack)
    2. ``embedded`` — ``faiss-cpu`` bundled with ``pip install pyplasmod`` (default)
    3. ``hnswlib`` / ``simple`` — fallbacks when FAISS is unavailable
    """
    if EmbeddedWarmStore.is_available():
        return _NativeAdapter(EmbeddedWarmStore(profile_root)), "native"
    if FaissWarmStore.is_available():
        return FaissWarmStore(profile_root), "embedded"
    if HnswlibWarmStore.is_available():
        return _HnswlibAdapter(HnswlibWarmStore(profile_root)), "hnswlib"
    if SimpleWarmStore.is_available():
        return _SimpleAdapter(SimpleWarmStore(profile_root)), "simple"
    return None, None


class _NativeAdapter:
    def __init__(self, store: EmbeddedWarmStore) -> None:
        self._store = store

    def insert(self, collection_name: str, **kwargs: Any) -> dict[str, Any]:
        return self._store.insert(collection_name, **kwargs)

    def search(self, collection_name: str, *, segment_id: str, query_vectors, top_k=10, output_fields=None):
        from pyplasmod.embedded.milvus_compat import format_search_hit

        batch: list[list[dict[str, Any]]] = []
        for query in query_vectors:
            raw = self._store.search(
                collection_name,
                segment_id=segment_id,
                query_vector=query,
                top_k=top_k,
            )
            hits = []
            for oid in raw.get("objects") or []:
                parsed: Any = oid
                if isinstance(oid, str) and oid.isdigit():
                    parsed = int(oid)
                hits.append(format_search_hit(hit_id=parsed, distance=0.0, entity={"id": parsed}, output_fields=output_fields))
            batch.append(hits)
        return batch

    def drop_collection(self, collection_name: str) -> None:
        from pyplasmod.embedded.manifest import drop_collection_data

        drop_collection_data(self._store._root, collection_name)


class _HnswlibAdapter:
    def __init__(self, store: HnswlibWarmStore) -> None:
        self._store = store

    def insert(self, collection_name: str, **kwargs: Any) -> dict[str, Any]:
        return self._store.insert(collection_name, **kwargs)

    def search(self, collection_name: str, *, segment_id: str, query_vectors, top_k=10, output_fields=None):
        from pyplasmod.embedded.milvus_compat import format_search_hit

        batch = []
        for query in query_vectors:
            raw = self._store.search(collection_name, segment_id=segment_id, query_vector=query, top_k=top_k)
            hits = []
            for oid in raw.get("objects") or []:
                parsed: Any = oid
                if isinstance(oid, str) and oid.isdigit():
                    parsed = int(oid)
                hits.append(format_search_hit(hit_id=parsed, distance=0.0, entity={"id": parsed}, output_fields=output_fields))
            batch.append(hits)
        return batch

    def drop_collection(self, collection_name: str) -> None:
        from pyplasmod.embedded.manifest import drop_collection_data

        drop_collection_data(self._store._root, collection_name)


class _SimpleAdapter:
    def __init__(self, store: SimpleWarmStore) -> None:
        self._store = store

    def insert(self, collection_name: str, **kwargs: Any) -> dict[str, Any]:
        return self._store.insert(collection_name, **kwargs)

    def search(self, collection_name: str, *, segment_id: str, query_vectors, top_k=10, output_fields=None):
        batch = []
        for query in query_vectors:
            raw = self._store.search(
                collection_name,
                segment_id=segment_id,
                query_vector=query,
                top_k=top_k,
                output_fields=output_fields,
            )
            batch.append(list(raw.get("hits") or []))
        return batch

    def drop_collection(self, collection_name: str) -> None:
        from pyplasmod.embedded.manifest import drop_collection_data

        drop_collection_data(self._store._root, collection_name)
