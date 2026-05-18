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
    decode_query_warm_batch_response,
    decode_query_warm_response,
    encode_ingest_batch,
    encode_query_warm,
    encode_query_warm_batch,
)

try:
    __version__ = _pkg_version("pyplasmod")
except PackageNotFoundError:
    __version__ = "0.0.0"

# Align with ``Plasmod/sdk/python/plasmod_sdk`` naming.
PlasmodClient = PlasmodHttpClient

__all__ = [
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
    "__version__",
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
