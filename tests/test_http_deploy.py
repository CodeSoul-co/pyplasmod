# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch

from pyplasmod.http.deploy import healthz_urls, resolve_mgmt_base_url


def test_healthz_urls_split_api_port():
    urls = healthz_urls("http://127.0.0.1:19530")
    assert urls == [
        "http://127.0.0.1:9091/healthz",
        "http://127.0.0.1:19530/healthz",
    ]


def test_healthz_urls_unified_8080():
    urls = healthz_urls("http://127.0.0.1:8080")
    assert urls == ["http://127.0.0.1:8080/healthz"]


def test_resolve_mgmt_base_url_split():
    mock_resp = MagicMock(ok=True)
    with patch("pyplasmod.http.deploy.requests.get", return_value=mock_resp):
        assert resolve_mgmt_base_url("http://127.0.0.1:19530") == "http://127.0.0.1:9091"


def test_resolve_mgmt_base_url_unified_on_19530():
    import requests as req_lib

    with patch(
        "pyplasmod.http.deploy.requests.get",
        side_effect=req_lib.RequestException("refused"),
    ):
        assert resolve_mgmt_base_url("http://127.0.0.1:19530") is None
