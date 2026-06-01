# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

import json
from pathlib import Path

from pyplasmod.profile_store import (
    DATA_DIRNAME,
    PROFILE_JSON,
    ensure_profile_layout,
    read_profile,
)


def test_new_db_path_creates_directory_like_milvus(tmp_path: Path):
    root = tmp_path / "plasmod_demo.db"
    profile_json, data_dir = ensure_profile_layout(root)
    assert root.is_dir()
    assert profile_json == root / PROFILE_JSON
    assert profile_json.is_file()
    assert data_dir == root / DATA_DIRNAME
    assert data_dir.is_dir()
    profile = read_profile(profile_json)
    assert profile["kind"] == "plasmod_profile"
    assert "uri" in profile


def test_legacy_single_file_profile_still_works(tmp_path: Path):
    legacy = tmp_path / "legacy.db"
    legacy.write_text(
        json.dumps({"uri": "http://127.0.0.1:19530", "collections": {}}),
        encoding="utf-8",
    )
    profile_json, data_dir = ensure_profile_layout(legacy)
    assert profile_json == legacy
    assert legacy.is_file()
    assert data_dir is None
