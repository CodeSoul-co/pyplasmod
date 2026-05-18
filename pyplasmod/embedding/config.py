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

"""Plasmod gateway embedder configuration (CPU / GPU dual-path)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Mapping, Optional

EmbedderProvider = Literal[
    "tfidf",
    "openai",
    "zhipuai",
    "cohere",
    "vertexai",
    "huggingface",
    "onnx",
    "gguf",
    "tensorrt",
]

EmbedderDevice = Literal["cpu", "cuda", "metal"]

# Providers with distinct CPU vs GPU implementations in Plasmod (build tags + device env).
LOCAL_DUAL_PATH_PROVIDERS: frozenset[str] = frozenset({"onnx", "gguf", "tensorrt"})

# tensorrt is CUDA-only on the server; gguf/onnx support cpu | cuda | metal (platform-dependent).
GPU_ONLY_PROVIDERS: frozenset[str] = frozenset({"tensorrt"})

REMOTE_HTTP_PROVIDERS: frozenset[str] = frozenset(
    {"openai", "zhipuai", "cohere", "vertexai", "huggingface"}
)


@dataclass(frozen=True)
class EmbedderConfig:
    """
    Describes how a **Plasmod gateway process** should embed text (server-side).

    pyplasmod does not run ONNX/GGUF locally; it documents and applies the same
    ``PLASMOD_EMBEDDER*`` environment variables the Go server reads at bootstrap.
    Use :meth:`apply_to_environ` before starting Plasmod, or pass :meth:`to_environ`
    to your process manager / ``docker-compose``.
    """

    provider: EmbedderProvider = "tfidf"
    device: EmbedderDevice = "cpu"
    dim: Optional[int] = None
    model_path: str = ""
    vocab_path: str = ""
    model: str = ""
    max_batch_size: int = 32
    gpu_layers: int = 0
    cuda_visible_devices: str = ""

    # ── CPU / GPU presets (local inference on the gateway) ─────────────────

    @classmethod
    def onnx_cpu(
        cls,
        *,
        model_path: str,
        dim: int = 384,
        vocab_path: str = "",
        max_batch_size: int = 32,
    ) -> EmbedderConfig:
        """ONNX Runtime on CPU (``go build`` without ``-tags cuda``)."""
        return cls(
            provider="onnx",
            device="cpu",
            dim=dim,
            model_path=model_path,
            vocab_path=vocab_path,
            max_batch_size=max_batch_size,
        )

    @classmethod
    def onnx_cuda(
        cls,
        *,
        model_path: str,
        dim: int = 384,
        vocab_path: str = "",
        max_batch_size: int = 32,
        cuda_visible_devices: str = "0",
    ) -> EmbedderConfig:
        """ONNX Runtime with CUDA execution provider (``go build -tags cuda``)."""
        return cls(
            provider="onnx",
            device="cuda",
            dim=dim,
            model_path=model_path,
            vocab_path=vocab_path,
            max_batch_size=max_batch_size,
            cuda_visible_devices=cuda_visible_devices,
        )

    @classmethod
    def gguf_cpu(
        cls,
        *,
        model_path: str,
        dim: int = 384,
        gpu_layers: int = 0,
    ) -> EmbedderConfig:
        """GGUF via llama.cpp on CPU (``PLASMOD_EMBEDDER_GPU_LAYERS=0``)."""
        return cls(
            provider="gguf",
            device="cpu",
            dim=dim,
            model_path=model_path,
            gpu_layers=gpu_layers,
        )

    @classmethod
    def gguf_cuda(
        cls,
        *,
        model_path: str,
        dim: int = 384,
        gpu_layers: int = 99,
        cuda_visible_devices: str = "0",
    ) -> EmbedderConfig:
        """GGUF with CUDA offload (``go build -tags cuda``)."""
        return cls(
            provider="gguf",
            device="cuda",
            dim=dim,
            model_path=model_path,
            gpu_layers=gpu_layers,
            cuda_visible_devices=cuda_visible_devices,
        )

    @classmethod
    def tensorrt_cuda(
        cls,
        *,
        engine_path: str,
        dim: int = 384,
        vocab_path: str = "",
        cuda_visible_devices: str = "0",
    ) -> EmbedderConfig:
        """TensorRT engine on NVIDIA GPU (CUDA-only provider)."""
        return cls(
            provider="tensorrt",
            device="cuda",
            dim=dim,
            model_path=engine_path,
            vocab_path=vocab_path,
            cuda_visible_devices=cuda_visible_devices,
        )

    @classmethod
    def tfidf(cls, *, dim: int = 256) -> EmbedderConfig:
        """Pure-Go TF-IDF (default Plasmod dev embedder, CPU-only)."""
        return cls(provider="tfidf", device="cpu", dim=dim)

    # ── Capability helpers ───────────────────────────────────────────────────

    def supports_local_device_choice(self) -> bool:
        """True when Plasmod exposes separate CPU and GPU code paths for this provider."""
        return self.provider in LOCAL_DUAL_PATH_PROVIDERS

    def is_gpu_only_provider(self) -> bool:
        return self.provider in GPU_ONLY_PROVIDERS

    def validate_device(self) -> None:
        """Raise ``ValueError`` if *device* is incompatible with *provider*."""
        if self.provider in GPU_ONLY_PROVIDERS and self.device != "cuda":
            raise ValueError(
                f"provider {self.provider!r} requires device='cuda' (got {self.device!r})"
            )
        if self.provider == "tfidf" and self.device not in ("cpu",):
            raise ValueError("tfidf embedder is CPU-only on the gateway")
        if self.provider in REMOTE_HTTP_PROVIDERS and self.device != "cpu":
            # Remote APIs have no local GPU path in Plasmod; device env is ignored.
            pass

    def execution_label(self) -> str:
        """Short label for logs/UI, e.g. ``onnx+cuda``."""
        if self.provider in REMOTE_HTTP_PROVIDERS:
            return f"{self.provider}+remote"
        if self.supports_local_device_choice():
            return f"{self.provider}+{self.device}"
        return self.provider

    # ── Environment mapping ──────────────────────────────────────────────────

    def to_environ(self) -> dict[str, str]:
        """Map this config to Plasmod ``PLASMOD_EMBEDDER*`` variables."""
        self.validate_device()
        env: dict[str, str] = {
            "PLASMOD_EMBEDDER": self.provider,
            "PLASMOD_EMBEDDER_DEVICE": self.device,
        }
        if self.dim is not None:
            env["PLASMOD_EMBEDDER_DIM"] = str(self.dim)
        if self.model_path:
            env["PLASMOD_EMBEDDER_MODEL_PATH"] = self.model_path
        if self.vocab_path:
            env["PLASMOD_ONNX_VOCAB_PATH"] = self.vocab_path
        if self.model:
            env["PLASMOD_EMBEDDER_MODEL"] = self.model
        if self.max_batch_size:
            env["PLASMOD_EMBEDDER_MAX_BATCH_SIZE"] = str(self.max_batch_size)
        if self.gpu_layers or self.provider == "gguf":
            env["PLASMOD_EMBEDDER_GPU_LAYERS"] = str(self.gpu_layers)
        if self.cuda_visible_devices:
            env["CUDA_VISIBLE_DEVICES"] = self.cuda_visible_devices
        return env

    def apply_to_environ(self, *, overwrite: bool = True) -> dict[str, str]:
        """
        Set process environment from :meth:`to_environ`.

        Returns the key/value pairs that were applied.
        """
        applied: dict[str, str] = {}
        for key, value in self.to_environ().items():
            if not overwrite and key in os.environ:
                continue
            os.environ[key] = value
            applied[key] = value
        return applied

    @classmethod
    def from_environ(cls, environ: Optional[Mapping[str, str]] = None) -> EmbedderConfig:
        """Parse current (or supplied) environment into an :class:`EmbedderConfig`."""
        e = os.environ if environ is None else environ
        provider = (e.get("PLASMOD_EMBEDDER") or e.get("ANDB_EMBEDDER") or "tfidf").strip()
        device = (e.get("PLASMOD_EMBEDDER_DEVICE") or e.get("ANDB_EMBEDDER_DEVICE") or "cpu").strip()
        dim_raw = (e.get("PLASMOD_EMBEDDER_DIM") or "").strip()
        dim = int(dim_raw) if dim_raw.isdigit() else None
        gpu_layers_raw = (e.get("PLASMOD_EMBEDDER_GPU_LAYERS") or "").strip()
        gpu_layers = int(gpu_layers_raw) if gpu_layers_raw.lstrip("-").isdigit() else 0
        max_bs_raw = (e.get("PLASMOD_EMBEDDER_MAX_BATCH_SIZE") or "32").strip()
        max_batch_size = int(max_bs_raw) if max_bs_raw.isdigit() else 32
        return cls(
            provider=provider,  # type: ignore[arg-type]
            device=device,  # type: ignore[arg-type]
            dim=dim,
            model_path=(e.get("PLASMOD_EMBEDDER_MODEL_PATH") or "").strip(),
            vocab_path=(e.get("PLASMOD_ONNX_VOCAB_PATH") or "").strip(),
            model=(e.get("PLASMOD_EMBEDDER_MODEL") or "").strip(),
            max_batch_size=max_batch_size,
            gpu_layers=gpu_layers,
            cuda_visible_devices=(e.get("CUDA_VISIBLE_DEVICES") or "").strip(),
        )

    def summary(self) -> str:
        """One-line human-readable description."""
        parts = [f"provider={self.provider}", f"device={self.device}"]
        if self.dim is not None:
            parts.append(f"dim={self.dim}")
        if self.model_path:
            parts.append(f"model_path={self.model_path!r}")
        if self.supports_local_device_choice():
            parts.append("dual_path=onnx|gguf|tensorrt")
        return "EmbedderConfig(" + ", ".join(parts) + ")"


@dataclass(frozen=True)
class ProviderCapability:
    """Documents CPU/GPU support for a Plasmod embedder backend."""

    provider: str
    local_inference: bool
    cpu: bool
    cuda: bool
    metal: bool
    notes: str = ""


# Authoritative matrix aligned with Plasmod ``src/internal/dataplane/embedding/``.
EMBEDDER_CAPABILITIES: tuple[ProviderCapability, ...] = (
    ProviderCapability("tfidf", True, True, False, False, "pure Go, default dev"),
    ProviderCapability("openai", False, True, False, False, "HTTP; includes Ollama/Azure"),
    ProviderCapability("zhipuai", False, True, False, False, "HTTP OpenAI-compatible"),
    ProviderCapability("cohere", False, True, False, False, "HTTP"),
    ProviderCapability("vertexai", False, True, False, False, "HTTP"),
    ProviderCapability("huggingface", False, True, False, False, "HTTP Inference API"),
    ProviderCapability(
        "onnx",
        True,
        True,
        True,
        False,
        "onnx_cpu.go vs onnx_cuda.go; device=cpu|cuda",
    ),
    ProviderCapability(
        "gguf",
        True,
        True,
        True,
        True,
        "gguf_cpu.go / gguf_cuda.go; metal on macOS",
    ),
    ProviderCapability(
        "tensorrt",
        True,
        False,
        True,
        False,
        "CUDA-only; stub without -tags cuda",
    ),
)


def list_embedder_capabilities() -> list[ProviderCapability]:
    """Return the CPU/GPU capability matrix for all built-in providers."""
    return list(EMBEDDER_CAPABILITIES)


def format_capability_table() -> str:
    """ASCII table of provider × {cpu, cuda, metal} for CLI/help."""
    header = f"{'provider':<14} {'local':^5} {'cpu':^5} {'cuda':^5} {'metal':^5}  notes"
    lines = [header, "-" * len(header)]
    for cap in EMBEDDER_CAPABILITIES:
        yn = lambda b: "yes" if b else "—"
        lines.append(
            f"{cap.provider:<14} {yn(cap.local_inference):^5} {yn(cap.cpu):^5} "
            f"{yn(cap.cuda):^5} {yn(cap.metal):^5}  {cap.notes}"
        )
    return "\n".join(lines)
