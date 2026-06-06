"""Simplified package LCA model.

Outputs kgCO2e per good package using material, electricity and yield assumptions.
"""

from __future__ import annotations

from typing import Any

from .yield_model import compute_total_yield


def _wafer_to_package_value(value_per_wafer: float, package_area_mm2: float, constants: dict[str, Any]) -> float:
    wafer = constants["wafer"]
    usable_wafer_area = wafer["area_mm2"] * wafer["edge_loss_factor"]
    packages_per_wafer = max(usable_wafer_area / package_area_mm2, 1.0)
    return value_per_wafer / packages_per_wafer


def compute_material_co2e(technology: dict[str, Any], constants: dict[str, Any]) -> float:
    factors = constants.get("material_co2e_kg_per_kg", {})
    materials = technology.get("materials", {})
    total = 0.0
    for key, mass_kg in materials.items():
        material = key.replace("_kg_per_package", "")
        total += float(mass_kg) * float(factors.get(material, 0.0))
    return total


def compute_process_energy_kwh(technology: dict[str, Any], constants: dict[str, Any]) -> float:
    geometry = technology.get("geometry", {})
    package_area = geometry.get("package_area_mm2", geometry.get("substrate_area_mm2", 1.0))
    total = 0.0

    for step in technology.get("process_flow", []):
        if "energy_kwh_per_package" in step:
            total += float(step["energy_kwh_per_package"])
        if "energy_kwh_per_die" in step:
            total += float(step["energy_kwh_per_die"]) * float(step.get("num_dies", 1))
        if "energy_kwh_per_wafer" in step:
            total += _wafer_to_package_value(float(step["energy_kwh_per_wafer"]), package_area, constants)
        if "energy_kwh_per_layer_per_wafer" in step:
            layer_energy = float(step["energy_kwh_per_layer_per_wafer"]) * float(step.get("layers", 1))
            total += _wafer_to_package_value(layer_energy, package_area, constants)

    total += float(technology.get("lca_model", {}).get("electricity_kwh_per_package_extra", 0.0))
    return total


def compute_process_energy_co2e(technology: dict[str, Any], constants: dict[str, Any]) -> float:
    region = technology.get("lca_model", {}).get("region", "world_default")
    factor = constants.get("electricity_co2e_kg_per_kwh", {}).get(region)
    if factor is None:
        factor = constants.get("electricity_co2e_kg_per_kwh", {}).get("world_default", 0.45)
    return compute_process_energy_kwh(technology, constants) * float(factor)


def compute_raw_co2e(technology: dict[str, Any], constants: dict[str, Any]) -> float:
    return compute_material_co2e(technology, constants) + compute_process_energy_co2e(technology, constants)


def compute_yield_adjusted_co2e(technology: dict[str, Any], constants: dict[str, Any]) -> float:
    total_yield = compute_total_yield(technology)
    if total_yield <= 0:
        raise ValueError("Total yield must be positive")
    return compute_raw_co2e(technology, constants) / total_yield
