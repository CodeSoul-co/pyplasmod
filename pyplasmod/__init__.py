# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Python SDK for Plasmod — HTTP Tier A + binary RPC (Plasmod ``docs/api``).

Topic help: ``from pyplasmod import plasmod_help; plasmod_help()`` or run ``python -m pyplasmod``.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from pyplasmod.batch import (
    DEFAULT_BATCH_SIZE,
    MAX_BATCH_VECTORS,
    BatchResult,
    iter_batches,
    validate_batch_size,
)
from pyplasmod.exceptions import (
    ConnectError,
    ParamError,
    PlasmodException,
    PlasmodUnavailableException,
)
from pyplasmod.client import (
    DEFAULT_API_URI,
    DEFAULT_DOCKER_IMAGE,
    DEFAULT_UNIFIED_URI,
    PlasmodClient,
)
from pyplasmod.easy import EasyPlasmod
from pyplasmod.embedding import (
    EmbedderConfig,
    EmbeddingRuntimeInfo,
    GatewayEmbedding,
    PlasmodEmbedding,
    format_capability_table,
    open_embedding,
)
from pyplasmod.package_help import plasmod_help, plasmod_topics
from pyplasmod.http import (
    PlasmodHttpClient,
    PlasmodHttpError,
    WARM_INDEX_DISKANN,
    WARM_INDEX_HNSW,
    WARM_INDEX_IVF_FLAT,
    WARM_INDEX_IVF_PQ,
    WARM_INDEX_IVF_SQ8,
    WARM_INDEX_TYPES,
    decode_query_warm_batch_response,
    decode_query_warm_response,
    encode_ingest_batch,
    encode_query_warm,
    encode_query_warm_batch,
    normalize_warm_index_type,
    warm_index_ingest_fields,
)

try:
    __version__ = _pkg_version("pyplasmod")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "DEFAULT_API_URI",
    "DEFAULT_DOCKER_IMAGE",
    "DEFAULT_UNIFIED_URI",
    "BatchResult",
    "ConnectError",
    "DEFAULT_BATCH_SIZE",
    "EasyPlasmod",
    "EmbedderConfig",
    "EmbeddingRuntimeInfo",
    "GatewayEmbedding",
    "MAX_BATCH_VECTORS",
    "PlasmodEmbedding",
    "open_embedding",
    "ParamError",
    "plasmod_help",
    "plasmod_topics",
    "PlasmodClient",
    "PlasmodException",
    "PlasmodHttpClient",
    "PlasmodHttpError",
    "PlasmodUnavailableException",
    "WARM_INDEX_DISKANN",
    "WARM_INDEX_HNSW",
    "WARM_INDEX_IVF_FLAT",
    "WARM_INDEX_IVF_PQ",
    "WARM_INDEX_IVF_SQ8",
    "WARM_INDEX_TYPES",
    "__version__",
    "normalize_warm_index_type",
    "warm_index_ingest_fields",
    "decode_query_warm_batch_response",
    "decode_query_warm_response",
    "encode_ingest_batch",
    "encode_query_warm",
    "encode_query_warm_batch",
    "format_capability_table",
    "iter_batches",
    "validate_batch_size",
]


def __getattr__(name: str):
    """Lazy import for optional LangChain integration."""
    if name == "PlasmodVectorStore":
        from pyplasmod.langchain import PlasmodVectorStore

        return PlasmodVectorStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
