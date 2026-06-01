# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Deploy-mode helpers: split (API :19530 + mgmt :9091) vs unified (single port)."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

import requests

SPLIT_API_PORT = 19530
SPLIT_MGMT_PORT = 9091


def healthz_urls(api_url: str) -> list[str]:
    """
    Candidate ``GET /healthz`` URLs, most specific first.

    * Split Docker: ``:9091/healthz`` then ``:19530/healthz`` (API port is not used for health).
    * Unified ``make dev`` on ``:19530`` or ``:8080``: only ``{base}/healthz``.
    """
    parsed = urlparse(api_url)
    host = parsed.hostname or "127.0.0.1"
    scheme = parsed.scheme or "http"
    base = api_url.rstrip("/")
    urls: list[str] = []
    if parsed.port == SPLIT_API_PORT:
        urls.append(f"{scheme}://{host}:{SPLIT_MGMT_PORT}/healthz")
    urls.append(f"{base}/healthz")
    return urls


def gateway_is_healthy(api_url: str, *, timeout: float = 2.0) -> bool:
    """Return True if any candidate health URL responds with 2xx."""
    for url in healthz_urls(api_url):
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.ok:
                return True
        except requests.RequestException:
            continue
    return False


def resolve_mgmt_base_url(api_url: str, *, timeout: float = 2.0) -> Optional[str]:
    """
    Mgmt base URL for split deploy (admin + health on :9091).

    Returns ``None`` when API is unified on a single port (including ``make dev`` on :19530).
    """
    parsed = urlparse(api_url)
    if parsed.port != SPLIT_API_PORT:
        return None
    host = parsed.hostname or "127.0.0.1"
    scheme = parsed.scheme or "http"
    mgmt = f"{scheme}://{host}:{SPLIT_MGMT_PORT}"
    try:
        resp = requests.get(f"{mgmt}/healthz", timeout=timeout)
        if resp.ok:
            return mgmt
    except requests.RequestException:
        pass
    return None


__all__ = [
    "SPLIT_API_PORT",
    "SPLIT_MGMT_PORT",
    "gateway_is_healthy",
    "healthz_urls",
    "resolve_mgmt_base_url",
]
