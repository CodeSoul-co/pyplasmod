# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""Plasmod gRPC client (``plasmod.v1.PlasmodAPIService``)."""

from pyplasmod.grpc.client import PlasmodGrpcClient
from pyplasmod.grpc.deploy import DEFAULT_GRPC_PORT, DEFAULT_GRPC_TARGET, resolve_grpc_target
from pyplasmod.grpc.errors import PlasmodGrpcError

__all__ = [
    "DEFAULT_GRPC_PORT",
    "DEFAULT_GRPC_TARGET",
    "PlasmodGrpcClient",
    "PlasmodGrpcError",
    "resolve_grpc_target",
]
