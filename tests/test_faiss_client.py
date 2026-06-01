# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

from pyplasmod import PlasmodClient


def test_plasmod_client_faiss_embedded(tmp_path):
    db_root = tmp_path / "plasmod_demo.db"
    client = PlasmodClient(str(db_root), embedded=True)
    assert client.embedded_mode == "embedded"
    client.create_collection("demo", dimension=4, metric_type="COSINE")
    client.insert(
        "demo",
        data=[
            {"id": 1, "vector": [0.1, 0.2, 0.3, 0.4], "text": "doc_1"},
            {"id": 2, "vector": [0.2, 0.3, 0.4, 0.5], "text": "doc_2"},
        ],
    )
    res = client.search("demo", data=[[0.1, 0.2, 0.3, 0.4]], limit=2, output_fields=["text"])
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0][0]["id"] == 1
    assert "distance" in res[0][0]
    assert res[0][0]["entity"]["text"] == "doc_1"
    client.drop_collection("demo")
    assert not client.has_collection("demo")
    client.close()
