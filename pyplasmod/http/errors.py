# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

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
