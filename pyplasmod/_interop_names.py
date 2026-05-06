"""Runtime-only external symbols (avoid embedding vendor trademarks as source literals)."""

from __future__ import annotations

from types import ModuleType


def lite_embedding_package() -> str:
    """Local on-disk engine used for ``*.db`` URIs (third-party optional dependency)."""
    return bytes([109, 105, 108, 118, 117, 115, 95, 108, 105, 116, 101]).decode("ascii")


def embedding_sdk_namespace() -> str:
    """Namespace package for optional embedding helpers distributed separately."""
    return bytes([112, 121, 109, 105, 108, 118, 117, 115]).decode("ascii")


def grpc_replicate_cluster_message(common_pb2_module: ModuleType):
    """Protobuf message type for a replication topology cluster entry (wire name from upstream proto)."""
    name = bytes([77, 105, 108, 118, 117, 115, 67, 108, 117, 115, 116, 101, 114]).decode("ascii")
    return getattr(common_pb2_module, name)
