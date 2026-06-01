# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Shared warm-manifest persistence for embedded vector stores."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence


def cosine_distance(a: Sequence[float], b: Sequence[float]) -> float:
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


def manifest_path(collections_dir: Path, collection_name: str) -> Path:
    return collections_dir / collection_name / "warm_manifest.json"


def read_manifest(collections_dir: Path, collection_name: str) -> dict[str, Any]:
    path = manifest_path(collections_dir, collection_name)
    if not path.is_file():
        raise ValueError(f"embedded collection {collection_name!r} has no warm data")
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(collections_dir: Path, collection_name: str, payload: Mapping[str, Any]) -> None:
    path = manifest_path(collections_dir, collection_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2), encoding="utf-8")


def merge_manifest_rows(
    manifest: Optional[dict[str, Any]],
    *,
    segment_id: str,
    object_ids: Sequence[Any],
    vectors: Sequence[Sequence[float]],
    entities: Optional[Sequence[Mapping[str, Any]]] = None,
    index_type: str,
    backend: str,
) -> dict[str, Any]:
    if not vectors:
        raise ValueError("vectors must be non-empty")
    dim = len(vectors[0])
    merged_ids: list[Any] = []
    merged_vectors: list[list[float]] = []
    merged_entities: list[dict[str, Any]] = []

    if manifest:
        merged_ids.extend(manifest.get("object_ids") or [])
        merged_vectors.extend([list(map(float, row)) for row in manifest.get("vectors") or []])
        merged_entities.extend([dict(row) for row in manifest.get("entities") or []])

    for i, row in enumerate(vectors):
        if len(row) != dim:
            raise ValueError(f"vectors[{i}] dim {len(row)} != {dim}")
        merged_ids.append(object_ids[i])
        merged_vectors.append(list(map(float, row)))
        if entities is not None and i < len(entities):
            merged_entities.append(dict(entities[i]))
        else:
            merged_entities.append({"id": object_ids[i]})

    return {
        "segment_id": segment_id,
        "object_ids": merged_ids,
        "entities": merged_entities,
        "dimension": dim,
        "index_type": index_type,
        "vectors": merged_vectors,
        "backend": backend,
    }


def entity_for_index(manifest: Mapping[str, Any], index: int, object_id: Any) -> dict[str, Any]:
    entities = manifest.get("entities") or []
    if 0 <= index < len(entities) and isinstance(entities[index], dict):
        return dict(entities[index])
    return {"id": object_id}


def brute_force_search(
    manifest: Mapping[str, Any],
    query_vector: Sequence[float],
    *,
    top_k: int,
    distance_fn: Callable[[Sequence[float], Sequence[float]], float] = cosine_distance,
) -> list[dict[str, Any]]:
    dim = int(manifest["dimension"])
    if len(query_vector) != dim:
        raise ValueError(f"query dim {len(query_vector)} != collection dim {dim}")

    q = list(map(float, query_vector))
    ids = manifest.get("object_ids") or []
    vectors = manifest.get("vectors") or []
    scored: list[tuple[float, int]] = []
    for idx, row in enumerate(vectors):
        scored.append((distance_fn(q, row), idx))
    scored.sort(key=lambda item: item[0])

    hits: list[dict[str, Any]] = []
    for distance, idx in scored[: max(1, top_k)]:
        if idx < 0 or idx >= len(ids):
            continue
        object_id = ids[idx]
        entity = entity_for_index(manifest, idx, object_id)
        hits.append({"id": entity.get("id", object_id), "distance": float(distance), "entity": entity})
    return hits
