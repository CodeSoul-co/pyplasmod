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

"""Python SDK for Plasmod — HTTP Tier A + binary RPC (Plasmod ``docs/api``)."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from pyplasmod.exceptions import (
    ConnectError,
    ParamError,
    PlasmodException,
    PlasmodUnavailableException,
)
from pyplasmod.easy import EasyPlasmod
from pyplasmod.http import (
    PlasmodHttpClient,
    PlasmodHttpError,
    decode_query_warm_batch_response,
    decode_query_warm_response,
    encode_ingest_batch,
    encode_query_warm,
    encode_query_warm_batch,
)

try:
    __version__ = _pkg_version("pyplasmod")
except PackageNotFoundError:
    __version__ = "0.0.0"

# Align with ``Plasmod/sdk/python/plasmod_sdk`` naming.
PlasmodClient = PlasmodHttpClient

__all__ = [
    "ConnectError",
    "EasyPlasmod",
    "ParamError",
    "PlasmodClient",
    "PlasmodException",
    "PlasmodHttpClient",
    "PlasmodHttpError",
    "PlasmodUnavailableException",
    "__version__",
    "decode_query_warm_batch_response",
    "decode_query_warm_response",
    "encode_ingest_batch",
    "encode_query_warm",
    "encode_query_warm_batch",
]
