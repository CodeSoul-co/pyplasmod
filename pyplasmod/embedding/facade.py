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

"""Simplified user-facing API for Plasmod gateway embedding (CPU / GPU)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence, Union

from pyplasmod.embedding.config import EmbedderConfig, format_capability_table
from pyplasmod.embedding.gateway import GatewayEmbedding
from pyplasmod.embedding.runtime import EmbeddingRuntimeInfo

if TYPE_CHECKING:
    from pyplasmod.easy import EasyPlasmod
    from pyplasmod.http.client import PlasmodHttpClient


class PlasmodEmbedding:
    """
    **Recommended entry** for Plasmod gateway-side text embedding (CPU / GPU).

    Plasmod has no ``POST /v1/embed``; vectors are produced inside ingest/query on the
    server. This class wraps that model with a small, memorable API:

    - **Deploy**: :meth:`use_cpu` / :meth:`use_gpu` / :meth:`apply_config` → ``PLASMOD_EMBEDDER*``
    - **Run**: :meth:`ingest` / :meth:`search` / :meth:`ingest_document`
    - **Observe**: :meth:`runtime` / :meth:`config`

    Example::

        from pyplasmod import PlasmodEmbedding

        with PlasmodEmbedding.connect() as emb:
            print(emb.capabilities())
            emb.use_onnx_cpu(model_path="/models/model.onnx", dim=384, apply=True)
            emb.ingest("hello world", workspace_id="w_demo")
            hits = emb.search("hello", workspace_id="w_demo", top_k=5)
            print(emb.runtime().family, emb.runtime().dim)

    Or attach to :class:`~pyplasmod.easy.EasyPlasmod`::

        with EasyPlasmod() as p:
            p.embedding.ingest("text", workspace_id="w_demo")
    """

    __slots__ = ("_gateway", "_owns_client")

    def __init__(
        self,
        client: Optional[PlasmodHttpClient] = None,
        *,
        easy: Optional[EasyPlasmod] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        admin_key: Optional[str] = None,
    ) -> None:
        """
        :param client: Existing :class:`~pyplasmod.http.client.PlasmodHttpClient`.
        :param easy: Use ``easy.http`` as the underlying client (mutually exclusive with *client*).
        :param base_url: When no *client* / *easy*, create a new client with this URL.
        :param timeout: Passed to a newly created client.
        :param admin_key: Passed to a newly created client.
        """
        if easy is not None:
            if client is not None:
                raise ValueError("pass only one of client= or easy=")
            client = easy.http
            self._owns_client = False
        elif client is not None:
            self._owns_client = False
        else:
            from pyplasmod.http.client import PlasmodHttpClient

            client = PlasmodHttpClient(
                base_url=base_url,
                timeout=timeout,
                admin_key=admin_key,
            )
            self._owns_client = True
        self._gateway = GatewayEmbedding(client)

    @classmethod
    def connect(
        cls,
        base_url: Optional[str] = None,
        *,
        timeout: Optional[float] = None,
        admin_key: Optional[str] = None,
    ) -> PlasmodEmbedding:
        """Create an instance that owns its HTTP client (supports ``with``)."""
        return cls(base_url=base_url, timeout=timeout, admin_key=admin_key)

    @property
    def client(self) -> PlasmodHttpClient:
        """Underlying HTTP client."""
        return self._gateway.client

    @property
    def gateway(self) -> GatewayEmbedding:
        """Lower-level helper (same behavior, more knobs)."""
        return self._gateway

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> PlasmodEmbedding:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ── CPU / GPU configuration (server env) ───────────────────────────────

    @staticmethod
    def capabilities() -> str:
        """ASCII table: which providers support cpu / cuda / metal."""
        return format_capability_table()

    def config(self) -> EmbedderConfig:
        """Read ``PLASMOD_EMBEDDER*`` from the current process environment."""
        return EmbedderConfig.from_environ()

    def apply_config(
        self,
        cfg: EmbedderConfig,
        *,
        overwrite: bool = True,
    ) -> dict[str, str]:
        """
        Write *cfg* to ``os.environ`` (call **before** starting the Plasmod server).

        Returns applied key/value pairs.
        """
        return cfg.apply_to_environ(overwrite=overwrite)

    def use_cpu(
        self,
        provider: str = "onnx",
        *,
        model_path: str = "",
        dim: int = 384,
        vocab_path: str = "",
        apply: bool = False,
    ) -> EmbedderConfig:
        """
        Preset for **CPU** local inference (``PLASMOD_EMBEDDER_DEVICE=cpu``).

        *provider*: ``onnx`` | ``gguf`` | ``tfidf`` (remote providers ignore device).
        """
        cfg = _cpu_preset(provider, model_path=model_path, dim=dim, vocab_path=vocab_path)
        if apply:
            self.apply_config(cfg)
        return cfg

    def use_gpu(
        self,
        provider: str = "onnx",
        *,
        model_path: str = "",
        dim: int = 384,
        vocab_path: str = "",
        cuda_device: str = "0",
        apply: bool = False,
    ) -> EmbedderConfig:
        """
        Preset for **GPU** local inference (``PLASMOD_EMBEDDER_DEVICE=cuda``).

        *provider*: ``onnx`` | ``gguf`` | ``tensorrt``.
        """
        cfg = _gpu_preset(
            provider,
            model_path=model_path,
            dim=dim,
            vocab_path=vocab_path,
            cuda_device=cuda_device,
        )
        if apply:
            self.apply_config(cfg)
        return cfg

    def use_onnx_cpu(self, *, model_path: str, dim: int = 384, vocab_path: str = "", apply: bool = False) -> EmbedderConfig:
        cfg = EmbedderConfig.onnx_cpu(model_path=model_path, dim=dim, vocab_path=vocab_path)
        if apply:
            self.apply_config(cfg)
        return cfg

    def use_onnx_gpu(self, *, model_path: str, dim: int = 384, vocab_path: str = "", apply: bool = False) -> EmbedderConfig:
        cfg = EmbedderConfig.onnx_cuda(model_path=model_path, dim=dim, vocab_path=vocab_path)
        if apply:
            self.apply_config(cfg)
        return cfg

    def use_gguf_cpu(self, *, model_path: str, dim: int = 384, apply: bool = False) -> EmbedderConfig:
        cfg = EmbedderConfig.gguf_cpu(model_path=model_path, dim=dim)
        if apply:
            self.apply_config(cfg)
        return cfg

    def use_gguf_gpu(self, *, model_path: str, dim: int = 384, apply: bool = False) -> EmbedderConfig:
        cfg = EmbedderConfig.gguf_cuda(model_path=model_path, dim=dim)
        if apply:
            self.apply_config(cfg)
        return cfg

    # ── Runtime probe ────────────────────────────────────────────────────────

    def runtime(self, workspace_id: str = "w_demo", **kwargs: Any) -> EmbeddingRuntimeInfo:
        """
        Ask the live gateway which embedder is active (via query ``provenance``).

        ``device`` is not in provenance; use :meth:`config` on the server host.
        """
        return self._gateway.runtime_info(workspace_id=workspace_id, **kwargs)

    def build_query(
        self,
        query_text: str,
        workspace_id: str,
        *,
        embedding_vector: Optional[Sequence[float]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Build ``POST /v1/query`` JSON (does not send HTTP)."""
        return self._gateway.build_query(
            query_text,
            workspace_id,
            embedding_vector=embedding_vector,
            **kwargs,
        )

    # ── Ingest / search (server embeds text) ─────────────────────────────────

    def ingest(
        self,
        text: str,
        workspace_id: str,
        *,
        session_id: str = "",
        agent_id: str = "pyplasmod_embedding",
        embedding_vector: Optional[Sequence[float]] = None,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """
        ``POST /v1/ingest/events`` with *text* (gateway embeds unless *embedding_vector* set).
        """
        return self._gateway.ingest_text_event(
            text,
            workspace_id,
            session_id=session_id,
            agent_id=agent_id,
            embedding_vector=embedding_vector,
            payload=payload,
        )

    def ingest_document(
        self,
        text: str,
        workspace_id: str,
        *,
        title: str = "",
        session_id: str = "",
        agent_id: str = "pyplasmod_embedding",
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """``POST /v1/ingest/document`` — chunked long text, server-side embedding."""
        body: dict[str, Any] = {
            "text": text,
            "workspace_id": workspace_id,
            "agent_id": agent_id,
            "session_id": session_id or f"doc_{workspace_id}",
        }
        if title:
            body["title"] = title
        if chunk_size is not None:
            body["chunk_size"] = chunk_size
        if overlap is not None:
            body["overlap"] = overlap
        if extra:
            body.update(dict(extra))
        return self.client.ingest_document(body)

    def search(
        self,
        query_text: str,
        workspace_id: str,
        *,
        top_k: int = 10,
        embedding_vector: Optional[Sequence[float]] = None,
        **kwargs: Any,
    ) -> Any:
        """
        ``POST /v1/query`` using gateway embedder (CPU/GPU per server env).

        Pass *embedding_vector* to skip server embedding.
        """
        return self._gateway.search(
            query_text,
            workspace_id,
            top_k=top_k,
            embedding_vector=embedding_vector,
            **kwargs,
        )

    def search_with_runtime(
        self,
        query_text: str,
        workspace_id: str,
        **kwargs: Any,
    ) -> tuple[Any, EmbeddingRuntimeInfo]:
        """Like :meth:`search` plus parsed ``embedding_runtime_*`` provenance."""
        return self._gateway.search_with_runtime(query_text, workspace_id, **kwargs)


def open_embedding(
    base_url: Optional[str] = None,
    *,
    timeout: Optional[float] = None,
    admin_key: Optional[str] = None,
) -> PlasmodEmbedding:
    """Alias for :meth:`PlasmodEmbedding.connect` — use as ``with open_embedding() as emb:``."""
    return PlasmodEmbedding.connect(
        base_url=base_url,
        timeout=timeout,
        admin_key=admin_key,
    )


def _cpu_preset(
    provider: str,
    *,
    model_path: str,
    dim: int,
    vocab_path: str,
) -> EmbedderConfig:
    p = provider.strip().lower()
    if p == "onnx":
        return EmbedderConfig.onnx_cpu(model_path=model_path, dim=dim, vocab_path=vocab_path)
    if p == "gguf":
        return EmbedderConfig.gguf_cpu(model_path=model_path, dim=dim)
    if p == "tfidf":
        return EmbedderConfig.tfidf(dim=dim or 256)
    return EmbedderConfig(provider=p, device="cpu", dim=dim, model_path=model_path)  # type: ignore[arg-type]


def _gpu_preset(
    provider: str,
    *,
    model_path: str,
    dim: int,
    vocab_path: str,
    cuda_device: str,
) -> EmbedderConfig:
    p = provider.strip().lower()
    if p == "onnx":
        return EmbedderConfig.onnx_cuda(
            model_path=model_path,
            dim=dim,
            vocab_path=vocab_path,
            cuda_visible_devices=cuda_device,
        )
    if p == "gguf":
        return EmbedderConfig.gguf_cuda(
            model_path=model_path,
            dim=dim,
            cuda_visible_devices=cuda_device,
        )
    if p == "tensorrt":
        return EmbedderConfig.tensorrt_cuda(
            engine_path=model_path,
            dim=dim,
            vocab_path=vocab_path,
            cuda_visible_devices=cuda_device,
        )
    return EmbedderConfig(provider=p, device="cuda", dim=dim, model_path=model_path)  # type: ignore[arg-type]
