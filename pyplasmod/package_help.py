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
            "网关侧嵌入：PlasmodEmbedding（ingest/search/runtime、use_cpu/use_gpu）。",
            PlasmodEmbedding,
            "from pyplasmod import PlasmodEmbedding; help(PlasmodEmbedding)",
        ),
        (
            "easy",
            "精简入口：健康检查、search/query、ingest、upload_fbin、memories；完整 HTTP 用 .http。",
            EasyPlasmod,
            "from pyplasmod import EasyPlasmod; help(EasyPlasmod)",
        ),
        (
            "client",
            "完整 HTTP 客户端（别名 PlasmodClient）：ingest、query、admin、RPC 等。",
            PlasmodHttpClient,
            "from pyplasmod import PlasmodHttpClient; help(PlasmodHttpClient)",
        ),
        (
            "upload",
            "将 .fbin 按行打成 ingest_event 并 POST（可传 client= 复用连接）。",
            upload,
            "from pyplasmod.data import upload; help(upload)",
        ),
        (
            "querybody",
            "只组装 POST /v1/query 的 dict，不发起 HTTP；常与 client.query 或 EasyPlasmod.query 搭配。",
            build_query_body,
            "from pyplasmod.data import build_query_body; help(build_query_body)",
        ),
        (
            "errors",
            "HTTP 失败时抛出 PlasmodHttpError（含 status_code、path、body）。",
            PlasmodHttpError,
            "from pyplasmod import PlasmodHttpError; help(PlasmodHttpError)",
        ),
        (
            "binary",
            "PLIB/PLQW/PLQB 编解码；多数场景直接用 PlasmodHttpClient.rpc_*。",
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
    环境变量（客户端）
      PLASMOD_BASE_URL / ANDB_BASE_URL   服务根 URL，默认 http://127.0.0.1:8080
      PLASMOD_HTTP_TIMEOUT / ANDB_HTTP_TIMEOUT   秒，默认 30
      PLASMOD_ADMIN_API_KEY / ANDB_ADMIN_API_KEY   访问 /v1/admin/* 时自动加 X-Admin-Key

    环境变量（Plasmod 网关进程 — 嵌入 CPU/GPU）
      PLASMOD_EMBEDDER              tfidf | onnx | gguf | tensorrt | openai | …
      PLASMOD_EMBEDDER_DEVICE       cpu | cuda | metal（onnx/gguf 双路径）
      PLASMOD_EMBEDDER_DIM          向量维度，须与模型一致
      PLASMOD_EMBEDDER_MODEL_PATH   本地 .onnx / .gguf / .engine 路径
      PLASMOD_ONNX_VOCAB_PATH       ONNX BERT vocab（可选）

    在 Python 中查看能力表: from pyplasmod import format_capability_table; print(format_capability_table())
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
        print("pyplasmod — 主题索引（详细说明请用 Python 内置 help()）\n", file=file)
        for name, blurb, _obj, how in _topic_entries():
            print(f"  {name:<14}{blurb}", file=file)
            print(f"                → {how}", file=file)
        print("  env           仅打印环境变量说明。", file=file)
        print("                → plasmod_help('env')", file=file)
        print(
            "\n用法: plasmod_help('easy')  —  也可: python -m pyplasmod [主题]\n"
            "内置文档: from pyplasmod import EasyPlasmod; help(EasyPlasmod)",
            file=file,
        )
        return

    if key == "env":
        _print_env(file=file)
        return

    embed = frozenset({"easy", "upload", "querybody", "errors", "binary", "embedding"})

    for name, blurb, obj, how in _topic_entries():
        if key == name:
            print(f"主题: {name}\n", file=file)
            print(textwrap.fill(blurb, width=88), file=file)
            print(f"\n在 REPL 查看完整 API: {how}\n", file=file)
            if obj is not None and name in embed:
                print("— 以下为内置 help() 输出 —\n", file=file)
                import pydoc

                pydoc.doc(obj, title="%s", output=file)
            elif name == "client":
                print(
                    "提示: ``PlasmodHttpClient`` 方法很多，请在 Python 中执行上述 ``help()`` 分页查看。\n",
                    file=file,
                )
            print(file=file)
            return

    print(f"未知主题 {topic!r}。可用主题: {', '.join(plasmod_topics())}", file=file)


__all__ = ["plasmod_help", "plasmod_topics"]
