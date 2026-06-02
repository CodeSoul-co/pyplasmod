# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""gRPC errors raised by :class:`pyplasmod.grpc.client.PlasmodGrpcClient`."""

from __future__ import annotations

from typing import Any, Optional

from pyplasmod.exceptions import PlasmodException


class PlasmodGrpcError(PlasmodException):
    """Non-OK gRPC response from a Plasmod server."""

    def __init__(
        self,
        code: int,
        *,
        details: str = "",
        method: str = "",
    ) -> None:
        msg = details or f"gRPC status {code}"
        super().__init__(msg, code=code if code else 1)
        self.grpc_code = code
        self.details = details
        self.method = method

    def __str__(self) -> str:
        return (
            f"<{type(self).__name__}: code={self.grpc_code}, method={self.method!r}, "
            f"details={self.details[:200]!r}>"
        )


def raise_for_rpc_error(exc: BaseException, *, method: str) -> None:
    import grpc

    if not isinstance(exc, grpc.RpcError):
        raise exc
    code = exc.code()
    details = exc.details() or str(exc)
    numeric = int(getattr(code, "value", [0])[0])
    raise PlasmodGrpcError(numeric, details=details, method=method) from exc
