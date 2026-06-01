# Copyright (C) 2026 CodeSoul-co.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
import sys
from ctypes import CDLL, c_char_p, c_float, c_int, c_int64, c_void_p
from ctypes.util import find_library
from pathlib import Path
from typing import Optional

_LIB_NAMES = (
    "plasmod_retrieval",
    "libplasmod_retrieval",
)


def find_retrieval_library() -> Optional[Path]:
    """Locate ``libplasmod_retrieval`` built from the Plasmod ``cpp/`` tree."""
    env = os.environ.get("PLASMOD_CPP_LIB_PATH", "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p
        for name in ("libplasmod_retrieval.so", "libplasmod_retrieval.dylib", "plasmod_retrieval.dll"):
            candidate = p / name
            if candidate.is_file():
                return candidate

    here = Path(__file__).resolve()
    for parent in here.parents:
        for rel in (
            "cpp/build/libplasmod_retrieval.so",
            "cpp/build/libplasmod_retrieval.dylib",
            "cpp/build/plasmod_retrieval.dll",
            "cpp/build/Release/plasmod_retrieval.dll",
            "Plasmod/cpp/build/libplasmod_retrieval.so",
            "Plasmod/cpp/build/libplasmod_retrieval.dylib",
            "Plasmod/cpp/build/plasmod_retrieval.dll",
            "Plasmod/cpp/build/Release/plasmod_retrieval.dll",
        ):
            candidate = parent / rel
            if candidate.is_file():
                return candidate

    for name in _LIB_NAMES:
        found = find_library(name)
        if found:
            return Path(found)
    return None


def load_retrieval_library(path: Optional[Path] = None) -> CDLL:
    lib_path = path or find_retrieval_library()
    if lib_path is None:
        raise OSError(
            "libplasmod_retrieval not found. Build Plasmod with `make cpp` and set "
            "PLASMOD_CPP_LIB_PATH to cpp/build, or install a wheel that bundles the library.",
        )
    lib = CDLL(str(lib_path))
    _bind(lib)
    return lib


def _bind(lib: CDLL) -> None:
    lib.plasmod_version.restype = c_char_p

    lib.plasmod_segment_build_with_type.argtypes = [
        c_char_p,
        c_void_p,
        c_int64,
        c_int,
        c_char_p,
        c_int,
        c_int,
        c_int,
        c_int,
        c_char_p,
    ]
    lib.plasmod_segment_build_with_type.restype = c_int

    lib.plasmod_segment_search.argtypes = [
        c_char_p,
        c_void_p,
        c_int64,
        c_int,
        c_void_p,
        c_void_p,
    ]
    lib.plasmod_segment_search.restype = c_int

    lib.plasmod_segment_unload.argtypes = [c_char_p]
    lib.plasmod_segment_unload.restype = c_int
