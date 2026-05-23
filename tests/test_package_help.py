# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

from pyplasmod.package_help import plasmod_help, plasmod_topics


def test_plasmod_topics_includes_expected_keys() -> None:
    t = plasmod_topics()
    for name in ("easy", "client", "upload", "querybody", "env", "errors", "binary"):
        assert name in t


def test_plasmod_help_index_contains_easy() -> None:
    buf = io.StringIO()
    plasmod_help(None, file=buf)
    out = buf.getvalue()
    assert "easy" in out
    assert "python -m pyplasmod" in out


def test_plasmod_help_unknown_topic() -> None:
    buf = io.StringIO()
    plasmod_help("no-such-topic-xyz", file=buf)
    assert "Unknown topic" in buf.getvalue()


def test_plasmod_help_env() -> None:
    buf = io.StringIO()
    plasmod_help("env", file=buf)
    assert "PLASMOD_BASE_URL" in buf.getvalue()


def test_main_module_smoke() -> None:
    repo = Path(__file__).resolve().parent.parent
    r = subprocess.run(
        [sys.executable, "-m", "pyplasmod", "env"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "PLASMOD_BASE_URL" in r.stdout
