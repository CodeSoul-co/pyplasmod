# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Milvus-style warm vector storage backed by ``libplasmod_retrieval`` (in-process)."""

from __future__ import annotations

import json
from array import array
from ctypes import c_float, c_int64, cast
from pathlib import Path
from typing import Any, Optional, Sequence

from pyplasmod.embedded._lib import find_retrieval_library, load_retrieval_library
from pyplasmod.http.warm_index import normalize_warm_index_type


class EmbeddedWarmStore:
    """
    In-process warm-segment ANN (HNSW / IVF) without HTTP or Docker.

    Persists vectors + object ids under ``<profile_root>/collections/<name>/`` so
    ``PlasmodClient("foo.db")`` can reload after restart (rebuilds the C++ index).
    """

    def __init__(self, profile_root: Path, *, lib_path: Optional[Path] = None) -> None:
        self._root = profile_root.resolve()
        self._lib = load_retrieval_library(lib_path)
        self._collections_dir = self._root / "collections"
        self._collections_dir.mkdir(parents=True, exist_ok=True)
        self._loaded_segments: set[str] = set()

    @staticmethod
    def is_available() -> bool:
        return find_retrieval_library() is not None

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
        if len(object_ids) != len(vectors):
            raise ValueError("object_ids and vectors length mismatch")
        if not vectors:
            raise ValueError("vectors must be non-empty")
        dim = len(vectors[0])
        for i, row in enumerate(vectors):
            if len(row) != dim:
                raise ValueError(f"vectors[{i}] dim {len(row)} != {dim}")

        idx = normalize_warm_index_type(index_type)
        self._build_segment(segment_id, vectors, dim, idx, ivf or {})
        self._loaded_segments.add(segment_id)

        if persist:
            coll_dir = self._collections_dir / collection_name
            coll_dir.mkdir(parents=True, exist_ok=True)
            manifest = {
                "segment_id": segment_id,
                "object_ids": list(object_ids),
                "dimension": dim,
                "index_type": idx,
                "vectors": [list(map(float, row)) for row in vectors],
            }
            (coll_dir / "warm_manifest.json").write_text(
                json.dumps(manifest, indent=2),
                encoding="utf-8",
            )

        return {
            "status": "ok",
            "segment_id": segment_id,
            "ingested": len(vectors),
            "vector_dim": dim,
            "index_type": idx,
            "direct_warm": True,
            "embedded": True,
        }

    def search(
        self,
        collection_name: str,
        *,
        segment_id: str,
        query_vector: Sequence[float],
        top_k: int = 10,
    ) -> dict[str, Any]:
        self._ensure_loaded(collection_name, segment_id)
        manifest = self._read_manifest(collection_name)
        dim = int(manifest["dimension"])
        if len(query_vector) != dim:
            raise ValueError(f"query dim {len(query_vector)} != collection dim {dim}")

        q = array("f", (float(x) for x in query_vector))
        out_ids = (c_int64 * top_k)()
        out_dists = (c_float * top_k)()
        qbuf = (c_float * len(q))(*q)
        rc = self._lib.plasmod_segment_search(
            segment_id.encode("utf-8"),
            cast(qbuf, c_float * len(q)),
            1,
            top_k,
            out_ids,
            out_dists,
        )
        if rc != 0:
            raise RuntimeError(f"plasmod_segment_search failed (rc={rc})")

        id_list = manifest["object_ids"]
        hits: list[str] = []
        for raw_idx in out_ids:
            idx = int(raw_idx)
            if 0 <= idx < len(id_list):
                hits.append(str(id_list[idx]))
        return {
            "status": "ok",
            "objects": hits,
            "warm_segment_id": segment_id,
            "tier": "warm_segment",
            "embedded": True,
        }

    def _build_segment(
        self,
        segment_id: str,
        vectors: Sequence[Sequence[float]],
        dim: int,
        index_type: str,
        ivf: dict[str, Any],
    ) -> None:
        flat = array("f")
        for row in vectors:
            flat.extend(float(x) for x in row)
        buf = (c_float * len(flat))(*flat)
        nlist = int(ivf.get("ivf_nlist") or 0)
        nprobe = int(ivf.get("ivf_nprobe") or 0)
        m = int(ivf.get("ivf_m") or 0)
        nbits = int(ivf.get("ivf_nbits") or 0)
        sq_type = str(ivf.get("ivf_sq_type") or "")
        sq_b = sq_type.encode("utf-8") if sq_type else None
        rc = self._lib.plasmod_segment_build_with_type(
            segment_id.encode("utf-8"),
            cast(buf, c_float * len(flat)),
            len(vectors),
            dim,
            index_type.encode("utf-8"),
            nlist,
            nprobe,
            m,
            nbits,
            sq_b,
        )
        if rc != 0:
            raise RuntimeError(f"plasmod_segment_build_with_type failed (rc={rc})")

    def _read_manifest(self, collection_name: str) -> dict[str, Any]:
        path = self._collections_dir / collection_name / "warm_manifest.json"
        if not path.is_file():
            raise ValueError(f"embedded collection {collection_name!r} has no warm data")
        return json.loads(path.read_text(encoding="utf-8"))

    def _ensure_loaded(self, collection_name: str, segment_id: str) -> None:
        if segment_id in self._loaded_segments:
            return
        manifest = self._read_manifest(collection_name)
        if manifest.get("segment_id") != segment_id:
            raise ValueError("segment_id mismatch for embedded collection")
        self._build_segment(
            segment_id,
            manifest["vectors"],
            int(manifest["dimension"]),
            str(manifest.get("index_type") or "HNSW"),
            {},
        )
        self._loaded_segments.add(segment_id)
