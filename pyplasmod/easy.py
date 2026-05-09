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

"""Small user-facing facade over :class:`~pyplasmod.http.client.PlasmodHttpClient`."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Union

from pyplasmod.data import build_query_body, upload as data_upload
from pyplasmod.http.client import PlasmodHttpClient


class EasyPlasmod:
    """
    Minimal API for demos and app integration: health, ingest, query, list memories.

    Full gateway surface (admin, RPC, internal task/MAS, …) remains on
    :attr:`http` (:class:`~pyplasmod.http.client.PlasmodHttpClient`).
    """

    __slots__ = ("http",)

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        timeout: Optional[float] = None,
        admin_key: Optional[str] = None,
        session: Optional[Any] = None,
    ) -> None:
        self.http = PlasmodHttpClient(
            base_url=base_url,
            timeout=timeout,
            admin_key=admin_key,
            session=session,
        )

    def close(self) -> None:
        self.http.close()

    def __enter__(self) -> EasyPlasmod:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def health(self) -> Any:
        return self.http.health()

    def system_mode(self) -> Any:
        return self.http.system_mode()

    def query(self, body: Mapping[str, Any]) -> Any:
        return self.http.query(body)

    def search(self, query_text: str, workspace_id: str, **kwargs: Any) -> Any:
        """``build_query_body`` + ``POST /v1/query``."""
        return self.http.query(build_query_body(query_text, workspace_id, **kwargs))

    def ingest_event(self, event: Mapping[str, Any]) -> Any:
        return self.http.ingest_event(event)

    def ingest_document(self, body: Mapping[str, Any]) -> Any:
        return self.http.ingest_document(body)

    def upload_fbin(
        self,
        dataset: str,
        workspace_id: str,
        path: Union[str, Path],
        **kwargs: Any,
    ) -> int:
        """``.fbin`` → :func:`pyplasmod.data.upload` using this instance's HTTP client."""
        return int(data_upload(dataset, workspace_id, path, client=self.http, **kwargs))

    def memories(self, workspace_id: str, **params: Any) -> Any:
        """``GET /v1/memory`` with ``workspace_id`` merged into query ``params``."""
        p: dict[str, Any] = {"workspace_id": workspace_id}
        p.update(params)
        return self.http.memory_get(params=p)


__all__ = ["EasyPlasmod"]
