# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""High-level helpers: ``.fbin`` → ``ingest_event``; ``build_query_body`` for ``PlasmodHttpClient.query``."""

from __future__ import annotations

import datetime as dt
import re
import struct
import time
import sys
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Optional, Sequence, TextIO

from pyplasmod.http.client import PlasmodHttpClient

__all__ = ["build_query_body", "upload"]


def _now_iso() -> str:
    return (
        dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def _slug_token(value: str, fallback: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return token or fallback


def _default_import_batch_id() -> str:
    """UTC time + microsecond + ``time.time_ns()`` so two ``upload()`` calls in the same second differ."""
    t = dt.datetime.now(dt.timezone.utc)
    return f"batch_{t.strftime('%Y%m%dT%H%M%S')}_{t.microsecond:06d}_{time.time_ns()}"


def _preview(vals: list[float], k: int) -> str:
    if k <= 0:
        return ""
    return " ".join(str(v) for v in vals[:k])


def _iter_fbin_rows(path: Path, limit: int) -> Iterator[tuple[int, int, list[float]]]:
    with path.open("rb") as f:
        header = f.read(8)
        if len(header) != 8:
            raise RuntimeError(f"{path}: malformed fbin header")
        n, dim = struct.unpack("<II", header)
        if dim == 0 or dim > 100000:
            raise RuntimeError(f"{path}: unexpected dim={dim}")
        rows = min(n, limit) if limit > 0 else n
        for i in range(rows):
            b = f.read(4 * dim)
            if len(b) != 4 * dim:
                raise RuntimeError(f"{path}: truncated data at row {i}")
            row = list(struct.unpack("<" + "f" * dim, b))
            yield i, dim, row


def _fbin_total_rows(path: Path, limit: int) -> int:
    """Number of rows that will be read (respects ``limit`` when ``limit > 0``)."""
    with path.open("rb") as f:
        hdr = f.read(8)
        if len(hdr) != 8:
            raise RuntimeError(f"{path}: malformed fbin header")
        n, dim = struct.unpack("<II", hdr)
        if dim == 0 or dim > 100000:
            raise RuntimeError(f"{path}: unexpected dim={dim}")
    if limit > 0:
        return min(int(n), limit)
    return int(n)


def _write_progress_bar(
    done: int,
    total: int,
    *,
    width: int = 28,
    file: Optional[TextIO] = None,
) -> None:
    """Single-line terminal progress bar (``\\r`` + flush). Uses stderr by default."""
    out = file if file is not None else sys.stderr
    if total <= 0:
        return
    done = min(max(0, done), total)
    filled = int(round(width * (done / total)))
    if done > 0 and filled == 0:
        filled = 1
    filled = min(width, filled)
    bar = "=" * (filled - 1) + ">" if filled > 0 else ""
    bar = bar.ljust(width, ".")
    pct = 100.0 * (done / total)
    out.write(f"\r[pyplasmod.data] [{bar}] {pct:5.1f}% ({done}/{total})")
    out.flush()


def _build_fbin_event(
    *,
    path: Path,
    row_i: int,
    dim: int,
    vector: list[float],
    preview_k: int,
    dataset: str,
    tenant_id: str,
    workspace_id: str,
    agent_id: str,
    session_id: str,
    event_type: str,
    source: str,
    version: int,
    import_batch_id: str,
    seq: int,
    event_id_scope: str,
) -> dict[str, Any]:
    ts = _now_iso()
    dataset_token = _slug_token(dataset, "dataset")
    file_token = _slug_token(path.stem, "file")
    if event_id_scope == "batch":
        batch_token = _slug_token(import_batch_id, "batch")
        ev_id = f"evt_{dataset_token}_{batch_token}_{file_token}_{seq:08d}"
    else:
        ev_id = f"evt_{dataset_token}_{file_token}_{seq:08d}"
    dtype = "float32"
    txt = (
        f"dataset={path.name} dataset_name:{dataset} row:{row_i} "
        f"dim:{dim} dtype:{dtype} head:{_preview(vector, preview_k)}"
    )
    return {
        "event_id": ev_id,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "agent_id": agent_id,
        "session_id": session_id,
        "event_type": event_type,
        "event_time": ts,
        "ingest_time": ts,
        "visible_time": ts,
        "embedding_vector": vector,
        "payload": {
            "text": txt,
            "dataset": dataset,
            "file_name": path.name,
            "row_index": row_i,
            "dim": dim,
            "dtype": dtype,
            "ingest_mode": "bulk_dataset",
            "import_batch_id": import_batch_id,
        },
        "source": source,
        "version": version,
    }


def build_query_body(
    query_text: str,
    workspace_id: str,
    *,
    tenant_id: str = "t_demo",
    session_id: str = "",
    agent_id: str = "pyplasmod_data",
    top_k: int = 10,
    response_mode: str = "structured_evidence",
    include_cold: bool = True,
    dataset_name: Optional[str] = None,
    ingest_fbin_path: str | Path | None = None,
    import_batch_id: str = "",
    latest_batch_only: bool = False,
    source_file_name: str = "",
    embedding_vector: Optional[Sequence[float]] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """
    Build a minimal ``QueryRequest``-shaped dict for :meth:`PlasmodHttpClient.query`.

    Does **not** send HTTP — call ``client.query(build_query_body(...))`` yourself so
    there is a single query path (same as ``docs/SDK.md`` §4.2).

    ``query_scope`` and ``workspace_id`` are both set to ``workspace_id``. Merge
    overrides last via ``extra={...}``.

    When the gateway applies structured filters (e.g. non-empty ``dataset_name``),
    ``session_id`` / ``agent_id`` must match the values used at ingest time. If you
    omit ``session_id`` but pass ``dataset_name`` and the same ``.fbin`` path as
    :func:`upload` via ``ingest_fbin_path``, the default session matches
    ``upload``'s ``ingest_{dataset}_{filename}`` rule. Otherwise the default is
    ``query_{workspace_id}``.

    Pass ``embedding_vector`` to query with a precomputed dense vector (skips the
    gateway embedder). Omit it to use server-side embedding (CPU/GPU per
    ``PLASMOD_EMBEDDER_DEVICE`` — see :mod:`pyplasmod.embedding`).
    """
    sid = session_id.strip()
    if not sid:
        ds = (dataset_name or "").strip()
        fbin_name = Path(ingest_fbin_path).name if ingest_fbin_path is not None else ""
        if ds and fbin_name:
            sid = f"ingest_{ds}_{fbin_name}"
        else:
            sid = f"query_{workspace_id}"
    body: dict[str, Any] = {
        "query_text": query_text,
        "query_scope": workspace_id,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "session_id": sid,
        "agent_id": agent_id,
        "top_k": int(top_k),
        "time_window": {"from": "1970-01-01T00:00:00Z", "to": "2099-12-31T23:59:59Z"},
        "relation_constraints": [],
        "response_mode": response_mode,
        "include_cold": include_cold,
    }
    if dataset_name:
        body["dataset_name"] = dataset_name
    if import_batch_id:
        body["import_batch_id"] = import_batch_id
    if latest_batch_only:
        body["latest_batch_only"] = True
    if source_file_name:
        body["source_file_name"] = source_file_name
    if embedding_vector is not None:
        body["embedding_vector"] = [float(x) for x in embedding_vector]
    if extra:
        body.update(dict(extra))
    return body


def upload(
    dataset: str,
    workspace_id: str,
    path: str | Path,
    *,
    tenant_id: str = "t_demo",
    base_url: Optional[str] = None,
    client: Optional[PlasmodHttpClient] = None,
    agent_id: str = "pyplasmod_data",
    session_id: str = "",
    event_type: str = "dataset_record",
    source: str = "pyplasmod.data",
    version: int = 1,
    import_batch_id: str = "",
    event_id_scope: str = "file",
    preview_k: int = 8,
    limit: int = 0,
    progress_every: int = 500,
    dry_run: bool = False,
    show_progress: bool = False,
    on_progress: Optional[Callable[[int], None]] = None,
    progress_file: Optional[TextIO] = None,
) -> int:
    """
    Upload a ``.fbin`` vector file to a running Plasmod via ``ingest_event`` (one row → one event).

    **File type:** only ``.fbin`` (case-insensitive suffix) is implemented. Other suffixes raise
    ``ValueError`` with a short \"not supported yet\" message so callers can branch without reading
    the file body.

    Positional arguments match the common call shape::

        from pyplasmod.data import upload
        upload(\"my_dataset\", \"w_demo\", \"/data/query.fbin\")

    Or::

        import pyplasmod.data as data
        data.upload(\"my_dataset\", \"w_demo\", \"/data/query.fbin\")

    Shell (same package)::

        python -m pyplasmod.data upload my_dataset w_demo /data/query.fbin

    Uses top-level ``embedding_vector`` (full row); server embedding dimension must match file ``dim``.

    :param dataset: Logical dataset name (payload + stable ``event_id`` tokens).
    :param workspace_id: Plasmod ``workspace_id``.
    :param path: Path to ``.fbin`` (uint32 n, uint32 dim, n×dim float32 LE).
    :param client: Optional existing ``PlasmodHttpClient``; if omitted, one is created from ``base_url``.
    :param base_url: Used only when ``client`` is ``None``. If omitted, uses the same env resolution
        as :class:`~pyplasmod.http.client.PlasmodHttpClient` (``PLASMOD_BASE_URL`` / ``ANDB_BASE_URL``,
        then ``http://127.0.0.1:8080``).
    :param limit: Max rows (``0`` = all).
    :param import_batch_id: Stored in each event payload; if empty after strip, a **new** UTC
        time-based id is generated **once per** ``upload()`` call (including two calls in the same
        second), so back-to-back imports do not silently share one batch unless you pass the same
        string explicitly.
    :param dry_run: If ``True``, build the first event only and do not POST.
    :param show_progress: If ``True``, redraw a one-line ASCII progress bar on stderr after each row.
    :param on_progress: Optional ``callable(rows_done: int)`` after each successful ingest.
    :param progress_file: Text stream for the progress bar (default ``sys.stderr``).
    :return: Number of rows processed (ingested or dry-run preview = 1).
    """
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(str(p))
    suf = p.suffix.lower()
    if suf != ".fbin":
        raise ValueError(
            f"暂时无法处理：当前 upload 仅支持 .fbin 向量文件；收到后缀 {p.suffix!r}（{p.name!r}）。"
            "其他格式后续再支持。"
        )

    batch_id = import_batch_id.strip() or _default_import_batch_id()
    sid = session_id.strip() or f"ingest_{dataset}_{p.name}"
    row_limit = limit if limit > 0 else 0

    seq = 0
    rows = _iter_fbin_rows(p, row_limit)
    if dry_run:
        try:
            next(rows)
        except StopIteration:
            return 0
        return 1

    c = (
        client
        if client is not None
        else PlasmodHttpClient(
            base_url=(base_url.strip() if isinstance(base_url, str) and base_url.strip() else None)
        )
    )
    total = _fbin_total_rows(p, row_limit)
    pf = progress_file if progress_file is not None else sys.stderr
    for row_i, dim, vector in _iter_fbin_rows(p, row_limit):
        body = _build_fbin_event(
            path=p,
            row_i=row_i,
            dim=dim,
            vector=vector,
            preview_k=preview_k,
            dataset=dataset,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
            session_id=sid,
            event_type=event_type,
            source=source,
            version=version,
            import_batch_id=batch_id,
            seq=seq,
            event_id_scope=event_id_scope,
        )
        c.ingest_event(body)
        seq += 1
        if on_progress is not None:
            on_progress(seq)
        if show_progress and total > 0:
            _write_progress_bar(seq, total, file=pf)
        elif not show_progress and progress_every > 0 and seq % progress_every == 0:
            print(f"  [pyplasmod.data] ingested {seq} rows ...", flush=True)

    if show_progress and total > 0:
        pf.write("\n")
        pf.flush()

    return seq
