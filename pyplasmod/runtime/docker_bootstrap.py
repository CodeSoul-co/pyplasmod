# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Start the published Plasmod Docker image when the local API port is down."""

from __future__ import annotations

import os
import socket
import subprocess
import time
from typing import Optional
from urllib.parse import urlparse

from pyplasmod.exceptions import ConnectError
from pyplasmod.http.deploy import SPLIT_API_PORT, gateway_is_healthy

DEFAULT_DOCKER_IMAGE = "oneflybird/plasmod"
DEFAULT_CONTAINER_NAME = "plasmod"
DEFAULT_API_PORT = SPLIT_API_PORT
DEFAULT_MGMT_PORT = 9091
DEFAULT_STARTUP_TIMEOUT = 120.0
DEFAULT_PULL_TIMEOUT = 600.0
_HEALTH_POLL_INTERVAL = 0.5

_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0"})


def _env_flag(name: str, *, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off")


def auto_start_enabled(explicit: Optional[bool]) -> bool:
    """Whether Docker auto-start is on (constructor flag overrides ``PLASMOD_AUTO_START``)."""
    if explicit is not None:
        return explicit
    return _env_flag("PLASMOD_AUTO_START", default=True)


def is_local_gateway_url(api_url: str, *, api_port: int = DEFAULT_API_PORT) -> bool:
    """True when ``api_url`` points at a local split-deploy API port (default ``:19530``)."""
    parsed = urlparse(api_url)
    host = (parsed.hostname or "127.0.0.1").lower()
    if host not in _LOCAL_HOSTS:
        return False
    port = parsed.port
    if port is None:
        return False
    return port == api_port


def port_is_open(host: str, port: int, *, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _docker_cmd(*args: str, timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ConnectError(
            "Docker is not installed or not on PATH. "
            f"Start Plasmod manually, e.g.: { _docker_run_line(DEFAULT_DOCKER_IMAGE) }",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ConnectError(f"Docker command timed out: docker {' '.join(args)}") from exc


def _docker_run_line(image: str, *, container_name: str = DEFAULT_CONTAINER_NAME) -> str:
    return (
        f"docker run -d --name {container_name} "
        f"-p {DEFAULT_MGMT_PORT}:{DEFAULT_MGMT_PORT} "
        f"-p {DEFAULT_API_PORT}:{DEFAULT_API_PORT} {image}"
    )


def _docker_image_present(image: str) -> bool:
    proc = _docker_cmd("image", "inspect", image, timeout=30.0)
    return proc.returncode == 0


def _docker_pull(image: str, *, timeout: float) -> None:
    proc = _docker_cmd("pull", image, timeout=timeout)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise ConnectError(f"docker pull {image} failed: {err}")


def _docker_container_state(name: str) -> Optional[str]:
    """Return container status string, or None if the container does not exist."""
    proc = _docker_cmd(
        "ps",
        "-a",
        "--filter",
        f"name=^{name}$",
        "--format",
        "{{.Status}}",
        timeout=15.0,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise ConnectError(f"docker ps failed: {err}")
    line = (proc.stdout or "").strip().splitlines()
    if not line:
        return None
    return line[0]


def _docker_start_container(name: str) -> None:
    proc = _docker_cmd("start", name, timeout=60.0)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise ConnectError(f"docker start {name} failed: {err}")


def _docker_run_container(image: str, *, container_name: str) -> None:
    proc = _docker_cmd(
        "run",
        "-d",
        "--name",
        container_name,
        "-p",
        f"{DEFAULT_MGMT_PORT}:{DEFAULT_MGMT_PORT}",
        "-p",
        f"{DEFAULT_API_PORT}:{DEFAULT_API_PORT}",
        image,
        timeout=60.0,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise ConnectError(
            f"docker run failed: {err}. Try: {_docker_run_line(image, container_name=container_name)}",
        )


def _wait_for_gateway(api_url: str, *, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if gateway_is_healthy(api_url, timeout=min(2.0, _HEALTH_POLL_INTERVAL + 1)):
            return
        time.sleep(_HEALTH_POLL_INTERVAL)
    raise ConnectError(
        f"Plasmod gateway at {api_url} did not become healthy within {timeout:.0f}s. "
        f"Check logs: docker logs {os.environ.get('PLASMOD_DOCKER_CONTAINER', DEFAULT_CONTAINER_NAME)}",
    )


def ensure_docker_gateway(
    api_url: str,
    *,
    image: Optional[str] = None,
    container_name: Optional[str] = None,
    startup_timeout: float = DEFAULT_STARTUP_TIMEOUT,
    pull_timeout: float = DEFAULT_PULL_TIMEOUT,
) -> None:
    """
    Ensure a local split-deploy Plasmod gateway is reachable at ``api_url``.

    If ``GET /healthz`` already succeeds, return immediately. Otherwise, on a local
    ``:19530`` URL, start or create the Docker container (pull ``image`` when missing).
    """
    api_url = api_url.rstrip("/")
    if gateway_is_healthy(api_url):
        return

    if not is_local_gateway_url(api_url):
        raise ConnectError(
            f"Plasmod gateway at {api_url} is not reachable and auto-start only applies "
            f"to local http://127.0.0.1:{DEFAULT_API_PORT} (set PLASMOD_AUTO_START=0 to skip).",
        )

    image = image or os.environ.get("PLASMOD_DOCKER_IMAGE", DEFAULT_DOCKER_IMAGE)
    container_name = container_name or os.environ.get(
        "PLASMOD_DOCKER_CONTAINER", DEFAULT_CONTAINER_NAME
    )

    parsed = urlparse(api_url)
    host = parsed.hostname or "127.0.0.1"
    if port_is_open(host, DEFAULT_API_PORT) and not gateway_is_healthy(api_url):
        raise ConnectError(
            f"Port {DEFAULT_API_PORT} on {host} is open but Plasmod health check failed "
            f"(tried split :{DEFAULT_MGMT_PORT} and unified {api_url}/healthz). "
            "Stop the conflicting process, use unified make dev on :8080, or set PLASMOD_BASE_URL.",
        )

    state = _docker_container_state(container_name)
    if state is not None:
        if not state.lower().startswith("up"):
            _docker_start_container(container_name)
        _wait_for_gateway(api_url, timeout=startup_timeout)
        return

    if not _docker_image_present(image):
        _docker_pull(image, timeout=pull_timeout)

    _docker_run_container(image, container_name=container_name)
    _wait_for_gateway(api_url, timeout=startup_timeout)


__all__ = [
    "DEFAULT_CONTAINER_NAME",
    "DEFAULT_API_PORT",
    "DEFAULT_MGMT_PORT",
    "DEFAULT_PULL_TIMEOUT",
    "DEFAULT_STARTUP_TIMEOUT",
    "auto_start_enabled",
    "ensure_docker_gateway",
    "gateway_is_healthy",
    "is_local_gateway_url",
    "port_is_open",
]
