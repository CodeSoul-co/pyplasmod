# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch

import pytest

from pyplasmod import PlasmodClient


@pytest.mark.skipif(
    not __import__("pyplasmod.embedded", fromlist=["EmbeddedWarmStore"]).EmbeddedWarmStore.is_available(),
    reason="libplasmod_retrieval not built on this host",
)
def test_plasmod_client_embedded_vectors(tmp_path):
    db_root = tmp_path / "plasmod_demo.db"
    with patch("pyplasmod.client.ensure_docker_gateway"), patch(
        "pyplasmod.client.find_plasmod_server_binary", return_value=None
    ), patch("pyplasmod.client.gateway_is_healthy", return_value=False):
        client = PlasmodClient(str(db_root), auto_start=False, embedded=True)
    assert client.embedded_mode == "vectors"
    client.create_collection("demo", dimension=4)
    client.insert("demo", data=[{"id": "1", "vector": [0.1, 0.2, 0.3, 0.4]}])
    res = client.search("demo", data=[0.1, 0.2, 0.3, 0.4], limit=3)
    assert res.get("objects")
    client.close()


def test_plasmod_client_prefers_embedded_vectors_over_healthy_gateway(tmp_path):
    db_root = tmp_path / "plasmod_demo.db"
    mock_store = MagicMock()
    mock_store.insert.return_value = {"status": "ok", "embedded": True}
    mock_store.search.return_value = {"status": "ok", "objects": ["1"], "embedded": True}
    with patch("pyplasmod.client.create_warm_store", return_value=(mock_store, "vectors")), patch(
        "pyplasmod.client.ensure_docker_gateway"
    ) as docker_boot, patch("pyplasmod.client.find_plasmod_server_binary", return_value=None), patch(
        "pyplasmod.client.gateway_is_healthy", return_value=True
    ):
        client = PlasmodClient(str(db_root), auto_start=True, embedded=True)
    assert client.embedded_mode == "vectors"
    docker_boot.assert_not_called()
    client.close()


def test_plasmod_client_prefers_embedded_vectors_over_docker(tmp_path):
    db_root = tmp_path / "plasmod_demo.db"
    mock_store = MagicMock()
    mock_store.insert.return_value = {"status": "ok", "embedded": True}
    mock_store.search.return_value = {"status": "ok", "objects": ["1"], "embedded": True}
    with patch("pyplasmod.client.create_warm_store", return_value=(mock_store, "vectors")), patch(
        "pyplasmod.client.ensure_docker_gateway"
    ) as docker_boot, patch("pyplasmod.client.find_plasmod_server_binary", return_value=None), patch(
        "pyplasmod.client.gateway_is_healthy", return_value=False
    ):
        client = PlasmodClient(str(db_root), auto_start=True, embedded=True)
    assert client.embedded_mode == "vectors"
    client.create_collection("demo", dimension=4)
    client.insert("demo", data=[{"id": "1", "vector": [0.0, 0.0, 0.0, 0.0]}])
    client.search("demo", data=[0.0, 0.0, 0.0, 0.0], limit=1)
    docker_boot.assert_not_called()
    mock_store.insert.assert_called_once()
    mock_store.search.assert_called_once()
    client.close()
