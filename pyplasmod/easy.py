# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Small user-facing facade over :class:`~pyplasmod.http.client.PlasmodHttpClient`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Union

from pyplasmod.data import build_query_body, upload as data_upload
from pyplasmod.embedding import PlasmodEmbedding
from pyplasmod.embedding.config import EmbedderConfig
from pyplasmod.embedding.runtime import EmbeddingRuntimeInfo
from pyplasmod.http.client import PlasmodHttpClient


class EasyPlasmod:
    """
    Minimal API for demos and app integration: health, ingest, query, list memories.

    Full gateway surface (admin, RPC, internal task/MAS, …) remains on
    :attr:`http` (:class:`~pyplasmod.http.client.PlasmodHttpClient`).
    """

    __slots__ = ("http", "_embedding")

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        timeout: Optional[float] = None,
        admin_key: Optional[str] = None,
        session: Optional[Any] = None,
    ) -> None:
        """
        :param base_url: 服务根 URL；默认读 ``PLASMOD_BASE_URL`` / ``ANDB_BASE_URL``，再 ``http://127.0.0.1:8080``。
        :param timeout: HTTP 超时秒数；默认读 ``PLASMOD_HTTP_TIMEOUT`` / ``ANDB_HTTP_TIMEOUT``，再 ``30``。
        :param admin_key: Admin API Key；默认读 ``PLASMOD_ADMIN_API_KEY`` / ``ANDB_ADMIN_API_KEY``。访问 ``/v1/admin/*`` 时自动加 ``X-Admin-Key``。
        :param session: 可选传入已有 ``requests.Session`` 以复用连接。
        """
        self.http = PlasmodHttpClient(
            base_url=base_url,
            timeout=timeout,
            admin_key=admin_key,
            session=session,
        )
        self._embedding: Optional[PlasmodEmbedding] = None

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> EasyPlasmod:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def health(self) -> Any:
        """``GET /healthz`` — 服务存活探针。"""
        return self.http.health()

    def system_mode(self) -> Any:
        """``GET /v1/system/mode`` — 系统模式等。"""
        return self.http.system_mode()

    def query(self, body: Mapping[str, Any]) -> Any:
        """``POST /v1/query`` — *body* 为查询 JSON（常用 :func:`pyplasmod.data.build_query_body` 生成）。"""
        return self.http.query(body)

    def search(self, query_text: str, workspace_id: str, **kwargs: Any) -> Any:
        """``build_query_body`` + ``POST /v1/query``；*kwargs* 传给 :func:`pyplasmod.data.build_query_body`。"""
        return self.http.query(build_query_body(query_text, workspace_id, **kwargs))

    def ingest_event(self, event: Mapping[str, Any]) -> Any:
        """``POST /v1/ingest/events`` — 单条事件 *event* 字典，字段须与服务端一致。"""
        return self.http.ingest_event(event)

    def ingest_document(self, body: Mapping[str, Any]) -> Any:
        """``POST /v1/ingest/document`` — *body* 至少含 ``text``，常含 ``workspace_id`` / ``agent_id`` / ``session_id`` / ``title``。"""
        return self.http.ingest_document(body)

    def upload_fbin(
        self,
        dataset: str,
        workspace_id: str,
        path: Union[str, Path],
        **kwargs: Any,
    ) -> int:
        """``.fbin`` → :func:`pyplasmod.data.upload`（固定 ``client=self.http``）；*kwargs* 同 ``upload``。"""
        return int(data_upload(dataset, workspace_id, path, client=self.http, **kwargs))

    @property
    def embedding(self) -> PlasmodEmbedding:
        """
        Gateway-side embedding helper (ingest / search / CPU·GPU presets).

        See :class:`~pyplasmod.embedding.facade.PlasmodEmbedding` and ``docs/EMBEDDING.md``.
        """
        if self._embedding is None:
            self._embedding = PlasmodEmbedding(easy=self)
        return self._embedding

    def embed_ingest(self, text: str, workspace_id: str, **kwargs: Any) -> Any:
        """Shorthand: ``self.embedding.ingest(text, workspace_id, **kwargs)``."""
        return self.embedding.ingest(text, workspace_id, **kwargs)

    def embed_search(self, query_text: str, workspace_id: str, **kwargs: Any) -> Any:
        """Shorthand: ``self.embedding.search(query_text, workspace_id, **kwargs)``."""
        return self.embedding.search(query_text, workspace_id, **kwargs)

    def gateway_embedding(self) -> PlasmodEmbedding:
        """Alias for :attr:`embedding` (backward compatible)."""
        return self.embedding

    def embedder_config(self) -> EmbedderConfig:
        """``PLASMOD_EMBEDDER*`` on this machine (deployment / client env)."""
        return self.embedding.config()

    def embedding_runtime(self, **kwargs: Any) -> EmbeddingRuntimeInfo:
        """Probe live gateway embedder via ``POST /v1/query`` provenance."""
        return self.embedding.runtime(**kwargs)

    def memories(self, workspace_id: str, **params: Any) -> Any:
        """``GET /v1/memory`` with ``workspace_id`` merged into query ``params``."""
        p: dict[str, Any] = {"workspace_id": workspace_id}
        p.update(params)
        return self.http.memory_get(params=p)


__all__ = ["EasyPlasmod"]
