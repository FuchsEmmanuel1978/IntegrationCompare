"""Load integration technology JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_technologies(data_dir: str | Path) -> list[dict[str, Any]]:
    data_dir = Path(data_dir)
    technologies: list[dict[str, Any]] = []
    for path in sorted(data_dir.glob("*.json")):
        if path.name == "constants.json":
            continue
        technologies.append(load_json(path))
    return technologies
