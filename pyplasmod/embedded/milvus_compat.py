# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""MilvusClient-shaped response helpers (Plasmod naming, pymilvus-compatible payloads)."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence


def format_insert_result(
    *,
    object_ids: Sequence[Any],
    insert_count: Optional[int] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    count = insert_count if insert_count is not None else len(object_ids)
    payload: dict[str, Any] = {
        "insert_count": count,
        "ids": list(object_ids),
    }
    if extra:
        payload.update(extra)
    return payload


def format_search_hit(
    *,
    hit_id: Any,
    distance: float,
    entity: Optional[Mapping[str, Any]] = None,
    output_fields: Optional[Sequence[str]] = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {"id": hit_id, "distance": distance}
    full_entity = dict(entity or {})
    if "id" not in full_entity:
        full_entity["id"] = hit_id
    if output_fields:
        row["entity"] = {k: full_entity[k] for k in output_fields if k in full_entity}
    else:
        row["entity"] = full_entity
    return row


def format_search_results(
    batch_hits: Sequence[Sequence[dict[str, Any]]],
) -> list[list[dict[str, Any]]]:
    """Return pymilvus-style ``[[{id, distance, entity}, ...], ...]`` (one list per query)."""
    return [list(group) for group in batch_hits]
