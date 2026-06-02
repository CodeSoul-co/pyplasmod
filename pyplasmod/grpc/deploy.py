# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Resolve Plasmod gRPC dial targets from HTTP base URLs and env vars."""

from __future__ import annotations

import os
from typing import Optional
from urllib.parse import urlparse

DEFAULT_GRPC_TARGET = "127.0.0.1:19531"
DEFAULT_GRPC_PORT = 19531


def _normalize_target(raw: str) -> str:
    value = str(raw).strip()
    if not value:
        return DEFAULT_GRPC_TARGET
    if value.startswith("grpc://"):
        value = value[len("grpc://") :]
    if "://" in value:
        parsed = urlparse(value)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or DEFAULT_GRPC_PORT
        return f"{host}:{port}"
    if value.startswith("[") and "]" in value:
        return value
    if ":" not in value:
        return f"{value}:{DEFAULT_GRPC_PORT}"
    return value


def resolve_grpc_target(
    target: Optional[str] = None,
    *,
    http_base_url: Optional[str] = None,
) -> str:
    """
    Pick ``host:port`` for ``PlasmodAPIService``.

    Priority: explicit ``target`` → ``PLASMOD_GRPC_ADDR`` / ``PLASMOD_GRPC_TARGET``
    → derive from ``http_base_url`` (same host, port 19531) → ``127.0.0.1:19531``.
    """
    if target is not None and str(target).strip():
        return _normalize_target(target)

    env = os.environ.get("PLASMOD_GRPC_ADDR") or os.environ.get("PLASMOD_GRPC_TARGET")
    if env and str(env).strip():
        return _normalize_target(env)

    if http_base_url:
        parsed = urlparse(str(http_base_url).strip())
        host = parsed.hostname or "127.0.0.1"
        return f"{host}:{DEFAULT_GRPC_PORT}"

    return DEFAULT_GRPC_TARGET


__all__ = ["DEFAULT_GRPC_PORT", "DEFAULT_GRPC_TARGET", "resolve_grpc_target"]
