"""Cost model for package-level comparison.

The model is deliberately simple. It is meant for scenario comparison,
not as a qualified quotation model.
"""

from __future__ import annotations

from typing import Any

from .yield_model import compute_total_yield


def _wafer_to_package_cost(cost_per_wafer: float, package_area_mm2: float, constants: dict[str, Any]) -> float:
    wafer = constants["wafer"]
    usable_wafer_area = wafer["area_mm2"] * wafer["edge_loss_factor"]
    packages_per_wafer = max(usable_wafer_area / package_area_mm2, 1.0)
    return cost_per_wafer / packages_per_wafer


def compute_die_cost(technology: dict[str, Any]) -> float:
    cost_model = technology.get("cost_model", {})
    total = 0.0

    total += cost_model.get("logic_die_cost_usd", 0.0) * cost_model.get("num_logic_dies", technology.get("geometry", {}).get("num_logic_dies", 1))
    total += cost_model.get("memory_package_cost_usd", 0.0) * cost_model.get("num_memory_packages", 0)
    total += cost_model.get("hbm_stack_cost_usd", 0.0) * cost_model.get("num_hbm_stacks", 0)
    total += cost_model.get("sram_die_cost_usd", 0.0) * cost_model.get("num_sram_cache_dies", 0)

    return total


def compute_process_cost(technology: dict[str, Any], constants: dict[str, Any]) -> float:
    geometry = technology.get("geometry", {})
    package_area = geometry.get("package_area_mm2", geometry.get("substrate_area_mm2", 1.0))

    total = 0.0
    for step in technology.get("process_flow", []):
        if "cost_usd_per_package" in step:
            total += float(step["cost_usd_per_package"])
        if "cost_usd_per_die" in step:
            total += float(step["cost_usd_per_die"]) * float(step.get("num_dies", 1))
        if "cost_usd_per_wafer" in step:
            total += _wafer_to_package_cost(float(step["cost_usd_per_wafer"]), package_area, constants)
        if "cost_usd_per_layer_per_wafer" in step:
            layer_cost = float(step["cost_usd_per_layer_per_wafer"]) * float(step.get("layers", 1))
            total += _wafer_to_package_cost(layer_cost, package_area, constants)

    return total


def compute_raw_cost(technology: dict[str, Any], constants: dict[str, Any]) -> float:
    cost_model = technology.get("cost_model", {})
    total = 0.0
    total += compute_die_cost(technology)
    total += cost_model.get("interposer_base_cost_usd", 0.0)
    total += cost_model.get("substrate_cost_usd", 0.0)
    total += cost_model.get("assembly_base_cost_usd", 0.0)
    total += cost_model.get("test_cost_usd", 0.0)
    total += compute_process_cost(technology, constants)
    return total


def compute_yield_adjusted_cost(technology: dict[str, Any], constants: dict[str, Any]) -> float:
    raw_cost = compute_raw_cost(technology, constants)
    total_yield = compute_total_yield(technology)
    if total_yield <= 0:
        raise ValueError("Total yield must be positive")
    return raw_cost / total_yield
