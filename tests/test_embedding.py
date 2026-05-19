# Copyright (C) 2019-2021 Zilliz. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from pyplasmod.data import build_query_body
from pyplasmod import PlasmodEmbedding, open_embedding
from pyplasmod.embedding import (
    EmbedderConfig,
    GatewayEmbedding,
    format_capability_table,
    parse_embedding_provenance,
    parse_query_response_embedding,
)
from pyplasmod.easy import EasyPlasmod
from pyplasmod.http.client import PlasmodHttpClient


def test_embedder_config_onnx_cpu_cuda_presets():
    cpu = EmbedderConfig.onnx_cpu(model_path="/m.onnx", dim=384)
    assert cpu.provider == "onnx"
    assert cpu.device == "cpu"
    assert cpu.supports_local_device_choice()

    cuda = EmbedderConfig.onnx_cuda(model_path="/m.onnx", dim=384)
    assert cuda.device == "cuda"
    env = cuda.to_environ()
    assert env["PLASMOD_EMBEDDER"] == "onnx"
    assert env["PLASMOD_EMBEDDER_DEVICE"] == "cuda"
    assert env["PLASMOD_EMBEDDER_DIM"] == "384"


def test_tensorrt_requires_cuda():
    cfg = EmbedderConfig.tensorrt_cuda(engine_path="/e.trt", dim=384)
    assert cfg.is_gpu_only_provider()
    with pytest.raises(ValueError):
        EmbedderConfig(provider="tensorrt", device="cpu").validate_device()


def test_embedder_config_roundtrip_environ(monkeypatch):
    monkeypatch.setenv("PLASMOD_EMBEDDER", "gguf")
    monkeypatch.setenv("PLASMOD_EMBEDDER_DEVICE", "cuda")
    monkeypatch.setenv("PLASMOD_EMBEDDER_DIM", "768")
    monkeypatch.setenv("PLASMOD_EMBEDDER_MODEL_PATH", "/x.gguf")
    cfg = EmbedderConfig.from_environ()
    assert cfg.provider == "gguf"
    assert cfg.device == "cuda"
    assert cfg.dim == 768
    assert cfg.model_path == "/x.gguf"


def test_apply_to_environ(monkeypatch):
    for key in list(os.environ):
        if key.startswith("PLASMOD_EMBEDDER"):
            monkeypatch.delenv(key, raising=False)
    cfg = EmbedderConfig.onnx_cpu(model_path="/m.onnx", dim=128)
    applied = cfg.apply_to_environ()
    assert os.environ["PLASMOD_EMBEDDER"] == "onnx"
    assert applied["PLASMOD_EMBEDDER_DEVICE"] == "cpu"


def test_parse_embedding_provenance():
    prov = [
        "embedding_runtime_family=onnx:minilm",
        "embedding_runtime_dim=384",
        "cross_dim_fusion=rrf_result_layer",
    ]
    info = parse_embedding_provenance(prov)
    assert info.family == "onnx:minilm"
    assert info.provider == "onnx"
    assert info.dim == 384
    assert info.cross_dim_fusion is True


def test_parse_query_response_embedding():
    resp = {"provenance": ["embedding_runtime_family=tfidf", "embedding_runtime_dim=256"]}
    info = parse_query_response_embedding(resp)
    assert info.family == "tfidf"
    assert info.dim == 256


def test_build_query_body_embedding_vector():
    body = build_query_body("q", "w1", embedding_vector=[0.1, 0.2])
    assert body["embedding_vector"] == [0.1, 0.2]


def test_format_capability_table_includes_onnx():
    table = format_capability_table()
    assert "onnx" in table
    assert "cuda" in table


def _ok_json(data):
    r = MagicMock()
    r.ok = True
    r.status_code = 200
    r.text = json.dumps(data)
    r.headers = {"Content-Type": "application/json"}
    r.json.return_value = data
    return r


def test_fetch_embedding_runtime_via_client():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    prov_resp = {
        "provenance": [
            "embedding_runtime_family=tfidf",
            "embedding_runtime_dim=256",
        ],
        "objects": [],
    }
    with patch.object(client._session, "request", return_value=_ok_json(prov_resp)):
        info = client.fetch_embedding_runtime(workspace_id="w1")
    assert info.family == "tfidf"
    assert info.dim == 256


def test_gateway_embedding_search_builds_query():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    gw = GatewayEmbedding(client)
    body = gw.build_query("hello", "w1", top_k=5)
    assert body["query_text"] == "hello"
    assert body["workspace_id"] == "w1"
    assert body["top_k"] == 5
    assert "embedding_vector" not in body


def test_gateway_ingest_text_event_includes_required_fields():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    gw = GatewayEmbedding(client)
    with patch.object(client, "ingest_event", return_value={"ok": True}) as mock_ingest:
        gw.ingest_text_event("hello", "w_demo")
    event = mock_ingest.call_args[0][0]
    assert event["event_type"] == "observation"
    assert event["workspace_id"] == "w_demo"
    assert event["payload"]["text"] == "hello"
    assert event["event_id"]
    assert event["event_time"]
    assert event["ingest_time"]
    assert event["visible_time"]
    assert event["source"] == "pyplasmod.embedding"
    assert event["version"] == 1


def test_plasmod_embedding_use_cpu_gpu():
    emb = PlasmodEmbedding.connect(base_url="http://example.invalid")
    cpu = emb.use_cpu("onnx", model_path="/m.onnx", dim=384)
    assert cpu.device == "cpu"
    gpu = emb.use_gpu("onnx", model_path="/m.onnx", dim=384)
    assert gpu.device == "cuda"
    emb.close()


def test_open_embedding_alias():
    emb = open_embedding(base_url="http://example.invalid")
    assert isinstance(emb, PlasmodEmbedding)
    emb.close()


def test_easy_plasmod_embedding_property():
    e = EasyPlasmod(base_url="http://example.invalid")
    assert e.embedding.client is e.http
    assert e.gateway_embedding() is e.embedding
    body = e.embedding.build_query("q", "w1")
    assert body["query_text"] == "q"
