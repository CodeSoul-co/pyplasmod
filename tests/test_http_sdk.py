# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

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


def test_plasmod_http_client_distinct_from_high_level_client():
    assert PlasmodClient is not PlasmodHttpClient


def test_encode_ingest_batch_magic_and_roundtrip_ids():
    buf = encode_ingest_batch("seg.a", [[0.0, 1.0], [2.0, 3.0]], ["x", "y"])
    assert buf[:4] == b"PLIB"
    assert buf[4] == 1


def test_encode_ingest_batch_wire_version_2():
    buf = encode_ingest_batch("s", [[1.0]], wire_version=2)
    assert buf[4] == 2


def test_normalize_warm_index_type():
    from pyplasmod.http.warm_index import (
        WARM_INDEX_HNSW,
        normalize_warm_index_type,
    )

    assert normalize_warm_index_type("") == WARM_INDEX_HNSW
    assert normalize_warm_index_type("ivf_flat") == "IVF_FLAT"
    with pytest.raises(ValueError):
        normalize_warm_index_type("FOO")


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


def test_plasmod_http_client_base_url_from_env(monkeypatch):
    monkeypatch.setenv("PLASMOD_BASE_URL", "http://plasmod.env.test:9999")
    c = PlasmodHttpClient()
    assert c.base_url == "http://plasmod.env.test:9999"


def test_plasmod_http_client_base_url_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("PLASMOD_BASE_URL", "http://wrong:1")
    c = PlasmodHttpClient(base_url="http://explicit:2")
    assert c.base_url == "http://explicit:2"


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


def test_ingest_vectors_index_type_json():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    with patch.object(client._session, "request", return_value=_ok_json_response({"index_type": "IVF_FLAT"})) as m:
        client.ingest_vectors(
            [[1.0, 0.0]],
            segment_id="demo.ivf",
            index_type="IVF_FLAT",
            ivf_nlist=128,
            ivf_nprobe=32,
        )
        body = m.call_args[1]["json"]
        assert body["index_type"] == "IVF_FLAT"
        assert body["ivf_nlist"] == 128
        assert body["ivf_nprobe"] == 32


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


def test_traces_get_encodes_object_id_in_path():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    with patch.object(
        client._session, "request", return_value=_ok_json_response({"object_id": "mem/x"})
    ):
        client.traces_get("mem/x")
        args, kwargs = client._session.request.call_args
        assert args[0] == "GET"
        assert args[1].endswith("/v1/traces/mem%2Fx")


def test_internal_memory_recall_posts_json():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    body = {"query": "q", "scope": "w", "top_k": 3}
    with patch.object(client._session, "request", return_value=_ok_json_response({})):
        client.internal_memory_recall(body)
        args, kwargs = client._session.request.call_args
        assert args[0] == "POST"
        assert args[1].endswith("/v1/internal/memory/recall")
        assert kwargs["json"] == body


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


def test_admin_topology_get_uses_get_and_admin_path():
    client = PlasmodHttpClient(base_url="http://example.invalid", admin_key="k")
    with patch.object(client._session, "request", return_value=_ok_json_response({})):
        client.admin_topology_get()
        args, kwargs = client._session.request.call_args
        assert args[0] == "GET"
        assert args[1].endswith("/v1/admin/topology")
        assert kwargs["headers"]["X-Admin-Key"] == "k"


def test_internal_task_start_posts_json():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    body = {"session_id": "s", "task_type": "t", "goal": "g"}
    with patch.object(client._session, "request", return_value=_ok_json_response({"status": "ok"})):
        client.internal_task_start(body)
        args, kwargs = client._session.request.call_args
        assert args[0] == "POST"
        assert args[1].endswith("/v1/internal/task/start")
        assert kwargs["json"] == body


def test_internal_tool_state_get_passes_query_params():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    with patch.object(client._session, "request", return_value=_ok_json_response({"pending": []})):
        client.internal_tool_state_get({"agent_id": "a", "session_id": "s"})
        _, kwargs = client._session.request.call_args
        assert kwargs["params"] == {"agent_id": "a", "session_id": "s"}


