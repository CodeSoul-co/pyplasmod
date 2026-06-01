# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Shared on-disk layout for embedded warm collections (Milvus Lite–style ``*.db/collections/``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional, Sequence


def collection_dir(profile_root: Path, collection_name: str) -> Path:
    return profile_root.resolve() / "collections" / collection_name


def manifest_path(profile_root: Path, collection_name: str) -> Path:
    return collection_dir(profile_root, collection_name) / "warm_manifest.json"


def read_manifest(profile_root: Path, collection_name: str) -> dict[str, Any]:
    path = manifest_path(profile_root, collection_name)
    if not path.is_file():
        raise ValueError(f"embedded collection {collection_name!r} has no warm data")
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(profile_root: Path, collection_name: str, payload: Mapping[str, Any]) -> None:
    coll_dir = collection_dir(profile_root, collection_name)
    coll_dir.mkdir(parents=True, exist_ok=True)
    manifest_path(profile_root, collection_name).write_text(
        json.dumps(dict(payload), indent=2),
        encoding="utf-8",
    )


def merge_entities(
    existing: Optional[Mapping[str, Any]],
    object_ids: Sequence[str],
    entities: Optional[Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    merged: dict[str, Any] = dict(existing or {})
    if not entities:
        return merged
    for oid, row in zip(object_ids, entities):
        merged[str(oid)] = dict(row)
    return merged


def drop_collection_data(profile_root: Path, collection_name: str) -> None:
    import shutil

    coll_dir = collection_dir(profile_root, collection_name)
    if coll_dir.is_dir():
        shutil.rmtree(coll_dir, ignore_errors=True)
