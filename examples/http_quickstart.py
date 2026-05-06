"""Minimal Plasmod HTTP client usage (requires a running Plasmod server)."""

from __future__ import annotations

from pyplasmod import PlasmodClient


def main() -> None:
    client = PlasmodClient(base_url="http://127.0.0.1:8080")
    print(client.health())


if __name__ == "__main__":
    main()