def test_internal_tool_state_get_allows_no_params():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    with patch.object(client._session, "request", return_value=_ok_json_response({})):
        client.internal_tool_state_get()
        _, kwargs = client._session.request.call_args
        assert kwargs["params"] is None


def test_internal_eval_ground_truth_get_optional_params():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    with patch.object(client._session, "request", return_value=_ok_json_response([])):
        client.internal_eval_ground_truth_get()
        _, kwargs = client._session.request.call_args
        assert kwargs["params"] is None


def test_tier_b_admin_get_routes_paths_and_method():
    """Every Tier B admin GET helper hits the expected path (mocked HTTP)."""
    client = PlasmodHttpClient(base_url="http://example.invalid", admin_key="k")
    getters = [
        ("admin_topology_get", "/v1/admin/topology"),
        ("admin_storage_get", "/v1/admin/storage"),
        ("admin_config_effective_get", "/v1/admin/config/effective"),
        ("admin_consistency_mode_get", "/v1/admin/consistency-mode"),
        ("admin_metrics_get", "/v1/admin/metrics"),
        ("admin_governance_mode_get", "/v1/admin/governance-mode"),
        ("admin_runtime_mode_get", "/v1/admin/runtime-mode"),
        ("admin_algorithm_profile_mode_get", "/v1/admin/memory/providers/mode"),
        ("admin_algorithm_profile_health_get", "/v1/admin/memory/providers/health"),
    ]
    for method_name, path_suffix in getters:
        with patch.object(client._session, "request", return_value=_ok_json_response({})) as m:
            getattr(client, method_name)()
            args, kwargs = m.call_args
            assert args[0] == "GET", method_name
            assert args[1].endswith(path_suffix), method_name
            assert kwargs["headers"].get("X-Admin-Key") == "k"


def test_tier_b_admin_metrics_get_with_storage_param():
    client = PlasmodHttpClient(base_url="http://example.invalid", admin_key="k")
    with patch.object(client._session, "request", return_value=_ok_json_response({})):
        client.admin_metrics_get(params={"storage": "true"})
        _, kwargs = client._session.request.call_args
        assert kwargs["params"] == {"storage": "true"}


def test_tier_b_internal_post_routes_paths():
    """Tier B internal POST helpers use POST + expected path suffix."""
    client = PlasmodHttpClient(base_url="http://example.invalid")
    calls: list[tuple[str, object]] = [
        ("internal_task_start", {"session_id": "s", "task_type": "t", "goal": "g"}),
        ("internal_task_complete", {"session_id": "s", "success": True, "duration_ms": 0.0}),
        ("internal_task_tokens", {"session_id": "s", "tokens": 1}),
        ("internal_task_claim", {"session_id": "s"}),
        (
            "internal_task_stage",
            {
                "session_id": "s",
                "agent_id": "a",
                "stage": "outline",
                "stage_index": 0,
                "total_stages": 1,
                "description": "",
            },
        ),
        ("internal_plan_step", {"session_id": "s", "step_description": "", "step_index": 0}),
        ("internal_plan_repair", {"session_id": "s", "success": True}),
        ("internal_mas_answer_consistency", {"score": 0.5, "session_id": "s"}),
        (
            "internal_mas_aggregate",
            {
                "requester_agent_id": "a",
                "source_agent_ids": [],
                "query": "q",
                "top_k": 1,
            },
        ),
        ("internal_agent_handoff", {"from_agent_id": "a", "to_agent_id": "b"}),
        ("internal_eval_ground_truth_post", {"task_id": "t", "expected": "e"}),
        ("debug_echo", {"ping": 1}),
    ]
    for method_name, body in calls:
        path = {
            "internal_task_start": "/v1/internal/task/start",
            "internal_task_complete": "/v1/internal/task/complete",
            "internal_task_tokens": "/v1/internal/task/tokens",
            "internal_task_claim": "/v1/internal/task/claim",
            "internal_task_stage": "/v1/internal/task/stage",
            "internal_plan_step": "/v1/internal/plan/step",
            "internal_plan_repair": "/v1/internal/plan/repair",
            "internal_mas_answer_consistency": "/v1/internal/mas/answer-consistency",
            "internal_mas_aggregate": "/v1/internal/mas/aggregate",
            "internal_agent_handoff": "/v1/internal/agent/handoff",
            "internal_eval_ground_truth_post": "/v1/internal/eval/ground-truth",
            "debug_echo": "/v1/debug/echo",
        }[method_name]
        with patch.object(client._session, "request", return_value=_ok_json_response({})) as m:
            getattr(client, method_name)(body)
            args, kwargs = m.call_args
            assert args[0] == "POST", method_name
            assert args[1].endswith(path), method_name
            assert kwargs["json"] == body


