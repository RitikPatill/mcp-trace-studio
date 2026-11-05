from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class ServerConfig(BaseModel):
    command: str
    args: list[str] = []
    env: dict[str, str] = {}


def load_servers(path: str | Path) -> dict[str, ServerConfig]:
    """Load servers.yaml → {name: ServerConfig}.

    Raises FileNotFoundError if the file does not exist.
    Raises KeyError if the top-level 'servers' key is missing.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"servers config not found: {p}")

    with p.open() as fh:
        data = yaml.safe_load(fh)

    servers_raw: dict = data["servers"]
    return {name: ServerConfig(**cfg) for name, cfg in servers_raw.items()}
