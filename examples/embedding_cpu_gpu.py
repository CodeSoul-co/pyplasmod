#!/usr/bin/env python3
"""
Plasmod gateway embedding — simplified API (PlasmodEmbedding).

Run with a live gateway (default http://127.0.0.1:8080):
  export PLASMOD_BASE_URL=http://127.0.0.1:8080
  python examples/embedding_cpu_gpu.py
"""

from __future__ import annotations

import os
import sys

from pyplasmod import EasyPlasmod, PlasmodEmbedding


def demo_presets() -> None:
    print("=== CPU / GPU capability matrix ===\n")
    print(PlasmodEmbedding.capabilities())
    print()

    print("=== Deployment presets (apply before starting Plasmod) ===\n")
    emb = PlasmodEmbedding.connect()
    for label, cfg in [
        ("ONNX CPU", emb.use_onnx_cpu(model_path="/models/model.onnx", dim=384)),
        ("ONNX GPU", emb.use_onnx_gpu(model_path="/models/model.onnx", dim=384)),
        ("GGUF CPU", emb.use_gguf_cpu(model_path="/models/model.gguf", dim=384)),
        ("GGUF GPU", emb.use_gguf_gpu(model_path="/models/model.gguf", dim=384)),
    ]:
        print(f"  {label}: {cfg.summary()}")
    emb.close()
    print()


def demo_live() -> None:
    base = os.environ.get("PLASMOD_BASE_URL", "http://127.0.0.1:8080")
    print(f"=== Live gateway ({base}) ===\n")

    with PlasmodEmbedding.connect() as emb:
        runtime = emb.runtime(workspace_id="w_demo")
        print(f"  runtime: family={runtime.family!r} dim={runtime.dim}")

        # Optional: ingest + search when you have a workspace
        # emb.ingest("示例句子", workspace_id="w_demo")
        # print(emb.search("示例", workspace_id="w_demo", top_k=3))

    print("\n=== Via EasyPlasmod (same embedding API) ===\n")
    with EasyPlasmod() as p:
        print(f"  config: {p.embedding.config().summary()}")
        print(f"  runtime: {p.embedding.runtime(workspace_id='w_demo')}")


def main() -> None:
    demo_presets()
    try:
        demo_live()
    except Exception as exc:
        print(f"  gateway probe failed: {exc}", file=sys.stderr)
        print("  Start Plasmod or set PLASMOD_BASE_URL.", file=sys.stderr)


if __name__ == "__main__":
    main()
