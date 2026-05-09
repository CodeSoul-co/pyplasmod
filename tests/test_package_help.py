# Copyright (C) 2019-2021 Zilliz. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.

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
    assert "未知主题" in buf.getvalue()


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
