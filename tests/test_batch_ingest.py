# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Tests for batch ingestion methods in PlasmodHttpClient."""

from unittest.mock import MagicMock, patch, call

import pytest

from pyplasmod import PlasmodClient, BatchResult
from pyplasmod.exceptions import PlasmodException
from pyplasmod.http import PlasmodHttpError


class TestIngestBatch:
    """Tests for PlasmodHttpClient.ingest_batch method."""

    def test_empty_vectors(self):
        """Empty vectors should return empty BatchResult."""
        client = PlasmodClient(base_url="http://example.invalid")
        result = client.ingest_batch("seg", [])
        assert result.total_count == 0
        assert result.batch_count == 0
        assert result.success is True

    def test_small_batch_single_request(self):
        """Vectors smaller than batch_size should send single request."""
        client = PlasmodClient(base_url="http://example.invalid")
        vectors = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

        with patch.object(client, "rpc_ingest_batch", return_value={"ok": True}) as mock:
            result = client.ingest_batch("seg", vectors, batch_size=10)

            assert mock.call_count == 1
            assert result.total_count == 3
            assert result.accepted_count == 3
            assert result.failed_count == 0
            assert result.batch_count == 1
            assert result.success is True

    def test_large_batch_multiple_requests(self):
        """Vectors larger than batch_size should send multiple requests."""
        client = PlasmodClient(base_url="http://example.invalid")
        vectors = [[float(i)] for i in range(10)]

        with patch.object(client, "rpc_ingest_batch", return_value={"ok": True}) as mock:
            result = client.ingest_batch("seg", vectors, batch_size=3)

            # 10 vectors / 3 per batch = 4 batches (3+3+3+1)
            assert mock.call_count == 4
            assert result.total_count == 10
            assert result.accepted_count == 10
            assert result.batch_count == 4
            assert result.success is True

    def test_with_object_ids(self):
        """Object IDs should be split correctly across batches."""
        client = PlasmodClient(base_url="http://example.invalid")
        vectors = [[0.1], [0.2], [0.3], [0.4], [0.5]]
        object_ids = ["a", "b", "c", "d", "e"]

        calls = []

        def capture_call(seg_id, vecs, ids, **kwargs):
            calls.append({"segment_id": seg_id, "vectors": vecs, "ids": ids})
            return {"ok": True}

        with patch.object(client, "rpc_ingest_batch", side_effect=capture_call):
            result = client.ingest_batch("seg", vectors, object_ids, batch_size=2)

            assert len(calls) == 3
            assert calls[0]["ids"] == ["a", "b"]
            assert calls[1]["ids"] == ["c", "d"]
            assert calls[2]["ids"] == ["e"]
            assert result.accepted_count == 5

    def test_object_ids_length_mismatch(self):
        """Mismatched object_ids length should raise ValueError."""
        client = PlasmodClient(base_url="http://example.invalid")
        vectors = [[0.1], [0.2], [0.3]]
        object_ids = ["a", "b"]  # Wrong length

        with pytest.raises(ValueError, match="object_ids length must match"):
            client.ingest_batch("seg", vectors, object_ids)

    def test_batch_failure_raise_on_error_true(self):
        """With raise_on_error=True, should raise on first failure."""
        client = PlasmodClient(base_url="http://example.invalid")
        vectors = [[float(i)] for i in range(10)]

        call_count = [0]

        def fail_on_second(seg_id, vecs, ids, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise PlasmodHttpError(500, reason="Server error", body="", path="")
            return {"ok": True}

        with patch.object(client, "rpc_ingest_batch", side_effect=fail_on_second):
            with pytest.raises(PlasmodException, match="Batch 1 failed"):
                client.ingest_batch("seg", vectors, batch_size=3, raise_on_error=True)

    def test_batch_failure_raise_on_error_false(self):
        """With raise_on_error=False, should collect errors and continue."""
        client = PlasmodClient(base_url="http://example.invalid")
        vectors = [[float(i)] for i in range(10)]

        call_count = [0]

        def fail_on_second(seg_id, vecs, ids, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise PlasmodHttpError(500, reason="Server error", body="", path="")
            return {"ok": True}

        with patch.object(client, "rpc_ingest_batch", side_effect=fail_on_second):
            result = client.ingest_batch("seg", vectors, batch_size=3, raise_on_error=False)

            assert result.total_count == 10
            assert result.accepted_count == 7  # 3 + 3 + 1 (batch 2 failed with 3)
            assert result.failed_count == 3
            assert result.batch_count == 4
            assert len(result.errors) == 1
            assert result.errors[0]["batch_index"] == 1
            assert result.success is False

    def test_extracts_memory_ids_from_response(self):
        """Should extract memory_ids from response."""
        client = PlasmodClient(base_url="http://example.invalid")
        vectors = [[0.1], [0.2]]

        with patch.object(
            client,
            "rpc_ingest_batch",
            return_value={"memory_ids": ["m1", "m2"]},
        ):
            result = client.ingest_batch("seg", vectors, batch_size=10)
            assert result.memory_ids == ["m1", "m2"]

    def test_extracts_object_ids_from_response(self):
        """Should extract object_ids from response as memory_ids."""
        client = PlasmodClient(base_url="http://example.invalid")
        vectors = [[0.1], [0.2]]

        with patch.object(
            client,
            "rpc_ingest_batch",
            return_value={"object_ids": ["o1", "o2"]},
        ):
            result = client.ingest_batch("seg", vectors, batch_size=10)
            assert result.memory_ids == ["o1", "o2"]


class TestAddVectors:
    """Tests for PlasmodHttpClient.add_vectors method."""

    def test_delegates_to_ingest_batch(self):
        """add_vectors should delegate to ingest_batch."""
        client = PlasmodClient(base_url="http://example.invalid")
        vectors = [[0.1], [0.2]]

        with patch.object(
            client,
            "ingest_batch",
            return_value=BatchResult(total_count=2, accepted_count=2, batch_count=1),
        ) as mock:
            result = client.add_vectors(vectors, segment_id="custom.seg", batch_size=100)

            mock.assert_called_once_with(
                "custom.seg",
                vectors,
                None,
                batch_size=100,
                raise_on_error=True,
            )
            assert result.accepted_count == 2

    def test_default_segment_id(self):
        """Default segment_id should be warm.default."""
        client = PlasmodClient(base_url="http://example.invalid")
        vectors = [[0.1]]

        with patch.object(
            client,
            "ingest_batch",
            return_value=BatchResult(total_count=1, accepted_count=1, batch_count=1),
        ) as mock:
            client.add_vectors(vectors)
            assert mock.call_args[0][0] == "warm.default"


class TestIngestEvents:
    """Tests for PlasmodHttpClient.ingest_events method."""

    def test_empty_events(self):
        """Empty events should return empty BatchResult."""
        client = PlasmodClient(base_url="http://example.invalid")
        result = client.ingest_events([])
        assert result.total_count == 0
        assert result.batch_count == 0

    def test_ingests_each_event(self):
        """Should call ingest_event for each event."""
        client = PlasmodClient(base_url="http://example.invalid")
        events = [
            {"event_id": "e1", "event_type": "test"},
            {"event_id": "e2", "event_type": "test"},
            {"event_id": "e3", "event_type": "test"},
        ]

        with patch.object(
            client,
            "ingest_event",
            return_value={"memory_id": "m1"},
        ) as mock:
            result = client.ingest_events(events, batch_size=10)

            assert mock.call_count == 3
            assert result.total_count == 3
            assert result.accepted_count == 3
            assert result.batch_count == 1

    def test_extracts_memory_id_from_response(self):
        """Should extract memory_id from each event response."""
        client = PlasmodClient(base_url="http://example.invalid")
        events = [{"event_id": "e1"}, {"event_id": "e2"}]

        responses = [{"memory_id": "m1"}, {"memory_id": "m2"}]

        with patch.object(client, "ingest_event", side_effect=responses):
            result = client.ingest_events(events)
            assert result.memory_ids == ["m1", "m2"]

    def test_event_failure_raise_on_error_true(self):
        """With raise_on_error=True, should raise on first failure."""
        client = PlasmodClient(base_url="http://example.invalid")
        events = [{"event_id": "e1"}, {"event_id": "e2"}]

        def fail_on_second(event):
            if event["event_id"] == "e2":
                raise PlasmodHttpError(400, reason="Bad event", body="", path="")
            return {"memory_id": "m1"}

        with patch.object(client, "ingest_event", side_effect=fail_on_second):
            with pytest.raises(PlasmodException, match="Event 1 failed"):
                client.ingest_events(events, raise_on_error=True)

    def test_event_failure_raise_on_error_false(self):
        """With raise_on_error=False, should collect errors and continue."""
        client = PlasmodClient(base_url="http://example.invalid")
        events = [{"event_id": "e1"}, {"event_id": "e2"}, {"event_id": "e3"}]

        def fail_on_second(event):
            if event["event_id"] == "e2":
                raise PlasmodHttpError(400, reason="Bad event", body="", path="")
            return {"memory_id": event["event_id"]}

        with patch.object(client, "ingest_event", side_effect=fail_on_second):
            result = client.ingest_events(events, raise_on_error=False)

            assert result.total_count == 3
            assert result.accepted_count == 2
            assert result.failed_count == 1
            assert len(result.errors) == 1
            assert result.errors[0]["event_index"] == 1


class TestBatchQuery:
    """Tests for PlasmodHttpClient.batch_query method."""

    def test_empty_queries(self):
        """Empty queries should return empty list."""
        client = PlasmodClient(base_url="http://example.invalid")
        result = client.batch_query([])
        assert result == []

    def test_executes_each_query(self):
        """Should execute each query and collect results."""
        client = PlasmodClient(base_url="http://example.invalid")
        queries = [
            {"query_text": "q1", "top_k": 5},
            {"query_text": "q2", "top_k": 5},
        ]

        responses = [{"objects": ["r1"]}, {"objects": ["r2"]}]

        with patch.object(client, "query", side_effect=responses) as mock:
            results = client.batch_query(queries)

            assert mock.call_count == 2
            assert len(results) == 2
            assert results[0] == {"objects": ["r1"]}
            assert results[1] == {"objects": ["r2"]}

    def test_preserves_order(self):
        """Results should be in same order as queries."""
        client = PlasmodClient(base_url="http://example.invalid")
        queries = [{"id": i} for i in range(10)]

        def return_id(query):
            return {"result_id": query["id"]}

        with patch.object(client, "query", side_effect=return_id):
            results = client.batch_query(queries, batch_size=3)

            for i, result in enumerate(results):
                assert result["result_id"] == i
