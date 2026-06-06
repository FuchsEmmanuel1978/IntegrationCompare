"""Simple performance scoring helpers."""

from __future__ import annotations

from typing import Any


def compute_performance_score(technology: dict[str, Any]) -> float:
    perf = technology.get("performance_model", {})
    bandwidth = float(perf.get("bandwidth_tb_s", 0.0))
    energy = max(float(perf.get("energy_pj_per_bit", 1.0)), 1e-9)
    thermal = max(float(perf.get("thermal_resistance_k_per_w", 1.0)), 1e-9)
    latency = max(float(perf.get("latency_ns", 1.0)), 1e-9)

    # Higher is better. This is a relative indicator, not a physical law.
    return bandwidth / energy / thermal / latency


def compute_cost_per_bandwidth(cost_usd: float, technology: dict[str, Any]) -> float:
    bandwidth = float(technology.get("performance_model", {}).get("bandwidth_tb_s", 0.0))
    if bandwidth <= 0:
        return float("inf")
    return cost_usd / bandwidth


def compute_co2e_per_bandwidth(co2e_kg: float, technology: dict[str, Any]) -> float:
    bandwidth = float(technology.get("performance_model", {}).get("bandwidth_tb_s", 0.0))
    if bandwidth <= 0:
        return float("inf")
    return co2e_kg / bandwidth
