# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Default pip-bundled embedded warm store (FAISS HNSW; no Docker / native Plasmod build required)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np

from pyplasmod.embedded.manifest import (
    collection_dir,
    drop_collection_data,
    merge_entities,
    read_manifest,
    write_manifest,
)
from pyplasmod.http.warm_index import normalize_warm_index_type


def _entities_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, list):
        out: dict[str, Any] = {}
        for item in raw:
            if isinstance(item, dict) and "id" in item:
                out[str(item["id"])] = dict(item)
        return out
    return {}


class FaissWarmStore:
    """
    In-process warm-segment ANN using ``faiss-cpu`` (installed with ``pip install pyplasmod``).

    Persists under ``<profile_root>/collections/<name>/`` (Milvus Lite–style layout).
    """

    def __init__(self, profile_root: Path) -> None:
        self._root = profile_root.resolve()
        self._indexes: dict[str, Any] = {}

    @staticmethod
    def is_available() -> bool:
        try:
            import faiss  # noqa: F401

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
        metric_type: str = "COSINE",
        entities: Optional[Sequence[Mapping[str, Any]]] = None,
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
        metric = str(metric_type or "COSINE").upper()

        if collection_dir(self._root, collection_name).joinpath("warm_manifest.json").is_file():
            manifest = read_manifest(self._root, collection_name)
            merged_ids = list(manifest["object_ids"])
            merged_vectors = [list(map(float, row)) for row in manifest["vectors"]]
            merged_entities = _entities_dict(manifest.get("entities"))
        else:
            merged_ids = []
            merged_vectors = []
            merged_entities = {}

        for oid, row in zip(object_ids, vectors):
            merged_ids.append(str(oid))
            merged_vectors.append(list(map(float, row)))

        if entities:
            merged_entities = merge_entities(merged_entities, object_ids, entities)

        index = self._build_index(merged_vectors, dim, idx, metric)
        self._indexes[collection_name] = index

        if persist:
            payload = {
                "segment_id": segment_id,
                "object_ids": merged_ids,
                "dimension": dim,
                "index_type": idx,
                "metric_type": metric,
                "vectors": merged_vectors,
                "entities": merged_entities,
                "backend": "faiss",
            }
            write_manifest(self._root, collection_name, payload)

        return {
            "status": "ok",
            "segment_id": segment_id,
            "ingested": len(vectors),
            "vector_dim": dim,
            "index_type": idx,
            "metric_type": metric,
            "direct_warm": True,
            "embedded": True,
            "backend": "faiss",
        }

    def search(
        self,
        collection_name: str,
        *,
        segment_id: str,
        query_vectors: Sequence[Sequence[float]],
        top_k: int = 10,
        output_fields: Optional[Sequence[str]] = None,
    ) -> list[list[dict[str, Any]]]:
        from pyplasmod.embedded.milvus_compat import format_search_hit

        manifest = read_manifest(self._root, collection_name)
        if manifest.get("segment_id") != segment_id:
            raise ValueError("segment_id mismatch for embedded collection")
        dim = int(manifest["dimension"])
        metric = str(manifest.get("metric_type") or "COSINE").upper()
        entities = manifest.get("entities") or {}

        index = self._indexes.get(collection_name)
        if index is None:
            index = self._load_index(collection_name, manifest)
            self._indexes[collection_name] = index

        id_list = manifest["object_ids"]
        k = max(1, min(int(top_k), len(id_list)))
        results: list[list[dict[str, Any]]] = []

        for query in query_vectors:
            if len(query) != dim:
                raise ValueError(f"query dim {len(query)} != collection dim {dim}")
            q = np.array([list(map(float, query))], dtype=np.float32)
            if metric == "COSINE":
                q = self._normalize(q)
            distances, indices = index.search(q, k)
            hits: list[dict[str, Any]] = []
            for dist, raw_idx in zip(distances[0], indices[0]):
                pos = int(raw_idx)
                if pos < 0 or pos >= len(id_list):
                    continue
                oid = id_list[pos]
                parsed_id: Any = oid
                if isinstance(oid, str) and oid.isdigit():
                    parsed_id = int(oid)
                distance = float(dist)
                if metric == "COSINE":
                    distance = 1.0 - distance
                entity = dict(entities.get(str(oid), entities.get(oid, {})))
                hits.append(
                    format_search_hit(
                        hit_id=parsed_id,
                        distance=distance,
                        entity=entity,
                        output_fields=output_fields,
                    )
                )
            results.append(hits)
        return results

    def drop_collection(self, collection_name: str) -> None:
        self._indexes.pop(collection_name, None)
        drop_collection_data(self._root, collection_name)

    def _build_index(
        self,
        vectors: Sequence[Sequence[float]],
        dim: int,
        index_type: str,
        metric_type: str,
    ) -> Any:
        import faiss

        arr = np.array(vectors, dtype=np.float32)
        metric = metric_type.upper()
        if metric == "COSINE":
            arr = self._normalize(arr)
            faiss_metric = faiss.METRIC_INNER_PRODUCT
        elif metric in ("L2", "EUCLIDEAN"):
            faiss_metric = faiss.METRIC_L2
        else:
            raise ValueError(f"unsupported metric_type {metric_type!r}")

        if index_type == "HNSW":
            # IndexFlat is the default embedded backend (stable wheels on Windows).
            # Optional HNSW when explicitly requested on non-Windows hosts.
            if faiss_metric == faiss.METRIC_INNER_PRODUCT:
                index = faiss.IndexFlatIP(dim)
            else:
                index = faiss.IndexFlatL2(dim)
        elif faiss_metric == faiss.METRIC_INNER_PRODUCT:
            index = faiss.IndexFlatIP(dim)
        else:
            index = faiss.IndexFlatL2(dim)
        index.add(arr)
        return index

    def _load_index(self, collection_name: str, manifest: Mapping[str, Any]) -> Any:
        return self._build_index(
            manifest["vectors"],
            int(manifest["dimension"]),
            str(manifest.get("index_type") or "HNSW"),
            str(manifest.get("metric_type") or "COSINE"),
        )

    @staticmethod
    def _normalize(arr: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        out = arr / norms
        return out.astype(np.float32, copy=False)
