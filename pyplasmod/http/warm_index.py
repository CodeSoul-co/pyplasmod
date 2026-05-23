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

"""Warm-segment ANN index types for ingest (aligned with Plasmod ``schemas/warm_segment_ingest.go``)."""

from __future__ import annotations

from typing import Any, Mapping, Optional

# Supported index_type values for POST /v1/ingest/vectors (JSON).
WARM_INDEX_HNSW = "HNSW"
WARM_INDEX_IVF_FLAT = "IVF_FLAT"
WARM_INDEX_IVF_PQ = "IVF_PQ"
WARM_INDEX_IVF_SQ8 = "IVF_SQ8"
WARM_INDEX_DISKANN = "DISKANN"

WARM_INDEX_TYPES = frozenset(
    {
        WARM_INDEX_HNSW,
        WARM_INDEX_IVF_FLAT,
        WARM_INDEX_IVF_PQ,
        WARM_INDEX_IVF_SQ8,
        WARM_INDEX_DISKANN,
    }
)


def normalize_warm_index_type(index_type: Optional[str]) -> str:
    """
    Uppercase and validate ``index_type``. Empty/None → ``HNSW`` (server default).

    Raises:
        ValueError: Unknown index type.
    """
    if index_type is None:
        return WARM_INDEX_HNSW
    t = str(index_type).strip().upper()
    if t == "":
        return WARM_INDEX_HNSW
    if t not in WARM_INDEX_TYPES:
        raise ValueError(
            f"index_type must be one of {', '.join(sorted(WARM_INDEX_TYPES))} (got {index_type!r})"
        )
    return t


def warm_index_ingest_fields(
    index_type: Optional[str] = None,
    *,
    ivf_nlist: int = 0,
    ivf_nprobe: int = 0,
    ivf_m: int = 0,
    ivf_nbits: int = 0,
    ivf_sq_type: str = "",
) -> dict[str, Any]:
    """
    Build optional JSON fields for ``POST /v1/ingest/vectors`` / ingest helpers.

    Omits keys when unset so default HNSW requests stay minimal.
    """
    out: dict[str, Any] = {}
    normalized = normalize_warm_index_type(index_type)
    if index_type is not None and str(index_type).strip() != "":
        out["index_type"] = normalized
    elif ivf_nlist or ivf_nprobe or ivf_m or ivf_nbits or str(ivf_sq_type).strip():
        out["index_type"] = normalized
    if ivf_nlist:
        out["ivf_nlist"] = int(ivf_nlist)
    if ivf_nprobe:
        out["ivf_nprobe"] = int(ivf_nprobe)
    if ivf_m:
        out["ivf_m"] = int(ivf_m)
    if ivf_nbits:
        out["ivf_nbits"] = int(ivf_nbits)
    sq = str(ivf_sq_type).strip()
    if sq:
        out["ivf_sq_type"] = sq
    return out


def warm_index_options_from_mapping(body: Mapping[str, Any]) -> dict[str, Any]:
    """Extract warm-index kwargs from a request body mapping."""
    return warm_index_ingest_fields(
        body.get("index_type"),
        ivf_nlist=int(body.get("ivf_nlist") or 0),
        ivf_nprobe=int(body.get("ivf_nprobe") or 0),
        ivf_m=int(body.get("ivf_m") or 0),
        ivf_nbits=int(body.get("ivf_nbits") or 0),
        ivf_sq_type=str(body.get("ivf_sq_type") or ""),
    )
