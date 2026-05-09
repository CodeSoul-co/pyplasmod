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
