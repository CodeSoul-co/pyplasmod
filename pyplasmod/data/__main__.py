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

"""CLI for ``pyplasmod.data``: upload (``.fbin``) or query.

Legacy (3 args)::

    python -m pyplasmod.data <dataset> <workspace_id> <path.fbin>

Explicit::

    python -m pyplasmod.data upload <dataset> <workspace_id> <path.fbin>
    python -m pyplasmod.data query <query_text> <workspace_id>

Two-arg shorthand (query)::

    python -m pyplasmod.data <query_text> <workspace_id>
"""

from __future__ import annotations

import argparse
import sys

from pyplasmod.data import build_query_body, upload
from pyplasmod.http.client import PlasmodHttpClient


def _legacy_fixup_argv() -> None:
    av = sys.argv[1:]
    if not av or av[0] in ("-h", "--help", "upload", "query"):
        return
    if len(av) == 2:
        sys.argv = [sys.argv[0], "query"] + av
    elif len(av) >= 3:
        sys.argv = [sys.argv[0], "upload"] + av


def main() -> int:
    _legacy_fixup_argv()
    ap = argparse.ArgumentParser(
        description="pyplasmod.data — upload .fbin or run a structured query against Plasmod."
    )
    sp = ap.add_subparsers(dest="cmd", required=True)

    pu = sp.add_parser("upload", help="Ingest .fbin rows via ingest_event")
    pu.add_argument("dataset", help="Logical dataset name")
    pu.add_argument("workspace_id", help="Plasmod workspace_id")
    pu.add_argument("path", help="Path to .fbin")
    pu.add_argument("--base-url", default=None)
    pu.add_argument("--tenant-id", default="t_demo")
    pu.add_argument("--limit", type=int, default=0)
    pu.add_argument("--dry-run", action="store_true")
    pu.add_argument(
        "--show-progress",
        action="store_true",
        help="Redraw a one-line progress bar on stderr while uploading",
    )

    pq = sp.add_parser("query", help="POST /v1/query with minimal body")
    pq.add_argument("query_text", help="Query string (e.g. natural language or dataset=...)")
    pq.add_argument("workspace_id", help="Plasmod workspace_id / query_scope")
    pq.add_argument("--base-url", default=None)
    pq.add_argument("--tenant-id", default="t_demo")
    pq.add_argument("--top-k", type=int, default=10)
    pq.add_argument("--dataset-name", default="", help="Optional dataset_name filter")

    args = ap.parse_args()
    try:
        if args.cmd == "upload":
            n = upload(
                args.dataset,
                args.workspace_id,
                args.path,
                tenant_id=args.tenant_id,
                base_url=args.base_url,
                limit=args.limit,
                dry_run=args.dry_run,
                show_progress=args.show_progress,
            )
            print(f"[pyplasmod.data] done: {n} row(s)" + (" (dry-run)" if args.dry_run else ""))
        else:
            c = PlasmodHttpClient(base_url=args.base_url or "http://127.0.0.1:8080")
            body = build_query_body(
                args.query_text,
                args.workspace_id,
                tenant_id=args.tenant_id,
                top_k=args.top_k,
                dataset_name=args.dataset_name or None,
            )
            out = c.query(body)
            print(out)
            print("[pyplasmod.data] query ok")
    except (OSError, ValueError) as e:
        print(e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
