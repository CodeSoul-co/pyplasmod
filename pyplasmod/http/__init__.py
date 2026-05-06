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

"""Plasmod HTTP SDK (JSON Tier A + binary RPC helpers)."""

from pyplasmod.http.binary import (
    decode_query_warm_batch_response,
    decode_query_warm_response,
    encode_ingest_batch,
    encode_query_warm,
    encode_query_warm_batch,
)
from pyplasmod.http.client import PlasmodHttpClient
from pyplasmod.http.errors import PlasmodHttpError

__all__ = [
    "PlasmodHttpClient",
    "PlasmodHttpError",
    "decode_query_warm_batch_response",
    "decode_query_warm_response",
    "encode_ingest_batch",
    "encode_query_warm",
    "encode_query_warm_batch",
]
