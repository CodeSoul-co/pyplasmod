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

"""High-level helpers: server-side embedding via ingest/query (no standalone /v1/embed)."""

from __future__ import annotations

import datetime as dt
import time
from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence

from pyplasmod.data import build_query_body
from pyplasmod.embedding.config import EmbedderConfig
from pyplasmod.embedding.runtime import (
    EmbeddingRuntimeInfo,
    fetch_embedding_runtime,
    parse_query_response_embedding,
)

if TYPE_CHECKING:
    from pyplasmod.http.client import PlasmodHttpClient


def _now_iso() -> str:
    return (
        dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def _default_event_id(workspace_id: str) -> str:
    return f"evt_emb_{workspace_id}_{int(time.time() * 1000)}"


class GatewayEmbedding:
    """
    Work with **gateway-side** embedding (Plasmod embedder, not local Python models).

    Plasmod has no dedicated embed HTTP route. Text is embedded inside:

    - ``POST /v1/ingest/events`` / ``/v1/ingest/document`` (index path)
    - ``POST /v1/query`` when ``query_text`` is set and ``embedding_vector`` is omitted

    CPU vs GPU is selected on the **server** via ``PLASMOD_EMBEDDER`` +
    ``PLASMOD_EMBEDDER_DEVICE`` (see :class:`EmbedderConfig`).
    """

    __slots__ = ("_client",)

    def __init__(self, client: PlasmodHttpClient) -> None:
        self._client = client

    @property
    def client(self) -> PlasmodHttpClient:
        return self._client

    def configured_embedder(self) -> EmbedderConfig:
        """
        Read embedder env from **this Python process** (client host).

        For the live gateway backend, prefer :meth:`runtime_info`.
        """
        return EmbedderConfig.from_environ()

    def runtime_info(self, **query_kwargs: Any) -> EmbeddingRuntimeInfo:
        """Probe the gateway via a minimal query and parse ``embedding_runtime_*`` provenance."""
        return fetch_embedding_runtime(self._client, **query_kwargs)

    def build_query(
        self,
        query_text: str,
        workspace_id: str,
        *,
        embedding_vector: Optional[Sequence[float]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Build ``POST /v1/query`` JSON.

        Omit ``embedding_vector`` to use the gateway embedder (CPU or GPU per server env).
        Pass ``embedding_vector`` to skip server embedding (client-supplied dense query).
        """
        return build_query_body(
            query_text,
            workspace_id,
            embedding_vector=embedding_vector,
            **kwargs,
        )

    def search(
        self,
        query_text: str,
        workspace_id: str,
        *,
        embedding_vector: Optional[Sequence[float]] = None,
        **kwargs: Any,
    ) -> Any:
        """``build_query`` + ``POST /v1/query``."""
        body = self.build_query(
            query_text,
            workspace_id,
            embedding_vector=embedding_vector,
            **kwargs,
        )
        return self._client.query(body)

    def ingest_text_event(
        self,
        text: str,
        workspace_id: str,
        *,
        tenant_id: str = "t_demo",
        agent_id: str = "pyplasmod_embedding",
        session_id: str = "",
        event_type: str = "observation",
        event_id: str = "",
        source: str = "pyplasmod.embedding",
        version: int = 1,
        embedding_vector: Optional[Sequence[float]] = None,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """
        ``POST /v1/ingest/events`` with text; gateway embeds unless ``embedding_vector`` is set.

        Plasmod requires canonical event fields (``event_type``, timestamps, etc.);
        this helper fills defaults aligned with ``pyplasmod.data`` ingest events.
        """
        pl: dict[str, Any] = {"text": text}
        if payload:
            pl.update(dict(payload))
        ts = _now_iso()
        event: dict[str, Any] = {
            "event_id": event_id.strip() or _default_event_id(workspace_id),
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "session_id": session_id or f"ingest_{workspace_id}",
            "event_type": event_type,
            "event_time": ts,
            "ingest_time": ts,
            "visible_time": ts,
            "payload": pl,
            "source": source,
            "version": version,
        }
        if embedding_vector is not None:
            event["embedding_vector"] = [float(x) for x in embedding_vector]
        return self._client.ingest_event(event)

    def search_with_runtime(
        self,
        query_text: str,
        workspace_id: str,
        **kwargs: Any,
    ) -> tuple[Any, EmbeddingRuntimeInfo]:
        """Like :meth:`search` but also return parsed embedding provenance from the response."""
        resp = self.search(query_text, workspace_id, **kwargs)
        if isinstance(resp, Mapping):
            return resp, parse_query_response_embedding(resp)
        return resp, EmbeddingRuntimeInfo()
