#!/usr/bin/env python3
"""Thin wrapper around ``pyplasmod.data.upload`` (see package API + ``python -m pyplasmod.data``)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pyplasmod.data import upload


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest .fbin via pyplasmod.data.upload")
    ap.add_argument(
        "--file",
        type=Path,
        default=Path("/home/yangyongsheng/database/MSTuring-30M-clustered/testQuery10K.fbin"),
    )
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--dataset", default="testQuery10K")
    ap.add_argument("--tenant-id", default="t_demo")
    ap.add_argument("--workspace-id", default="w_demo")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--show-progress",
        action="store_true",
        help="Terminal progress bar on stderr (same as upload(show_progress=True))",
    )
    args = ap.parse_args()
    try:
        n = upload(
            args.dataset,
            args.workspace_id,
            args.file,
            tenant_id=args.tenant_id,
            base_url=args.base_url,
            limit=args.limit,
            dry_run=args.dry_run,
            show_progress=args.show_progress,
        )
    except (OSError, ValueError) as e:
        print(e, file=sys.stderr)
        return 2
    print(f"[ingest_fbin] done: {n} row(s)" + (" (dry-run)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
