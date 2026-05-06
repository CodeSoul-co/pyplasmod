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

"""HTTP errors raised by :class:`pyplasmod.http.PlasmodHttpClient`."""

from typing import Any, Optional

from pyplasmod.exceptions import PlasmodException


class PlasmodHttpError(PlasmodException):
    """Non-success HTTP response from a Plasmod server."""

    def __init__(
        self,
        status_code: int,
        *,
        reason: str = "",
        body: str = "",
        path: str = "",
        response_headers: Optional[Any] = None,
    ) -> None:
        msg = reason or body[:512] or f"HTTP {status_code}"
        super().__init__(msg, code=status_code if status_code else 1)
        self.status_code = status_code
        self.reason = reason
        self.body = body
        self.path = path
        self.response_headers = response_headers

    def __str__(self) -> str:
        return (
            f"<{type(self).__name__}: status={self.status_code}, path={self.path!r}, "
            f"body={self.body[:200]!r}>"
        )
