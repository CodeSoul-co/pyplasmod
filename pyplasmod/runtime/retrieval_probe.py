# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Detect whether a Plasmod HTTP gateway can ingest/search warm vectors."""

from __future__ import annotations

import requests

_BRIDGE_MARKERS = (
    "c++ bridge unavailable",
    "cgo_enabled=0",
    "plasmod_retrieval:",
)


def gateway_has_vector_retrieval(base_url: str, *, timeout: float = 3.0) -> bool:
    """
    Return True when ``POST /v1/ingest/vectors`` is handled by the retrieval stack.

    A gateway without CGO retrieval returns HTTP 400 with ``C++ bridge unavailable``.
    """
    url = f"{base_url.rstrip('/')}/v1/ingest/vectors"
    body = {
        "segment_id": "__pyplasmod_probe__",
        "vectors": [[0.0, 0.0, 0.0]],
        "object_ids": ["__probe__"],
        "index_type": "HNSW",
    }
    try:
        resp = requests.post(url, json=body, timeout=timeout)
    except requests.RequestException:
        return False
    if resp.ok:
        return True
    text = (resp.text or "").lower()
    return not any(marker in text for marker in _BRIDGE_MARKERS)