def test_dataset_purge_and_admin_alias_post_same_path():
    client = PlasmodHttpClient(base_url="http://example.invalid", admin_key="k")
    body = {"workspace_id": "w", "dataset_name": "d", "dry_run": True}
    for method_name in ("dataset_purge", "admin_dataset_purge"):
        with patch.object(client._session, "request", return_value=_ok_json_response({})) as m:
            getattr(client, method_name)(body)
            args, kwargs = m.call_args
            assert args[0] == "POST"
            assert args[1].endswith("/v1/admin/dataset/purge")
            assert kwargs["json"] == body


def test_dataset_purge_task_and_admin_alias_get_same_path():
    client = PlasmodHttpClient(base_url="http://example.invalid", admin_key="k")
    for method_name in ("dataset_purge_task", "admin_dataset_purge_task"):
        with patch.object(client._session, "request", return_value=_ok_json_response({})) as m:
            getattr(client, method_name)("tid-1")
            args, kwargs = m.call_args
            assert args[0] == "GET"
            assert args[1].endswith("/v1/admin/dataset/purge/task")
            assert kwargs["params"] == {"task_id": "tid-1"}


def test_tier_b_admin_post_routes_paths():
    client = PlasmodHttpClient(base_url="http://example.invalid", admin_key="k")
    bodies = [
        ("admin_s3_cold_purge", "/v1/admin/s3/cold-purge", {"confirm": "purge_cold_tier", "dry_run": True}),
        ("admin_rollback", "/v1/admin/rollback", {"memory_id": "m", "action": "reactivate"}),
        ("admin_replay", "/v1/admin/replay", {"from_lsn": 0, "limit": 1}),
        ("admin_consistency_mode_post", "/v1/admin/consistency-mode", {"mode": "strict_visible"}),
        ("admin_governance_mode_post", "/v1/admin/governance-mode", {"enabled": True}),
        ("admin_runtime_mode_post", "/v1/admin/runtime-mode", {"vector_only_mode": False}),
        ("admin_algorithm_profile_mode_post", "/v1/admin/memory/providers/mode", {"mode": "default"}),
    ]
    for method_name, path, body in bodies:
        with patch.object(client._session, "request", return_value=_ok_json_response({})) as m:
            getattr(client, method_name)(body)
            args, kwargs = m.call_args
            assert args[0] == "POST"
            assert args[1].endswith(path)
            assert kwargs["json"] == body


def test_tier_b_admin_s3_export_posts_without_json_when_body_none():
    client = PlasmodHttpClient(base_url="http://example.invalid", admin_key="k")
    with patch.object(client._session, "request", return_value=_ok_json_response({})) as m:
        client.admin_s3_export(None)
        _, kwargs = m.call_args
        assert kwargs.get("json") is None
        assert m.call_args[0][1].endswith("/v1/admin/s3/export")


