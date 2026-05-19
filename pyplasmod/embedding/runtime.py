# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Read embedding runtime metadata from Plasmod query provenance."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence

if TYPE_CHECKING:
    from pyplasmod.http.client import PlasmodHttpClient

_FAMILY_RE = re.compile(r"^embedding_runtime_family=(.+)$")
_DIM_RE = re.compile(r"^embedding_runtime_dim=(\d+)$")


@dataclass(frozen=True)
class EmbeddingRuntimeInfo:
    """
    Embedding backend reported by a live Plasmod gateway (from query provenance).

    ``device`` is **not** included in provenance today; use
    :class:`~pyplasmod.embedding.config.EmbedderConfig.from_environ` on the server
    host or your deployment manifest for ``PLASMOD_EMBEDDER_DEVICE``.
    """

    family: str = ""
    dim: Optional[int] = None
    provenance: tuple[str, ...] = field(default_factory=tuple)
    cross_dim_fusion: bool = False

    @property
    def provider(self) -> str:
        """Provider segment before ``:`` in *family* (e.g. ``onnx:model`` → ``onnx``)."""
        if not self.family:
            return ""
        return self.family.split(":", 1)[0]

    def as_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "provider": self.provider,
            "dim": self.dim,
            "cross_dim_fusion": self.cross_dim_fusion,
            "provenance": list(self.provenance),
        }


def parse_embedding_provenance(provenance: Sequence[str]) -> EmbeddingRuntimeInfo:
    """
    Parse ``embedding_runtime_*`` markers from ``POST /v1/query`` response ``provenance``.

    Example entries::

        embedding_runtime_family=onnx:all-MiniLM-L6-v2
        embedding_runtime_dim=384
        cross_dim_fusion=rrf_result_layer
    """
    family = ""
    dim: Optional[int] = None
    fusion = False
    kept: list[str] = []
    for raw in provenance:
        line = (raw or "").strip()
        if not line:
            continue
        kept.append(line)
        if m := _FAMILY_RE.match(line):
            family = m.group(1).strip()
        elif m := _DIM_RE.match(line):
            dim = int(m.group(1))
        elif line.startswith("cross_dim_fusion="):
            fusion = True
    return EmbeddingRuntimeInfo(
        family=family,
        dim=dim,
        provenance=tuple(kept),
        cross_dim_fusion=fusion,
    )


def parse_query_response_embedding(response: Mapping[str, Any]) -> EmbeddingRuntimeInfo:
    """Extract runtime embedding info from a full query JSON object."""
    prov = response.get("provenance")
    if prov is None:
        return EmbeddingRuntimeInfo()
    if isinstance(prov, str):
        return parse_embedding_provenance([prov])
    if isinstance(prov, (list, tuple)):
        return parse_embedding_provenance([str(p) for p in prov])
    return EmbeddingRuntimeInfo()


def fetch_embedding_runtime(
    client: PlasmodHttpClient,
    *,
    workspace_id: str = "w_embedding_probe",
    query_text: str = ".",
    top_k: int = 1,
    **query_kwargs: Any,
) -> EmbeddingRuntimeInfo:
    """
    Run a minimal ``POST /v1/query`` and return parsed embedding provenance.

    Requires a reachable gateway; does not mutate data beyond a read-only query.
    """
    from pyplasmod.data import build_query_body

    body = build_query_body(
        query_text,
        workspace_id,
        top_k=top_k,
        **query_kwargs,
    )
    resp = client.query(body)
    if not isinstance(resp, Mapping):
        return EmbeddingRuntimeInfo()
    return parse_query_response_embedding(resp)
