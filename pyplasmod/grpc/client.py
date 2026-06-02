# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""gRPC client for Plasmod ``plasmod.v1.PlasmodAPIService``."""

from __future__ import annotations

import json
import os
from typing import Any, Mapping, Optional, Sequence

from pyplasmod.grpc.deploy import resolve_grpc_target
from pyplasmod.grpc.errors import PlasmodGrpcError, raise_for_rpc_error
from pyplasmod.grpc.pb.plasmod.v1 import plasmod_pb2, plasmod_pb2_grpc
from pyplasmod.http.warm_index import warm_index_ingest_fields

try:
    import grpc
except ImportError as exc:  # pragma: no cover - exercised when optional dep missing
    grpc = None  # type: ignore[assignment]
    _GRPC_IMPORT_ERROR = exc
else:
    _GRPC_IMPORT_ERROR = None


def _require_grpc() -> None:
    if grpc is None:
        raise ImportError(
            "pyplasmod gRPC transport requires grpcio. Install with: pip install pyplasmod[grpc]"
        ) from _GRPC_IMPORT_ERROR


def _vector_rows(vectors: Sequence[Sequence[float]]) -> list[plasmod_pb2.VectorRow]:
    return [plasmod_pb2.VectorRow(values=[float(v) for v in row]) for row in vectors]


def _query_batch_response_to_dict(resp: plasmod_pb2.QueryBatchResponse) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for row in resp.rows:
        rows.append(
            {
                "row_index": int(row.row_index),
                "object_ids": list(row.object_ids),
                "distances": list(row.distances),
                "source_refs": list(row.source_refs),
            }
        )
    by_source = {key: list(val.values) for key, val in resp.by_source.items()}
    return {
        "status": resp.status,
        "agent_mode": resp.agent_mode,
        "warm_segment_id": resp.warm_segment_id,
        "source_ids": list(resp.source_ids),
        "rows": rows,
        "by_source": by_source,
    }


class PlasmodGrpcClient:
    """
    Plasmod gRPC SDK client for ``PlasmodAPIService``.

    Mirrors the HTTP JSON semantics of ``POST /v1/ingest/*`` and ``POST /v1/query*``.
    Admin routes, SSE, and binary internal RPC remain on :class:`~pyplasmod.http.client.PlasmodHttpClient`.

    Default target: ``PLASMOD_GRPC_ADDR`` or ``127.0.0.1:19531`` (parallel to HTTP :19530).
    """

    def __init__(
        self,
        target: Optional[str] = None,
        *,
        http_base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        channel: Any = None,
        options: Optional[Sequence[tuple[str, Any]]] = None,
    ) -> None:
        _require_grpc()
        self.target = resolve_grpc_target(target, http_base_url=http_base_url)
        env_timeout = os.environ.get("PLASMOD_GRPC_TIMEOUT") or os.environ.get(
            "PLASMOD_HTTP_TIMEOUT",
            "30",
        )
        self.timeout = float(timeout) if timeout is not None else float(env_timeout)
        self._owns_channel = channel is None
        self._channel = channel or grpc.insecure_channel(self.target, options=options)
        self._stub = plasmod_pb2_grpc.PlasmodAPIServiceStub(self._channel)

    def close(self) -> None:
        if self._owns_channel:
            self._channel.close()

    def __enter__(self) -> PlasmodGrpcClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _call(self, method: str, request: Any) -> Any:
        stub_method = getattr(self._stub, method)
        try:
            return stub_method(request, timeout=self.timeout)
        except Exception as exc:
            raise_for_rpc_error(exc, method=method)

    def health(self) -> dict[str, Any]:
        resp = self._call("Health", plasmod_pb2.HealthRequest())
        return {"status": resp.status, "transport": resp.transport}

    def ingest_event(self, event: Mapping[str, Any]) -> Any:
        req = plasmod_pb2.IngestEventRequest(event_json=json.dumps(dict(event), ensure_ascii=False))
        resp = self._call("IngestEvent", req)
        if not resp.ack_json.strip():
            return None
        return json.loads(resp.ack_json)

    def ingest_vectors(
        self,
        vectors: Sequence[Sequence[float]],
        *,
        segment_id: str = "warm.default",
        object_ids: Optional[Sequence[str]] = None,
        index_type: Optional[str] = None,
        ivf_nlist: int = 0,
        ivf_nprobe: int = 0,
        ivf_m: int = 0,
        ivf_nbits: int = 0,
        ivf_sq_type: str = "",
    ) -> dict[str, Any]:
        fields = warm_index_ingest_fields(
            index_type,
            ivf_nlist=ivf_nlist,
            ivf_nprobe=ivf_nprobe,
            ivf_m=ivf_m,
            ivf_nbits=ivf_nbits,
            ivf_sq_type=ivf_sq_type,
        )
        req = plasmod_pb2.IngestVectorsRequest(
            segment_id=segment_id,
            object_ids=list(object_ids) if object_ids is not None else [],
            vectors=_vector_rows(vectors),
            index_type=str(fields.get("index_type", "")),
            ivf_nlist=int(fields.get("ivf_nlist", 0) or 0),
            ivf_nprobe=int(fields.get("ivf_nprobe", 0) or 0),
            ivf_m=int(fields.get("ivf_m", 0) or 0),
            ivf_nbits=int(fields.get("ivf_nbits", 0) or 0),
            ivf_sq_type=str(fields.get("ivf_sq_type", "") or ""),
        )
        resp = self._call("IngestVectors", req)
        return {
            "status": resp.status,
            "segment_id": resp.segment_id,
            "ingested": int(resp.ingested),
            "vector_dim": int(resp.vector_dim),
            "index_type": resp.index_type,
            "direct_warm": bool(resp.direct_warm),
        }

    def query(self, body: Mapping[str, Any]) -> Any:
        req = plasmod_pb2.QueryRequest(
            query_json=json.dumps(dict(body), ensure_ascii=False),
        )
        resp = self._call("Query", req)
        if not resp.result_json.strip():
            return None
        return json.loads(resp.result_json)

    def query_batch(self, body: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(body)
        vectors = payload.get("vectors") or []
        row_lineage = payload.get("row_lineage") or []
        req = plasmod_pb2.QueryBatchRequest(
            agent_mode=str(payload.get("agent_mode", "")),
            warm_segment_id=str(payload.get("warm_segment_id", "")),
            top_k=int(payload.get("top_k", 0) or 0),
            vectors=_vector_rows([list(map(float, row)) for row in vectors]),
            source_ids=[str(x) for x in payload.get("source_ids", [])],
            row_lineage=[
                plasmod_pb2.RowLineage(source_indices=[int(i) for i in (row or [])])
                for row in row_lineage
            ],
            search_raw=bool(payload.get("search_raw", False)),
        )
        resp = self._call("QueryBatch", req)
        return _query_batch_response_to_dict(resp)


__all__ = ["PlasmodGrpcClient", "PlasmodGrpcError"]