def test_tier_b_internal_session_context_and_eval_get():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    with patch.object(client._session, "request", return_value=_ok_json_response({})) as m:
        client.internal_session_context_get({"session_id": "s", "last_n": 5})
        assert m.call_args[0][0] == "GET"
        assert m.call_args[0][1].endswith("/v1/internal/session/context")
        assert m.call_args[1]["params"] == {"session_id": "s", "last_n": 5}
    with patch.object(client._session, "request", return_value=_ok_json_response([])) as m:
        client.internal_eval_ground_truth_get(params={"task_id": "t1"})
        assert m.call_args[1]["params"] == {"task_id": "t1"}
    with patch.object(client._session, "request", return_value=_ok_json_response([])) as m:
        client.agent_list_get(params={"role": "planner"})
        assert m.call_args[0][1].endswith("/v1/agent/list")
        assert m.call_args[1]["params"] == {"role": "planner"}


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


def test_query_batch_json():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    with patch.object(client._session, "request", return_value=_ok_json_response({"status": "ok"})) as m:
        out = client.query_batch(
            {
                "warm_segment_id": "warm.default",
                "agent_mode": "single_agent",
                "top_k": 2,
                "vectors": [[1, 2], [3, 4]],
            }
        )
        assert out == {"status": "ok"}
        assert m.call_args[0][0] == "POST"
        assert m.call_args[0][1].endswith("/v1/query/batch")
        body = m.call_args[1]["json"]
        assert body["vectors"] == [[1.0, 2.0], [3.0, 4.0]]


def test_admin_routes_use_mgmt_port_on_split_api_url():
    client = PlasmodHttpClient(base_url="http://127.0.0.1:19530")
    assert client._mgmt_base_url == "http://127.0.0.1:9091"
    assert client._url("/v1/admin/topology").startswith("http://127.0.0.1:9091/")
    assert client._url("/v1/query").startswith("http://127.0.0.1:19530/")


def test_admin_memory_delete_and_purge():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    with patch.object(client._session, "request", return_value=_ok_json_response({"deleted": 1})) as m:
        client.admin_memory_delete_by_source(
            {"workspace_id": "ws1", "event_id": "evt_x", "dry_run": True}
        )
        assert m.call_args[0][1].endswith("/v1/admin/memory/delete-by-source")
    with patch.object(client._session, "request", return_value=_ok_json_response({"purged": 0})) as m:
        client.admin_memory_purge_by_source(
            {"workspace_id": "ws1", "reference_id": "ref_y", "only_if_inactive": False}
        )
        assert m.call_args[0][1].endswith("/v1/admin/memory/purge-by-source")


def test_iter_wal_stream_events_sse_parse():
    from pyplasmod.http.client import _iter_wal_sse_json_events

    r = MagicMock()
    r.iter_lines.return_value = iter(
        [
            "event: wal",
            'data: {"lsn": 7, "event": {"k": 1}}',
            "",
            ": keep-alive",
            "",
        ]
    )
    events = list(_iter_wal_sse_json_events(r))
    assert len(events) == 1
    assert events[0]["lsn"] == 7
    assert events[0]["event"]["k"] == 1


def test_iter_wal_stream_events_http_error():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    r = MagicMock()
    r.ok = False
    r.status_code = 503
    r.text = "unavailable"
    r.reason = "Service Unavailable"
    r.headers = {}
    r.close = MagicMock()
    with patch.object(client._session, "get", return_value=r):
        gen = client.iter_wal_stream_events()
        with pytest.raises(PlasmodHttpError) as ei:
            next(gen)
        assert ei.value.status_code == 503
        r.close.assert_called()


def test_iter_wal_stream_events_get_params():
    client = PlasmodHttpClient(base_url="http://example.invalid")
    r = MagicMock()
    r.ok = True
    r.status_code = 200
    r.headers = {}
    r.iter_lines.return_value = iter([])
    r.close = MagicMock()
    with patch.object(client._session, "get", return_value=r) as m:
        list(client.iter_wal_stream_events(from_lsn=100, heartbeat="20s"))
    kwargs = m.call_args[1]
    assert kwargs["stream"] is True
    assert kwargs["params"] == {"from_lsn": "100", "heartbeat": "20s"}
    assert kwargs["headers"]["Accept"] == "text/event-stream"
    r.close.assert_called()
