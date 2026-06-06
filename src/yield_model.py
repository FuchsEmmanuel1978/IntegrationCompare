"""Simple multiplicative yield model."""

from __future__ import annotations

from math import prod
from typing import Any


def compute_total_yield(technology: dict[str, Any]) -> float:
    yields = technology.get("yield_model", {})
    if not yields:
        return 1.0
    return prod(float(value) for value in yields.values())


def compute_yield_loss_factor(technology: dict[str, Any]) -> float:
    total_yield = compute_total_yield(technology)
    if total_yield <= 0:
        raise ValueError(f"Invalid yield for {technology.get('name', 'unknown')}: {total_yield}")
    return 1.0 / total_yield
