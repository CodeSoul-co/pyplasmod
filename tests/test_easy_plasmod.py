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

import json
from unittest.mock import MagicMock, patch

from pyplasmod import EasyPlasmod


def _ok_json(data):
    r = MagicMock()
    r.ok = True
    r.status_code = 200
    r.text = json.dumps(data)
    r.headers = {"Content-Type": "application/json"}
    r.json.return_value = data
    return r


def test_easy_plasmod_delegates_health_and_search():
    e = EasyPlasmod(base_url="http://example.invalid")
    with patch.object(e.http._session, "request", return_value=_ok_json({"status": "ok"})) as m:
        assert e.health() == {"status": "ok"}
        args, kwargs = m.call_args
        assert args[1].endswith("/healthz")
    with patch.object(e.http._session, "request", return_value=_ok_json({"objects": []})) as m:
        assert e.search("hi", "w1", top_k=3) == {"objects": []}
        _, kwargs = m.call_args
        assert kwargs["json"]["query_text"] == "hi"
        assert kwargs["json"]["workspace_id"] == "w1"
        assert kwargs["json"]["top_k"] == 3


def test_easy_plasmod_memories_merges_workspace_id():
    e = EasyPlasmod(base_url="http://example.invalid")
    with patch.object(e.http._session, "request", return_value=_ok_json([])) as m:
        assert e.memories("w_demo", limit=10) == []
        _, kwargs = m.call_args
        assert kwargs["params"] == {"workspace_id": "w_demo", "limit": 10}
