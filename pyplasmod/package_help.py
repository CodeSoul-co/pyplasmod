# Copyright (c) 2026 CodeSoul-co
#
# Licensed under the MIT License. See LICENSE in the repository root.

"""Package-level help index; detailed API text lives in docstrings (use ``help(obj)``)."""

from __future__ import annotations

import importlib
import sys
import textwrap
from typing import Optional, TextIO


def _topic_entries() -> list[tuple[str, str, Optional[object], str]]:
    """name, one-line blurb, object for ``help()`` or None, how to open ``help`` in REPL."""
    from pyplasmod.data import build_query_body, upload
    from pyplasmod.easy import EasyPlasmod
    from pyplasmod.embedding import PlasmodEmbedding
    from pyplasmod.http.client import PlasmodHttpClient
    from pyplasmod.http.errors import PlasmodHttpError

    binary = importlib.import_module("pyplasmod.http.binary")
    return [
        (
            "embedding",
            "Gateway-side embeddings: PlasmodEmbedding (ingest/search/runtime, use_cpu/use_gpu).",
            PlasmodEmbedding,
            "from pyplasmod import PlasmodEmbedding; help(PlasmodEmbedding)",
        ),
        (
            "easy",
            "Convenience API: health, search/query, ingest, upload_fbin, memories; full HTTP via .http.",
            EasyPlasmod,
            "from pyplasmod import EasyPlasmod; help(EasyPlasmod)",
        ),
        (
            "client",
            "Full HTTP client (alias PlasmodClient): ingest, query, admin, RPC, etc.",
            PlasmodHttpClient,
            "from pyplasmod import PlasmodHttpClient; help(PlasmodHttpClient)",
        ),
        (
            "upload",
            "Upload .fbin rows as ingest_event POSTs (optional client= for connection reuse).",
            upload,
            "from pyplasmod.data import upload; help(upload)",
        ),
        (
            "querybody",
            "Build POST /v1/query JSON only (no HTTP); pair with client.query or EasyPlasmod.query.",
            build_query_body,
            "from pyplasmod.data import build_query_body; help(build_query_body)",
        ),
        (
            "errors",
            "PlasmodHttpError on HTTP failures (status_code, path, body).",
            PlasmodHttpError,
            "from pyplasmod import PlasmodHttpError; help(PlasmodHttpError)",
        ),
        (
            "binary",
            "PLIB/PLQW/PLQB encode/decode; prefer PlasmodHttpClient.rpc_* in most apps.",
            binary,
            "import pyplasmod.http.binary as b; help(b)",
        ),
    ]


def plasmod_topics() -> list[str]:
    """Sorted topic keys understood by :func:`plasmod_help`."""
    names = [t[0] for t in _topic_entries()]
    names.append("env")
    return sorted(names)


def _print_env(*, file: TextIO) -> None:
    text = """\
    Client environment variables
      PLASMOD_BASE_URL / ANDB_BASE_URL   Gateway root URL (default http://127.0.0.1:8080)
      PLASMOD_HTTP_TIMEOUT / ANDB_HTTP_TIMEOUT   Seconds (default 30)
      PLASMOD_ADMIN_API_KEY / ANDB_ADMIN_API_KEY   Sent as X-Admin-Key for /v1/admin/*

    Plasmod gateway process (embedding CPU/GPU)
      PLASMOD_EMBEDDER              tfidf | onnx | gguf | tensorrt | openai | …
      PLASMOD_EMBEDDER_DEVICE       cpu | cuda | metal (onnx/gguf)
      PLASMOD_EMBEDDER_DIM          Vector dimension (must match the model)
      PLASMOD_EMBEDDER_MODEL_PATH   Local .onnx / .gguf / .engine path
      PLASMOD_ONNX_VOCAB_PATH       Optional ONNX BERT vocab

    Capability table: from pyplasmod import format_capability_table; print(format_capability_table())
    """
    print(textwrap.dedent(text).rstrip(), file=file)


def plasmod_help(
    topic: Optional[str] = None,
    *,
    file: TextIO = sys.stdout,
) -> None:
    """
    Print a short topic index or a single topic blurb.

    For full signatures and parameters, use the built-in ``help()`` on the
    symbol shown (same text as in the CPython standard library).

    Examples::

        from pyplasmod import plasmod_help
        plasmod_help()           # index
        plasmod_help("easy")
        plasmod_help("env")      # environment variables only

    CLI::

        python -m pyplasmod
        python -m pyplasmod easy
    """
    raw = (topic or "").strip().lower()
    aliases = {
        "plasmodclient": "client",
        "httpclient": "client",
        "plasmodhttpclient": "client",
        "fbin": "upload",
        "ingest": "upload",
        "dataset": "client",
        "admin": "client",
    }
    key = aliases.get(raw, raw)

    if key in ("", "index", "topics", "list"):
        print("pyplasmod — topic index (use Python help() for full API docs)\n", file=file)
        for name, blurb, _obj, how in _topic_entries():
            print(f"  {name:<14}{blurb}", file=file)
            print(f"                → {how}", file=file)
        print("  env           Print environment variable reference only.", file=file)
        print("                → plasmod_help('env')", file=file)
        print(
            "\nUsage: plasmod_help('easy')  —  or: python -m pyplasmod [topic]\n"
            "Built-in docs: from pyplasmod import EasyPlasmod; help(EasyPlasmod)",
            file=file,
        )
        return

    if key == "env":
        _print_env(file=file)
        return

    embed = frozenset({"easy", "upload", "querybody", "errors", "binary", "embedding"})

    for name, blurb, obj, how in _topic_entries():
        if key == name:
            print(f"Topic: {name}\n", file=file)
            print(textwrap.fill(blurb, width=88), file=file)
            print(f"\nIn the REPL: {how}\n", file=file)
            if obj is not None and name in embed:
                print("— built-in help() output —\n", file=file)
                import pydoc

                pydoc.doc(obj, title="%s", output=file)
            elif name == "client":
                print(
                    "Tip: PlasmodHttpClient has many methods; run the help() command above to page through them.\n",
                    file=file,
                )
            print(file=file)
            return

    print(f"Unknown topic {topic!r}. Available: {', '.join(plasmod_topics())}", file=file)


__all__ = ["plasmod_help", "plasmod_topics"]
