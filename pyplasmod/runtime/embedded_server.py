# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Start ``plasmod-server`` as a child process (embedded gateway, no Docker)."""

from __future__ import annotations

import atexit
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

from pyplasmod.exceptions import ConnectError

DEFAULT_STARTUP_TIMEOUT = 120.0
_HEALTH_POLL_INTERVAL = 0.5

_SERVER_NAMES = ("plasmod-server", "plasmod-server.exe")


@dataclass
class _EmbeddedState:
    process: subprocess.Popen[str]
    base_url: str
    data_dir: Path
    refs: int = 0


_STATE: Optional[_EmbeddedState] = None


def embedded_enabled(explicit: Optional[bool]) -> bool:
    if explicit is not None:
        return explicit
    raw = os.environ.get("PLASMOD_EMBEDDED", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def find_plasmod_server_binary() -> Optional[Path]:
    env = os.environ.get("PLASMOD_SERVER_BIN", "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p

    for name in _SERVER_NAMES:
        found = shutil.which(name)
        if found:
            return Path(found)

    here = Path.cwd()
    for parent in [here, *here.parents]:
        for rel in (
            "bin/plasmod-server",
            "bin/plasmod-server.exe",
            "Plasmod/bin/plasmod-server",
            "Plasmod/bin/plasmod-server.exe",
        ):
            candidate = parent / rel
            if candidate.is_file():
                return candidate
    return None


def pick_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _health_ok(base_url: str, *, timeout: float = 2.0) -> bool:
    try:
        resp = requests.get(f"{base_url.rstrip('/')}/healthz", timeout=timeout)
        return resp.ok
    except requests.RequestException:
        return False


def ensure_embedded_server(
    data_dir: Path,
    *,
    binary: Optional[Path] = None,
    startup_timeout: float = DEFAULT_STARTUP_TIMEOUT,
) -> str:
    """
    Ensure an embedded ``plasmod-server`` is listening.

    Returns unified base URL (``http://127.0.0.1:<port>``).
    """
    global _STATE
    data_dir = data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    if _STATE is not None and _STATE.process.poll() is None:
        if _health_ok(_STATE.base_url):
            _STATE.refs += 1
            return _STATE.base_url

    binary = binary or find_plasmod_server_binary()
    if binary is None:
        raise ConnectError(
            "Plasmod embedded mode requires plasmod-server on PATH or PLASMOD_SERVER_BIN. "
            "Build from Plasmod repo: `make cpp && make build`, or set PLASMOD_EMBEDDED=0 "
            "to fall back to Docker auto-start.",
        )

    host = os.environ.get("PLASMOD_EMBEDDED_HOST", "127.0.0.1")
    port = pick_free_port(host)
    base_url = f"http://{host}:{port}"

    env = os.environ.copy()
    env.update(
        {
            "PLASMOD_LISTEN_MODE": "unified",
            "PLASMOD_HTTP_ADDR": f"{host}:{port}",
            "PLASMOD_SHOW_BANNER": "0",
            "PLASMOD_STORAGE": "disk",
            "PLASMOD_DATA_DIR": str(data_dir),
            "PLASMOD_EMBEDDER": env.get("PLASMOD_EMBEDDER", "tfidf"),
        }
    )

    proc = subprocess.Popen(
        [str(binary)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    deadline = time.monotonic() + startup_timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise ConnectError(
                f"plasmod-server exited early (code={proc.returncode}). "
                f"Build with retrieval: `make cpp && make build`.",
            )
        if _health_ok(base_url):
            _STATE = _EmbeddedState(process=proc, base_url=base_url, data_dir=data_dir, refs=1)
            atexit.register(_shutdown_embedded_server)
            return base_url
        time.sleep(_HEALTH_POLL_INTERVAL)

    proc.terminate()
    raise ConnectError(f"embedded plasmod-server did not become healthy within {startup_timeout:.0f}s")


def release_embedded_server() -> None:
    global _STATE
    if _STATE is None:
        return
    _STATE.refs -= 1
    if _STATE.refs <= 0:
        _shutdown_embedded_server()


def _shutdown_embedded_server() -> None:
    global _STATE
    if _STATE is None:
        return
    proc = _STATE.process
    _STATE = None
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


__all__ = [
    "embedded_enabled",
    "ensure_embedded_server",
    "find_plasmod_server_binary",
    "release_embedded_server",
]
