# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Pure-Python warm vector storage via ``hnswlib`` (Windows-friendly fallback)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Sequence

from pyplasmod.http.warm_index import normalize_warm_index_type


class HnswlibWarmStore:
    """
    In-process HNSW when ``libplasmod_retrieval`` is unavailable (e.g. Windows without a native build).

    Uses the same ``collections/<name>/warm_manifest.json`` layout as :class:`EmbeddedWarmStore`.
    """

    def __init__(self, profile_root: Path) -> None:
        self._root = profile_root.resolve()
        self._collections_dir = self._root / "collections"
        self._collections_dir.mkdir(parents=True, exist_ok=True)
        self._indexes: dict[str, Any] = {}

    @staticmethod
    def is_available() -> bool:
        try:
            import hnswlib  # noqa: F401

            return True
        except ImportError:
            return False

    def insert(
        self,
        collection_name: str,
        *,
        segment_id: str,
        object_ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
        index_type: str = "HNSW",
        ivf: Optional[dict[str, Any]] = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        del ivf
        if len(object_ids) != len(vectors):
            raise ValueError("object_ids and vectors length mismatch")
        if not vectors:
            raise ValueError("vectors must be non-empty")
        dim = len(vectors[0])
        for i, row in enumerate(vectors):
            if len(row) != dim:
                raise ValueError(f"vectors[{i}] dim {len(row)} != {dim}")

        idx = normalize_warm_index_type(index_type)
        if idx != "HNSW":
            raise ValueError(f"hnswlib fallback supports HNSW only, got {idx!r}")

        manifest = self._read_manifest(collection_name) if self._manifest_path(collection_name).is_file() else None
        merged_ids = list(manifest["object_ids"]) if manifest else []
        merged_vectors = [list(map(float, row)) for row in manifest["vectors"]] if manifest else []

        for oid, row in zip(object_ids, vectors):
            merged_ids.append(str(oid))
            merged_vectors.append(list(map(float, row)))

        if persist:
            coll_dir = self._collections_dir / collection_name
            coll_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "segment_id": segment_id,
                "object_ids": merged_ids,
                "dimension": dim,
                "index_type": idx,
                "vectors": merged_vectors,
                "backend": "hnswlib",
            }
            self._manifest_path(collection_name).write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )

        self._indexes[collection_name] = self._build_index(merged_vectors, dim)
        return {
            "status": "ok",
            "segment_id": segment_id,
            "ingested": len(vectors),
            "vector_dim": dim,
            "index_type": idx,
            "direct_warm": True,
            "embedded": True,
            "backend": "hnswlib",
        }

    def search(
        self,
        collection_name: str,
        *,
        segment_id: str,
        query_vector: Sequence[float],
        top_k: int = 10,
    ) -> dict[str, Any]:
        manifest = self._read_manifest(collection_name)
        if manifest.get("segment_id") != segment_id:
            raise ValueError("segment_id mismatch for embedded collection")
        dim = int(manifest["dimension"])
        if len(query_vector) != dim:
            raise ValueError(f"query dim {len(query_vector)} != collection dim {dim}")

        index = self._indexes.get(collection_name)
        if index is None:
            index = self._build_index(manifest["vectors"], dim)
            self._indexes[collection_name] = index

        labels, _distances = index.knn_query([list(map(float, query_vector))], k=min(top_k, len(manifest["object_ids"])))
        id_list = manifest["object_ids"]
        hits = [str(id_list[int(idx)]) for idx in labels[0] if 0 <= int(idx) < len(id_list)]
        return {
            "status": "ok",
            "objects": hits,
            "warm_segment_id": segment_id,
            "tier": "warm_segment",
            "embedded": True,
            "backend": "hnswlib",
        }

    def _build_index(self, vectors: Sequence[Sequence[float]], dim: int) -> Any:
        import hnswlib

        count = len(vectors)
        index = hnswlib.Index(space="cosine", dim=dim)
        index.init_index(max_elements=max(count, 1), ef_construction=200, M=16)
        labels = list(range(count))
        index.add_items(vectors, labels)
        index.set_ef(max(10, min(count, 200)))
        return index

    def _manifest_path(self, collection_name: str) -> Path:
        return self._collections_dir / collection_name / "warm_manifest.json"

    def _read_manifest(self, collection_name: str) -> dict[str, Any]:
        path = self._manifest_path(collection_name)
        if not path.is_file():
            raise ValueError(f"embedded collection {collection_name!r} has no warm data")
        return json.loads(path.read_text(encoding="utf-8"))
