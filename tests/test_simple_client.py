# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

from unittest.mock import patch

from pyplasmod import PlasmodClient


def test_plasmod_client_simple_fallback(tmp_path):
    db_root = tmp_path / "plasmod_demo.db"
    with patch("pyplasmod.embedded.factory.EmbeddedWarmStore.is_available", return_value=False), patch(
        "pyplasmod.embedded.factory.FaissWarmStore.is_available", return_value=False
    ), patch("pyplasmod.embedded.factory.HnswlibWarmStore.is_available", return_value=False):
        client = PlasmodClient(str(db_root), auto_start=False, embedded=True)
    assert client.embedded_mode == "simple"
    client.create_collection("demo", dimension=4)
    client.insert("demo", data=[{"id": "1", "vector": [0.1, 0.2, 0.3, 0.4]}])
    res = client.search("demo", data=[0.1, 0.2, 0.3, 0.4], limit=3)
    assert res[0][0]["id"] == 1
    client.close()
