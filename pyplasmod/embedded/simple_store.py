# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Pure-Python warm vector storage (brute-force cosine; no native deps)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from pyplasmod.embedded.manifest import drop_collection_data, merge_entities
from pyplasmod.http.warm_index import normalize_warm_index_type


def _cosine_distance(a: Sequence[float], b: Sequence[float]) -> float:
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 1.0
    return 1.0 - (dot / math.sqrt(na * nb))


class SimpleWarmStore:
    """
    In-process cosine top-k without native libraries.

    Suitable for local ``*.db`` demos on Windows when ``libplasmod_retrieval`` is unavailable.
    """

    def __init__(self, profile_root: Path) -> None:
        self._root = profile_root.resolve()
        self._collections_dir = self._root / "collections"
        self._collections_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_available() -> bool:
        return True

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
        del ivf, metric_type
        if len(object_ids) != len(vectors):
            raise ValueError("object_ids and vectors length mismatch")
        if not vectors:
            raise ValueError("vectors must be non-empty")
        dim = len(vectors[0])
        for i, row in enumerate(vectors):
            if len(row) != dim:
                raise ValueError(f"vectors[{i}] dim {len(row)} != {dim}")

        idx = normalize_warm_index_type(index_type)
        manifest_path = self._manifest_path(collection_name)
        if manifest_path.is_file():
            manifest = self._read_manifest(collection_name)
            merged_ids = list(manifest["object_ids"])
            merged_vectors = [list(map(float, row)) for row in manifest["vectors"]]
            merged_entities = manifest.get("entities")
            if not isinstance(merged_entities, dict):
                merged_entities = {}
        else:
            merged_ids = []
            merged_vectors = []
            merged_entities = {}

        for oid, row in zip(object_ids, vectors):
            merged_ids.append(str(oid))
            merged_vectors.append(list(map(float, row)))

        if entities:
            merged_entities = merge_entities(merged_entities, object_ids, entities)

        if persist:
            coll_dir = self._collections_dir / collection_name
            coll_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "segment_id": segment_id,
                "object_ids": merged_ids,
                "dimension": dim,
                "index_type": idx,
                "vectors": merged_vectors,
                "entities": merged_entities,
                "backend": "simple",
            }
            manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return {
            "status": "ok",
            "segment_id": segment_id,
            "ingested": len(vectors),
            "vector_dim": dim,
            "index_type": idx,
            "direct_warm": True,
            "embedded": True,
            "backend": "simple",
        }

    def search(
        self,
        collection_name: str,
        *,
        segment_id: str,
        query_vector: Sequence[float],
        top_k: int = 10,
        output_fields: Optional[Sequence[str]] = None,
    ) -> dict[str, Any]:
        from pyplasmod.embedded.milvus_compat import format_search_hit

        manifest = self._read_manifest(collection_name)
        if manifest.get("segment_id") != segment_id:
            raise ValueError("segment_id mismatch for embedded collection")
        dim = int(manifest["dimension"])
        if len(query_vector) != dim:
            raise ValueError(f"query dim {len(query_vector)} != collection dim {dim}")

        entities = manifest.get("entities") if isinstance(manifest.get("entities"), dict) else {}
        q = list(map(float, query_vector))
        scored = [
            (_cosine_distance(q, row), str(oid))
            for oid, row in zip(manifest["object_ids"], manifest["vectors"])
        ]
        scored.sort(key=lambda item: item[0])
        hits = []
        for dist, oid in scored[: max(1, top_k)]:
            parsed: Any = oid
            if oid.isdigit():
                parsed = int(oid)
            entity = dict(entities.get(str(oid), entities.get(oid, {})))
            hits.append(
                format_search_hit(
                    hit_id=parsed,
                    distance=float(dist),
                    entity=entity,
                    output_fields=output_fields,
                )
            )
        return {
            "status": "ok",
            "hits": hits,
            "warm_segment_id": segment_id,
            "tier": "warm_segment",
            "embedded": True,
            "backend": "simple",
        }

    def drop_collection(self, collection_name: str) -> None:
        drop_collection_data(self._root, collection_name)

    def _manifest_path(self, collection_name: str) -> Path:
        return self._collections_dir / collection_name / "warm_manifest.json"

    def _read_manifest(self, collection_name: str) -> dict[str, Any]:
        path = self._manifest_path(collection_name)
        if not path.is_file():
            raise ValueError(f"embedded collection {collection_name!r} has no warm data")
        return json.loads(path.read_text(encoding="utf-8"))
