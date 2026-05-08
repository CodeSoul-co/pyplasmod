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
import struct
from unittest.mock import MagicMock, patch

import pytest
from pyplasmod import (
    PlasmodClient,
    PlasmodHttpClient,
    PlasmodHttpError,
    decode_query_warm_batch_response,
    decode_query_warm_response,
    encode_ingest_batch,
    encode_query_warm,
    encode_query_warm_batch,
)


def test_plasmod_client_alias():
    assert PlasmodClient is PlasmodHttpClient


def test_encode_ingest_batch_magic_and_roundtrip_ids():
    buf = encode_ingest_batch("seg.a", [[0.0, 1.0], [2.0, 3.0]], ["x", "y"])
    assert buf[:4] == b"PLIB"
    assert buf[4] == 1


def test_encode_ingest_batch_wire_version_2():
    buf = encode_ingest_batch("s", [[1.0]], wire_version=2)
    assert buf[4] == 2


def test_encode_query_warm_prefix():
    buf = encode_query_warm("warm.default", 10, [0.25] * 128)
    assert buf[:4] == b"PLQW"
    assert buf[4] == 1


def test_encode_query_warm_batch_prefix():
    buf = encode_query_warm_batch("seg", 5, [[1.0, 0.0], [0.0, 1.0]])
    assert buf[:4] == b"PLQB"


def test_decode_query_warm_response_roundtrip_manual():
    parts = bytearray()
    parts += struct.pack("<I", 2)
    for s in (b"id_a", b"id_b"):
        parts += struct.pack("<H", len(s))
        parts += s
    assert decode_query_warm_response(bytes(parts)) == ["id_a", "id_b"]


def test_decode_query_warm_batch_response_manual():
    nq, topk = 2, 3
    count = nq * topk
    buf = bytearray()
    buf += struct.pack("<II", nq, topk)
    for i in range(count):
        buf += struct.pack("<q", i)
    for i in range(count):
        buf += struct.pack("<f", float(i) * 0.1)
    nn, tk, ids, dists = decode_query_warm_batch_response(bytes(buf))
    assert nn == nq and tk == topk
    assert ids == list(range(count))
    assert len(dists) == count


def _ok_json_response(data):
    r = MagicMock()
    r.ok = True
    r.status_code = 200
    r.text = json.dumps(data)
    r.headers = {"Content-Type": "application/json"}
    r.json.return_value = data
    return r


def test_http_client_health():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    with patch.object(client._session, "request", return_value=_ok_json_response({"status": "ok"})):
        assert client.health() == {"status": "ok"}
        client._session.request.assert_called_once()
        args, kwargs = client._session.request.call_args
        assert args[1].endswith("/healthz")


def test_http_client_admin_key_on_admin_route():
    client = PlasmodHttpClient(base_url="http://example.invalid", admin_key="k")
    with patch.object(client._session, "request", return_value=_ok_json_response({})):
        client.warm_prebuild()
        _, kwargs = client._session.request.call_args
        assert kwargs["headers"]["X-Admin-Key"] == "k"


def test_http_client_query_body():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    body = {"query_text": "hi", "top_k": 3}
    with patch.object(client._session, "request", return_value=_ok_json_response({"objects": []})):
        client.query(body)
        _, kwargs = client._session.request.call_args
        assert kwargs["json"] == body


def test_system_mode_uses_get():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    with patch.object(
        client._session, "request", return_value=_ok_json_response({"app_mode": "x"})
    ):
        client.system_mode()
        args, kwargs = client._session.request.call_args
        assert args[0] == "GET"
        assert args[1].endswith("/v1/system/mode")


def test_ingest_document_posts_json():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    body = {"text": "hello", "agent_id": "a", "session_id": "s", "workspace_id": "w"}
    with patch.object(client._session, "request", return_value=_ok_json_response({"status": "ok"})):
        client.ingest_document(body)
        _, kwargs = client._session.request.call_args
        assert kwargs["json"] == body


def test_agents_get_with_params():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    with patch.object(client._session, "request", return_value=_ok_json_response([])):
        client.agents_get(params={"limit": "10"})
        _, kwargs = client._session.request.call_args
        assert kwargs["params"] == {"limit": "10"}


def test_rpc_query_warm_batch_raw_uses_raw_path():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    plqb = encode_query_warm_batch("seg", 2, [[0.0, 1.0], [1.0, 0.0]])
    nq, topk = 2, 2
    count = nq * topk
    raw_resp = bytearray()
    raw_resp += struct.pack("<II", nq, topk)
    for i in range(count):
        raw_resp += struct.pack("<q", i)
    for i in range(count):
        raw_resp += struct.pack("<f", float(i))
    with patch.object(client, "request_bytes", return_value=(200, bytes(raw_resp), {})) as m:
        client.rpc_query_warm_batch_raw("seg", 2, [[0.0, 1.0], [1.0, 0.0]])
        m.assert_called_once()
        args, kwargs = m.call_args
        assert args[0] == "POST"
        assert args[1] == "/v1/internal/rpc/query_warm_batch_raw"
        assert kwargs["data"] == plqb


def test_http_client_raises_on_error_status():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    r = MagicMock()
    r.ok = False
    r.status_code = 400
    r.reason = "Bad Request"
    r.text = "bad"
    r.headers = {}
    with patch.object(client._session, "request", return_value=r):
        with pytest.raises(PlasmodHttpError) as ei:
            client.health()
        assert ei.value.status_code == 400
        assert "bad" in ei.value.body
