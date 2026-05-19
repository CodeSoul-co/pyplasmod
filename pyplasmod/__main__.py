# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

"""``python -m pyplasmod`` — print :func:`pyplasmod.package_help.plasmod_help` index or a topic."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from pyplasmod.package_help import plasmod_help


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m pyplasmod",
        description="Print pyplasmod topic help (use built-in help() in REPL for full API).",
    )
    p.add_argument(
        "topic",
        nargs="?",
        default=None,
        help="Topic name (e.g. easy, client, upload, querybody, env, errors, binary). "
        "Omit to list topics.",
    )
    args = p.parse_args(argv)
    plasmod_help(args.topic, file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
