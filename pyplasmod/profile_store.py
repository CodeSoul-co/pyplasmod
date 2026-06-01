# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Local Plasmod connection profiles (MilvusClient-style ``*.db`` paths)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional

DEFAULT_PROFILE_URI = "http://127.0.0.1:19530"

PROFILE_JSON = "profile.json"
DATA_DIRNAME = "data"
PROFILE_KIND = "plasmod_profile"


def is_profile_path(value: str) -> bool:
    v = value.strip()
    if v.endswith(".db") or v.endswith(".json"):
        return True
    return "/" in v or "\\" in v or v.startswith(".")


def ensure_profile_layout(user_path: Path) -> tuple[Path, Optional[Path]]:
    """
    Resolve how a Milvus-style ``*.db`` path is stored on disk.

    * **Milvus Lite** ``foo.db`` → directory ``foo.db/`` with embedded vector files.
    * **pyplasmod** ``foo.db/`` → ``profile.json`` (connection + collection metadata) and
      ``data/`` (optional host mount for Plasmod server persistence when Docker auto-starts).

    Legacy: a single JSON **file** named ``foo.db`` is still supported.
    """
    user_path = Path(user_path)

    if user_path.is_file():
        return user_path, None

    if user_path.is_dir():
        data_dir = user_path / DATA_DIRNAME
        data_dir.mkdir(parents=True, exist_ok=True)
        profile_path = user_path / PROFILE_JSON
        if not profile_path.is_file():
            _write_profile_file(profile_path, _default_profile())
        return profile_path, data_dir

    # New path — ``*.db`` uses a directory (same convention as Milvus Lite).
    if user_path.suffix == ".db":
        user_path.mkdir(parents=True, exist_ok=True)
        data_dir = user_path / DATA_DIRNAME
        data_dir.mkdir(parents=True, exist_ok=True)
        profile_path = user_path / PROFILE_JSON
        _write_profile_file(profile_path, _default_profile())
        return profile_path, data_dir

    user_path.parent.mkdir(parents=True, exist_ok=True)
    if not user_path.is_file():
        _write_profile_file(user_path, _default_profile())
    return user_path, None


def read_profile(profile_path: Path) -> dict[str, Any]:
    if profile_path.is_file():
        with profile_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("kind", PROFILE_KIND)
            data.setdefault("collections", {})
            return data
    profile = _default_profile()
    _write_profile_file(profile_path, profile)
    return profile


def write_profile(profile_path: Path, profile: Mapping[str, Any]) -> None:
    payload = dict(profile)
    payload.setdefault("kind", PROFILE_KIND)
    payload.setdefault("collections", {})
    _write_profile_file(profile_path, payload)


def profile_uri(profile: Mapping[str, Any]) -> str:
    uri = str(profile.get("uri") or "").strip()
    if not uri:
        uri = DEFAULT_PROFILE_URI
    return uri.rstrip("/")


def _default_profile() -> dict[str, Any]:
    return {
        "kind": PROFILE_KIND,
        "uri": DEFAULT_PROFILE_URI,
        "token": "",
        "collections": {},
        "note": (
            "Plasmod local profile (MilvusClient-style *.db). "
            "pip install pyplasmod bundles faiss-cpu for embedded insert/search under collections/."
        ),
    }


def _write_profile_file(path: Path, profile: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
        f.write("\n")
