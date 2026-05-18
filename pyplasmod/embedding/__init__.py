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

"""
Plasmod **gateway-side** embedding: CPU/GPU provider matrix, env presets, and query helpers.

Plasmod embeds text inside ingest/query; there is no ``POST /v1/embed``. This package
mirrors the server's ``PLASMOD_EMBEDDER`` / ``PLASMOD_EMBEDDER_DEVICE`` design and helps
you probe ``embedding_runtime_*`` provenance from ``POST /v1/query``.

Quick start (recommended)::

    from pyplasmod import PlasmodEmbedding

    with PlasmodEmbedding.connect() as emb:
        print(emb.capabilities())
        emb.ingest("hello", workspace_id="w_demo")
        print(emb.search("hello", workspace_id="w_demo", top_k=3))
        print(emb.runtime())

Advanced / deployment::

    emb.use_onnx_gpu(model_path="/models/model.onnx", dim=384, apply=True)
    # then start Plasmod with those env vars
"""

from pyplasmod.embedding.config import (
    EMBEDDER_CAPABILITIES,
    GPU_ONLY_PROVIDERS,
    LOCAL_DUAL_PATH_PROVIDERS,
    REMOTE_HTTP_PROVIDERS,
    EmbedderConfig,
    EmbedderDevice,
    EmbedderProvider,
    ProviderCapability,
    format_capability_table,
    list_embedder_capabilities,
)
from pyplasmod.embedding.facade import PlasmodEmbedding, open_embedding
from pyplasmod.embedding.gateway import GatewayEmbedding
from pyplasmod.embedding.runtime import (
    EmbeddingRuntimeInfo,
    fetch_embedding_runtime,
    parse_embedding_provenance,
    parse_query_response_embedding,
)

__all__ = [
    "PlasmodEmbedding",
    "open_embedding",
    "EMBEDDER_CAPABILITIES",
    "GPU_ONLY_PROVIDERS",
    "LOCAL_DUAL_PATH_PROVIDERS",
    "REMOTE_HTTP_PROVIDERS",
    "EmbedderConfig",
    "EmbedderDevice",
    "EmbedderProvider",
    "EmbeddingRuntimeInfo",
    "GatewayEmbedding",
    "ProviderCapability",
    "fetch_embedding_runtime",
    "format_capability_table",
    "list_embedder_capabilities",
    "parse_embedding_provenance",
    "parse_query_response_embedding",
]
