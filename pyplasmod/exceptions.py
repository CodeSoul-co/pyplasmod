# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Exceptions for the Plasmod HTTP SDK (see Plasmod ``docs/api``)."""

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
