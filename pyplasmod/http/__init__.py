# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Plasmod HTTP SDK (JSON Tier A + binary RPC helpers)."""

from pyplasmod.http.binary import (
    decode_query_warm_batch_response,
    decode_query_warm_response,
    encode_ingest_batch,
    encode_query_warm,
    encode_query_warm_batch,
)
from pyplasmod.http.client import PlasmodHttpClient
from pyplasmod.http.errors import PlasmodHttpError
from pyplasmod.http.warm_index import (
    WARM_INDEX_DISKANN,
    WARM_INDEX_HNSW,
    WARM_INDEX_IVF_FLAT,
    WARM_INDEX_IVF_PQ,
    WARM_INDEX_IVF_SQ8,
    WARM_INDEX_TYPES,
    normalize_warm_index_type,
    warm_index_ingest_fields,
)

__all__ = [
    "PlasmodHttpClient",
    "PlasmodHttpError",
    "WARM_INDEX_DISKANN",
    "WARM_INDEX_HNSW",
    "WARM_INDEX_IVF_FLAT",
    "WARM_INDEX_IVF_PQ",
    "WARM_INDEX_IVF_SQ8",
    "WARM_INDEX_TYPES",
    "decode_query_warm_batch_response",
    "decode_query_warm_response",
    "encode_ingest_batch",
    "encode_query_warm",
    "encode_query_warm_batch",
    "normalize_warm_index_type",
    "warm_index_ingest_fields",
]
