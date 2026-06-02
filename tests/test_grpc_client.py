# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

import json
from unittest.mock import MagicMock

import pytest

from pyplasmod.grpc.client import PlasmodGrpcClient
from pyplasmod.grpc.deploy import resolve_grpc_target
from pyplasmod.grpc.pb.plasmod.v1 import plasmod_pb2


def test_resolve_grpc_target_from_http():
    assert resolve_grpc_target(http_base_url="http://127.0.0.1:19530") == "127.0.0.1:19531"
    assert resolve_grpc_target(http_base_url="http://127.0.0.1:8080") == "127.0.0.1:19531"


def test_resolve_grpc_target_explicit():
    assert resolve_grpc_target("grpc://remote.example:20000") == "remote.example:20000"
    assert resolve_grpc_target("remote.example") == "remote.example:19531"


def test_grpc_client_health(monkeypatch):
    stub = MagicMock()
    stub.Health.return_value = plasmod_pb2.HealthResponse(status="ok", transport="grpc")
    client = PlasmodGrpcClient("127.0.0.1:19531", channel=MagicMock())
    client._stub = stub
    assert client.health() == {"status": "ok", "transport": "grpc"}
    stub.Health.assert_called_once()


def test_grpc_client_ingest_vectors(monkeypatch):
    stub = MagicMock()
    stub.IngestVectors.return_value = plasmod_pb2.IngestVectorsResponse(
        status="ok",
        segment_id="warm.demo",
        ingested=2,
        vector_dim=3,
        index_type="HNSW",
        direct_warm=True,
    )
    client = PlasmodGrpcClient("127.0.0.1:19531", channel=MagicMock())
    client._stub = stub
    out = client.ingest_vectors([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]], segment_id="warm.demo")
    assert out["ingested"] == 2
    assert out["segment_id"] == "warm.demo"
    req = stub.IngestVectors.call_args[0][0]
    assert req.segment_id == "warm.demo"
    assert len(req.vectors) == 2


def test_grpc_client_query_json():
    stub = MagicMock()
    stub.Query.return_value = plasmod_pb2.QueryResponse(
        result_json=json.dumps({"status": "ok", "objects": ["a"]}),
    )
    client = PlasmodGrpcClient("127.0.0.1:19531", channel=MagicMock())
    client._stub = stub
    out = client.query({"query_text": "hello", "workspace_id": "ws"})
    assert out == {"status": "ok", "objects": ["a"]}
    req = stub.Query.call_args[0][0]
    body = json.loads(req.query_json)
    assert body["query_text"] == "hello"


def test_grpc_client_query_batch():
    stub = MagicMock()
    stub.QueryBatch.return_value = plasmod_pb2.QueryBatchResponse(
        status="ok",
        agent_mode="single_agent",
        warm_segment_id="warm.demo",
        source_ids=["s0"],
        rows=[
            plasmod_pb2.QueryBatchRow(
                row_index=0,
                object_ids=["id0"],
                distances=[0.1],
                source_refs=[0],
            )
        ],
        by_source={"s0": plasmod_pb2.StringList(values=["id0"])},
    )
    client = PlasmodGrpcClient("127.0.0.1:19531", channel=MagicMock())
    client._stub = stub
    out = client.query_batch(
        {
            "warm_segment_id": "warm.demo",
            "vectors": [[0.0, 1.0]],
            "top_k": 5,
            "agent_mode": "single_agent",
        }
    )
    assert out["status"] == "ok"
    assert out["rows"][0]["object_ids"] == ["id0"]
    assert out["by_source"]["s0"] == ["id0"]


def test_grpc_import_error_message(monkeypatch):
    import pyplasmod.grpc.client as grpc_client_mod

    monkeypatch.setattr(grpc_client_mod, "grpc", None)
    monkeypatch.setattr(grpc_client_mod, "_GRPC_IMPORT_ERROR", ImportError("no grpc"))
    with pytest.raises(ImportError, match="pyplasmod\\[grpc\\]"):
        PlasmodGrpcClient("127.0.0.1:19531", channel=object())
