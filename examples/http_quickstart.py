"""Minimal Plasmod HTTP client usage (requires a running Plasmod server)."""

from __future__ import annotations

import os

from pyplasmod import PlasmodClient


def main() -> None:
    base = os.environ.get("PLASMOD_BASE_URL", "http://127.0.0.1:8080")
    client = PlasmodClient(base_url=base)
    print("health:", client.health())
    if os.environ.get("PLASMOD_QUICKSTART_ADMIN", "").strip() in ("1", "true", "yes"):
        key = os.environ.get("PLASMOD_ADMIN_API_KEY") or os.environ.get("ANDB_ADMIN_API_KEY") or ""
        if not key:
            print("PLASMOD_QUICKSTART_ADMIN set but no PLASMOD_ADMIN_API_KEY — skip admin_topology_get")
            return
        admin_client = PlasmodClient(base_url=base, admin_key=key)
        print("admin topology:", admin_client.admin_topology_get())


if __name__ == "__main__":
    main()
