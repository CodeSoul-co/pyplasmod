# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""
Binary wire formats for Plasmod ``/v1/internal/rpc/*``.

Authoritative Go: ``src/internal/transport/framing.go``.
"""

from __future__ import annotations

import struct
from typing import Optional, Sequence

_MAGIC_PLIB = b"PLIB"
_MAGIC_PLQW = b"PLQW"
_MAGIC_PLQB = b"PLQB"

_MAX_BATCH_VECTORS = 1 << 22
_MAX_DIM = 1 << 14
_MAX_ID_LEN = 1 << 12
_MAX_QUERY_BATCH = 1 << 16


def encode_ingest_batch(
    segment_id: str,
    vectors: Sequence[Sequence[float]],
    object_ids: Optional[Sequence[str]] = None,
    *,
    wire_version: int = 1,
) -> bytes:
    """Encode ``POST /v1/internal/rpc/ingest_batch`` body (PLIB)."""
    if wire_version not in (1, 2):
        raise ValueError("wire_version must be 1 or 2")
    if len(vectors) == 0:
        raise ValueError("vectors must be non-empty")
    dim = len(vectors[0])
    n = len(vectors)
    if n > _MAX_BATCH_VECTORS or dim > _MAX_DIM:
        raise ValueError("n or dim exceeds server limits")
    ids: Sequence[str] = object_ids or [f"{segment_id}_{i}" for i in range(n)]
    if len(ids) != n:
        raise ValueError("object_ids length must match vectors length")
    sid = segment_id.encode("utf-8")
    if len(sid) > _MAX_ID_LEN:
        raise ValueError("segment_id too long")

    out = bytearray()
    out += _MAGIC_PLIB
    out += bytes([wire_version])
    out += len(sid).to_bytes(2, "little")
    out += sid
    out += n.to_bytes(4, "little")
    out += dim.to_bytes(4, "little")
    for row in vectors:
        if len(row) != dim:
            raise ValueError("all rows must have length dim")
        for f in row:
            out += struct.pack("<f", float(f))
    for oid in ids:
        b = oid.encode("utf-8")
        if len(b) > _MAX_ID_LEN:
            raise ValueError("object id too long")
        out += len(b).to_bytes(2, "little") + b
    return bytes(out)


def encode_query_warm(segment_id: str, top_k: int, vector: Sequence[float]) -> bytes:
    """Encode ``POST /v1/internal/rpc/query_warm`` body (PLQW)."""
    dim = len(vector)
    if dim <= 0 or dim > _MAX_DIM:
        raise ValueError("invalid dim")
    sid = segment_id.encode("utf-8")
    if len(sid) > _MAX_ID_LEN:
        raise ValueError("segment_id too long")
    out = bytearray()
    out += _MAGIC_PLQW
    out += bytes([1])
    out += len(sid).to_bytes(2, "little")
    out += sid
    out += int(top_k).to_bytes(4, "little")
    out += dim.to_bytes(4, "little")
    for f in vector:
        out += struct.pack("<f", float(f))
    return bytes(out)


def encode_query_warm_batch(
    segment_id: str,
    top_k: int,
    queries: Sequence[Sequence[float]],
) -> bytes:
    """Encode ``POST /v1/internal/rpc/query_warm_batch`` body (PLQB)."""
    if len(queries) == 0:
        raise ValueError("queries must be non-empty")
    nq = len(queries)
    if nq > _MAX_QUERY_BATCH:
        raise ValueError("nq exceeds server limit")
    dim = len(queries[0])
    if dim <= 0 or dim > _MAX_DIM:
        raise ValueError("invalid dim")
    for row in queries:
        if len(row) != dim:
            raise ValueError("all query rows must have length dim")
    sid = segment_id.encode("utf-8")
    if len(sid) > _MAX_ID_LEN:
        raise ValueError("segment_id too long")

    out = bytearray()
    out += _MAGIC_PLQB
    out += bytes([1])
    out += len(sid).to_bytes(2, "little")
    out += sid
    out += int(top_k).to_bytes(4, "little")
    out += nq.to_bytes(4, "little")
    out += dim.to_bytes(4, "little")
    for row in queries:
        for f in row:
            out += struct.pack("<f", float(f))
    return bytes(out)


def decode_query_warm_response(data: bytes) -> list[str]:
    """Decode binary response from ``query_warm``: ``n(u32)`` + repeated ``id_len(u16)+id``."""
    off = 0
    if len(data) < 4:
        raise ValueError("truncated query_warm response")
    (n,) = struct.unpack_from("<I", data, off)
    off += 4
    out: list[str] = []
    for _ in range(n):
        if off + 2 > len(data):
            raise ValueError("truncated query_warm id header")
        (ilen,) = struct.unpack_from("<H", data, off)
        off += 2
        if off + ilen > len(data):
            raise ValueError("truncated query_warm id bytes")
        out.append(data[off : off + ilen].decode("utf-8"))
        off += ilen
    if off != len(data):
        raise ValueError("trailing bytes in query_warm response")
    return out


def decode_query_warm_batch_response(data: bytes) -> tuple[int, int, list[int], list[float]]:
    """Decode ``query_warm_batch`` response: header + int64 ids + float32 distances (row-major)."""
    if len(data) < 8:
        raise ValueError("truncated PLQB response header")
    nq, topk = struct.unpack_from("<II", data, 0)
    count = nq * topk
    need = 8 + count * 8 + count * 4
    if len(data) < need:
        raise ValueError("truncated PLQB response body")
    off = 8
    internal_ids: list[int] = []
    for _ in range(count):
        internal_ids.append(struct.unpack_from("<q", data, off)[0])
        off += 8
    dists: list[float] = []
    for _ in range(count):
        dists.append(struct.unpack_from("<f", data, off)[0])
        off += 4
    if off != len(data):
        raise ValueError("trailing bytes in query_warm_batch response")
    return nq, topk, internal_ids, dists
