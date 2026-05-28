# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pyplasmod.exceptions import ConnectError
from pyplasmod.runtime.docker_bootstrap import (
    DEFAULT_DOCKER_IMAGE,
    auto_start_enabled,
    ensure_docker_gateway,
    gateway_is_healthy,
    is_local_gateway_url,
    port_is_open,
)


def test_is_local_gateway_url():
    assert is_local_gateway_url("http://127.0.0.1:19530")
    assert is_local_gateway_url("http://localhost:19530")
    assert not is_local_gateway_url("https://plasmod.example:19530")
    assert not is_local_gateway_url("http://127.0.0.1:8080")


def test_auto_start_env(monkeypatch):
    monkeypatch.delenv("PLASMOD_AUTO_START", raising=False)
    assert auto_start_enabled(None) is True
    monkeypatch.setenv("PLASMOD_AUTO_START", "0")
    assert auto_start_enabled(None) is False
    assert auto_start_enabled(True) is True


def test_ensure_docker_gateway_already_healthy():
    with patch(
        "pyplasmod.runtime.docker_bootstrap.gateway_is_healthy",
        return_value=True,
    ) as health:
        ensure_docker_gateway("http://127.0.0.1:19530")
    health.assert_called()


def test_ensure_docker_gateway_pull_and_run():
    with patch(
        "pyplasmod.runtime.docker_bootstrap.gateway_is_healthy",
        side_effect=[False, False, True],
    ), patch(
        "pyplasmod.runtime.docker_bootstrap.port_is_open",
        return_value=False,
    ), patch(
        "pyplasmod.runtime.docker_bootstrap._docker_container_state",
        return_value=None,
    ), patch(
        "pyplasmod.runtime.docker_bootstrap._docker_image_present",
        return_value=False,
    ), patch(
        "pyplasmod.runtime.docker_bootstrap._docker_pull",
    ) as pull, patch(
        "pyplasmod.runtime.docker_bootstrap._docker_run_container",
    ) as run:
        ensure_docker_gateway("http://127.0.0.1:19530", image=DEFAULT_DOCKER_IMAGE)
    pull.assert_called_once()
    run.assert_called_once()


def test_ensure_docker_gateway_starts_existing_container():
    with patch(
        "pyplasmod.runtime.docker_bootstrap.gateway_is_healthy",
        side_effect=[False, True],
    ), patch(
        "pyplasmod.runtime.docker_bootstrap.port_is_open",
        return_value=False,
    ), patch(
        "pyplasmod.runtime.docker_bootstrap._docker_container_state",
        return_value="Exited (0) 1 hour ago",
    ), patch(
        "pyplasmod.runtime.docker_bootstrap._docker_start_container",
    ) as start, patch(
        "pyplasmod.runtime.docker_bootstrap._docker_run_container",
    ) as run:
        ensure_docker_gateway("http://127.0.0.1:19530")
    start.assert_called_once()
    run.assert_not_called()


def test_ensure_docker_gateway_port_conflict():
    with patch(
        "pyplasmod.runtime.docker_bootstrap.gateway_is_healthy",
        return_value=False,
    ), patch(
        "pyplasmod.runtime.docker_bootstrap.port_is_open",
        return_value=True,
    ):
        with pytest.raises(ConnectError, match="Port 19530"):
            ensure_docker_gateway("http://127.0.0.1:19530")


def test_plasmod_client_auto_start_invokes_ensure():
    with patch("pyplasmod.client.ensure_docker_gateway") as ensure, patch(
        "pyplasmod.client.PlasmodHttpClient",
    ) as http_cls:
        http_cls.return_value = MagicMock(base_url="http://127.0.0.1:19530")
        from pyplasmod import PlasmodClient

        c = PlasmodClient(auto_start=True)
        ensure.assert_called_once()
        c.close()


def test_plasmod_client_auto_start_disabled():
    with patch("pyplasmod.client.ensure_docker_gateway") as ensure, patch(
        "pyplasmod.client.PlasmodHttpClient",
    ) as http_cls:
        http_cls.return_value = MagicMock(base_url="http://127.0.0.1:19530")
        from pyplasmod import PlasmodClient

        c = PlasmodClient(auto_start=False)
        ensure.assert_not_called()
        c.close()


def test_gateway_is_healthy_uses_mgmt_port():
    mock_resp = MagicMock(ok=True)
    with patch("pyplasmod.runtime.docker_bootstrap.requests.get", return_value=mock_resp) as get:
        assert gateway_is_healthy("http://127.0.0.1:19530") is True
    assert get.call_args[0][0] == "http://127.0.0.1:9091/healthz"


def test_port_is_open_localhost():
    assert port_is_open("127.0.0.1", 1) is False  # unlikely to have a listener on port 1
