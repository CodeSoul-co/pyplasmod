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

"""Exceptions for the Plasmod HTTP SDK (see Plasmod ``docs/sdk/README.md``)."""

from __future__ import annotations


class PlasmodException(Exception):
    """Base SDK error."""

    def __init__(self, message: str = "", *, code: int = 1) -> None:
        super().__init__(message)
        self._message = message
        self._code = code

    @property
    def message(self) -> str:
        return self._message

    @property
    def code(self) -> int:
        return self._code

    def __str__(self) -> str:
        return f"<{type(self).__name__}: (code={self.code}, message={self.message!r})>"


class ParamError(PlasmodException):
    """Invalid parameters (often maps from HTTP 400)."""


class ConnectError(PlasmodException):
    """Transport / connection failure before a response is received."""


class PlasmodUnavailableException(PlasmodException):
    """Server unavailable or overloaded (e.g. HTTP 503)."""


__all__ = [
    "ConnectError",
    "ParamError",
    "PlasmodException",
    "PlasmodUnavailableException",
]
