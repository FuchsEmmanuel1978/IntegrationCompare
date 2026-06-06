"""Run comparison between all JSON integration scenarios."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from .cost_model import compute_raw_cost, compute_yield_adjusted_cost
from .lca_model import compute_process_energy_kwh, compute_raw_co2e, compute_yield_adjusted_co2e
from .loader import load_json, load_technologies
from .performance_model import compute_co2e_per_bandwidth, compute_cost_per_bandwidth, compute_performance_score
from .yield_model import compute_total_yield


def summarize(technology: dict[str, Any], constants: dict[str, Any]) -> dict[str, Any]:
    raw_cost = compute_raw_cost(technology, constants)
    good_cost = compute_yield_adjusted_cost(technology, constants)
    raw_co2e = compute_raw_co2e(technology, constants)
    good_co2e = compute_yield_adjusted_co2e(technology, constants)
    perf = technology.get("performance_model", {})
    geometry = technology.get("geometry", {})

    return {
        "name": technology.get("name"),
        "type": technology.get("integration_type"),
        "package_area_mm2": geometry.get("package_area_mm2"),
        "interconnect_pitch_um": geometry.get("interconnect_pitch_um"),
        "tsv_count": geometry.get("tsv_count"),
        "hybrid_bond_pads": geometry.get("hybrid_bond_pads"),
        "total_yield": round(compute_total_yield(technology), 4),
        "raw_cost_usd": round(raw_cost, 2),
        "yield_adjusted_cost_usd": round(good_cost, 2),
        "raw_co2e_kg": round(raw_co2e, 3),
        "yield_adjusted_co2e_kg": round(good_co2e, 3),
        "energy_kwh_per_package_raw": round(compute_process_energy_kwh(technology, constants), 3),
        "bandwidth_tb_s": perf.get("bandwidth_tb_s"),
        "energy_pj_per_bit": perf.get("energy_pj_per_bit"),
        "latency_ns": perf.get("latency_ns"),
        "thermal_resistance_k_per_w": perf.get("thermal_resistance_k_per_w"),
        "performance_score": round(compute_performance_score(technology), 4),
        "cost_per_tb_s_usd": round(compute_cost_per_bandwidth(good_cost, technology), 2),
        "co2e_per_tb_s_kg": round(compute_co2e_per_bandwidth(good_co2e, technology), 3)
    }


def write_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_table(rows: list[dict[str, Any]]) -> None:
    headers = ["name", "total_yield", "yield_adjusted_cost_usd", "yield_adjusted_co2e_kg", "bandwidth_tb_s", "energy_pj_per_bit", "performance_score"]
    widths = {h: max(len(h), *(len(str(row[h])) for row in rows)) for h in headers}
    print(" | ".join(h.ljust(widths[h]) for h in headers))
    print("-+-".join("-" * widths[h] for h in headers))
    for row in rows:
        print(" | ".join(str(row[h]).ljust(widths[h]) for h in headers))


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare 2.0D, 2.5D and 3D integration scenarios.")
    parser.add_argument("--data-dir", default="data", help="Directory containing technology JSON files")
    parser.add_argument("--constants", default="data/constants.json", help="Path to constants JSON")
    parser.add_argument("--output", default="outputs/results.csv", help="CSV output path")
    args = parser.parse_args()

    constants = load_json(args.constants)
    technologies = load_technologies(args.data_dir)
    rows = [summarize(technology, constants) for technology in technologies]
    rows.sort(key=lambda row: row["type"])

    print_table(rows)
    write_csv(rows, Path(args.output))
    print(f"\nResults written to {args.output}")


if __name__ == "__main__":
    main()
