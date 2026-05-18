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

import struct
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pyplasmod.data import build_query_body, upload
from pyplasmod.http.client import PlasmodHttpClient


def _write_fbin(path: Path, n: int, dim: int, fill: float = 0.25) -> None:
    with path.open("wb") as f:
        f.write(struct.pack("<II", n, dim))
        for _ in range(n):
            for _ in range(dim):
                f.write(struct.pack("<f", fill))


def test_upload_dry_run_empty_file():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "empty.fbin"
        _write_fbin(p, 0, 4)
        assert upload("ds", "w", p, dry_run=True) == 0


def test_upload_dry_run_non_empty():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "one.fbin"
        _write_fbin(p, 3, 2)
        assert upload("ds", "w", p, dry_run=True) == 1


def test_upload_rejects_non_fbin_suffix():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "data.csv"
        p.write_text("a,b\n", encoding="utf-8")
        with pytest.raises(ValueError, match="暂时无法处理"):
            upload("ds", "w", p, dry_run=True)


def test_build_query_body_and_client_query():
    client = MagicMock(spec=PlasmodHttpClient)
    client.query.return_value = {"objects": ["a"]}
    body = build_query_body("hello", "w_x", top_k=5)
    out = client.query(body)
    assert out == {"objects": ["a"]}
    client.query.assert_called_once_with(body)
    assert body["query_text"] == "hello"
    assert body["query_scope"] == "w_x"
    assert body["workspace_id"] == "w_x"
    assert body["top_k"] == 5
    assert body["relation_constraints"] == []
    assert body["session_id"] == "query_w_x"


def test_build_query_body_session_aligns_with_upload_when_fbin_given():
    body = build_query_body(
        "dataset=ds",
        "w",
        dataset_name="ds",
        ingest_fbin_path="/tmp/foo.fbin",
    )
    assert body["session_id"] == "ingest_ds_foo.fbin"


def test_build_query_body_explicit_session_overrides_ingest_fbin_path():
    body = build_query_body(
        "dataset=ds",
        "w",
        session_id="s_custom",
        dataset_name="ds",
        ingest_fbin_path="/tmp/foo.fbin",
    )
    assert body["session_id"] == "s_custom"


def test_upload_with_show_progress_bar(capsys):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.fbin"
        _write_fbin(p, 3, 2)
        client = MagicMock(spec=PlasmodHttpClient)
        upload("ds", "w", p, client=client, show_progress=True)
    err = capsys.readouterr().err
    assert "100.0%" in err
    assert "(3/3)" in err


def test_upload_calls_ingest_event():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.fbin"
        _write_fbin(p, 2, 2)
        client = MagicMock(spec=PlasmodHttpClient)
        n = upload("myds", "w_space", p, client=client, progress_every=0)
        assert n == 2
        assert client.ingest_event.call_count == 2
        first = client.ingest_event.call_args_list[0][0][0]
        assert first["workspace_id"] == "w_space"
        assert first["payload"]["dataset"] == "myds"
        assert len(first["embedding_vector"]) == 2


def test_upload_default_import_batch_id_unique_per_call():
    """Omitting import_batch_id must not reuse one batch for two uploads in the same second."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.fbin"
        _write_fbin(p, 1, 2)
        client = MagicMock(spec=PlasmodHttpClient)
        upload("ds", "w", p, client=client, progress_every=0)
        upload("ds", "w", p, client=client, progress_every=0)
        bid1 = client.ingest_event.call_args_list[0][0][0]["payload"]["import_batch_id"]
        bid2 = client.ingest_event.call_args_list[1][0][0]["payload"]["import_batch_id"]
        assert bid1 != bid2
        assert bid1.startswith("batch_")
        assert bid2.startswith("batch_")
