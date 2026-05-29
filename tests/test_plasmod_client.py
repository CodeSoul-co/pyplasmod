# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from pyplasmod import (
    DEFAULT_API_URI,
    DEFAULT_DOCKER_IMAGE,
    PlasmodClient,
    PlasmodHttpClient,
)


def test_plasmod_client_is_high_level_entry():
    assert PlasmodClient is not PlasmodHttpClient
    assert issubclass(PlasmodClient, object)


def test_plasmod_client_default_uri():
    with patch("pyplasmod.client.ensure_docker_gateway"), patch(
        "pyplasmod.client.resolve_mgmt_base_url",
        return_value="http://127.0.0.1:9091",
    ):
        c = PlasmodClient(auto_start=False)
    assert c.http.base_url == DEFAULT_API_URI.rstrip("/")
    assert c._mgmt_base_url == "http://127.0.0.1:9091"
    c.close()


def test_plasmod_client_unified_on_19530_mgmt_is_none():
    with patch("pyplasmod.client.ensure_docker_gateway"), patch(
        "pyplasmod.http.client.resolve_mgmt_base_url",
        return_value=None,
    ):
        c = PlasmodClient(uri="http://127.0.0.1:19530", auto_start=False)
    assert c._mgmt_base_url is None
    c.close()


def test_plasmod_client_remote_uri():
    c = PlasmodClient(uri="https://plasmod.example:19530")
    assert c.http.base_url == "https://plasmod.example:19530"
    c.close()


def test_plasmod_client_base_url_backward_compat():
    c = PlasmodClient(base_url="http://127.0.0.1:8080")
    assert c.http.base_url == "http://127.0.0.1:8080"
    assert c._mgmt_base_url is None
    c.close()


def test_plasmod_client_profile_file(tmp_path: Path):
    db = tmp_path / "plasmod_demo.db"
    with patch("pyplasmod.client.ensure_docker_gateway"):
        c = PlasmodClient(str(db), auto_start=False)
    assert db.is_file()
    profile = json.loads(db.read_text(encoding="utf-8"))
    assert profile["uri"] == DEFAULT_API_URI
    c.create_collection("demo_collection", dimension=4)
    c.close()
    profile2 = json.loads(db.read_text(encoding="utf-8"))
    assert "demo_collection" in profile2["collections"]


def test_plasmod_client_create_insert_search():
    c = PlasmodClient(uri="http://example.invalid")
    c.create_collection("demo_collection", dimension=2)
    ok = {"status": "ok"}

    with patch.object(c.http._session, "request", return_value=_json_resp(ok)) as m:
        assert c.insert("demo_collection", [[0.0, 1.0], [2.0, 3.0]]) == ok
        _, kwargs = m.call_args
        body = kwargs["json"]
        assert body["segment_id"] == "warm.demo_collection"
        assert len(body["vectors"]) == 2

    with patch.object(c.http._session, "request", return_value=_json_resp({"objects": []})) as m:
        assert c.search("demo_collection", "hello", limit=3) == {"objects": []}
        _, kwargs = m.call_args
        assert kwargs["json"]["query_text"] == "hello"
        assert kwargs["json"]["workspace_id"] == "demo_collection"
        assert kwargs["json"]["top_k"] == 3
    c.close()


def test_docker_run_hint():
    hint = PlasmodClient.docker_run_hint()
    assert DEFAULT_DOCKER_IMAGE in hint
    assert "9091:9091" in hint
    assert "19530:19530" in hint


def _json_resp(data):
    r = MagicMock()
    r.ok = True
    r.status_code = 200
    r.text = json.dumps(data)
    r.headers = {"Content-Type": "application/json"}
    r.json.return_value = data
    return r
