from pathlib import Path
import json
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch


def _box(ax, x, y, w, h, label, fontsize=9, alpha=0.95, hatch=None):
    """Draw a labeled rectangle."""
    rect = Rectangle((x, y), w, h, linewidth=1.2, edgecolor="black",
                     facecolor="white", alpha=alpha, hatch=hatch)
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fontsize, wrap=True)
    return rect


def _rounded_box(ax, x, y, w, h, label, fontsize=9):
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.2,
        edgecolor="black",
        facecolor="white"
    )
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fontsize, wrap=True)
    return rect


def _vias(ax, xs, y0, y1, label=None):
    for x in xs:
        ax.plot([x, x], [y0, y1], linewidth=2.0)
    if label:
        ax.text(sum(xs) / len(xs), (y0 + y1) / 2, label,
                ha="center", va="center", fontsize=8,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black"))


def _micro_bumps(ax, xs, y, radius=0.045, label=None):
    for x in xs:
        circ = plt.Circle((x, y), radius, fill=False, linewidth=1.1)
        ax.add_patch(circ)
    if label:
        ax.text(sum(xs) / len(xs), y + 0.18, label,
                ha="center", va="bottom", fontsize=8)


def _draw_scale_notes(ax, data, x, y):
    g = data.get("geometry", {})
    perf = data.get("performance_model", {})
    notes = [
        f"Package: {g.get('package_area_mm2', 'NA')} mm²",
        f"RDL layers: {g.get('rdl_layers', 'NA')}",
        f"Pitch: {g.get('interconnect_pitch_um', 'NA')} µm",
        f"Bandwidth: {perf.get('bandwidth_tb_s', 'NA')} TB/s",
        f"Energy/bit: {perf.get('energy_pj_per_bit', 'NA')} pJ/bit",
        f"Rth: {perf.get('thermal_resistance_k_per_w', 'NA')} K/W",
    ]
    ax.text(x, y, "\n".join(notes), ha="left", va="top", fontsize=8,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="black"))


def draw_2d_sip(data, output_path):
    fig, ax = plt.subplots(figsize=(12, 6))

    # Substrate and board-like view
    _box(ax, 0.6, 0.7, 10.8, 0.55, "PCB / board side", fontsize=9)
    _box(ax, 1.0, 1.25, 10.0, 0.75, "Organic package substrate\nlarge routing pitch, long lateral links", fontsize=10)

    # C4 bumps
    _micro_bumps(ax, [2.0, 2.4, 2.8, 6.0, 6.4, 6.8, 9.2, 9.6], 2.05, label="C4 bumps / solder balls")

    # Dies side-by-side
    _box(ax, 1.5, 2.15, 2.2, 1.0, "Logic die\nCPU/GPU/ASIC", fontsize=10)
    _box(ax, 5.4, 2.15, 1.8, 0.85, "Memory die\nor chiplet", fontsize=10)
    _box(ax, 8.5, 2.15, 1.8, 0.85, "I/O chiplet\nanalog/RF/SerDes", fontsize=10)

    # Lateral routing
    ax.annotate("", xy=(5.4, 2.65), xytext=(3.7, 2.65), arrowprops=dict(arrowstyle="<->", lw=1.5))
    ax.annotate("", xy=(8.5, 2.60), xytext=(7.2, 2.60), arrowprops=dict(arrowstyle="<->", lw=1.5))
    ax.text(4.55, 2.85, "longer package traces", ha="center", fontsize=8)
    ax.text(7.85, 2.82, "substrate routing", ha="center", fontsize=8)

    # Labels
    ax.text(6.0, 4.35, "2.0D / SiP on organic substrate", ha="center", fontsize=16, weight="bold")
    ax.text(6.0, 3.95, "Mature, lower cost, no silicon interposer, no TSV, lower interconnect density",
            ha="center", fontsize=10)
    _draw_scale_notes(ax, data, 0.7, 5.15)

    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5.6)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def draw_25d_interposer(data, output_path):
    fig, ax = plt.subplots(figsize=(12, 6.5))

    _box(ax, 0.5, 0.55, 11.0, 0.50, "PCB / board side", fontsize=9)
    _box(ax, 1.0, 1.05, 10.0, 0.65, "Organic package substrate", fontsize=10)

    # C4 between interposer and substrate
    _micro_bumps(ax, [2.0, 2.4, 2.8, 5.4, 5.8, 6.2, 8.8, 9.2, 9.6], 1.82, label="C4 bumps")

    # Silicon interposer
    _box(ax, 1.2, 1.95, 9.6, 0.95, "Silicon interposer\nfine RDL + TSV", fontsize=11, hatch="//")

    # TSVs
    _vias(ax, [2.0, 2.5, 3.0, 5.8, 6.3, 8.9, 9.4], 1.95, 2.90, label="TSV")

    # Microbumps
    _micro_bumps(ax, [2.1, 2.4, 2.7, 3.0, 4.8, 5.1, 5.4, 6.8, 7.1, 7.4, 8.8, 9.1], 3.02,
                 label="micro-bumps, fine pitch")

    # Logic and HBMs
    _box(ax, 1.6, 3.15, 2.2, 1.05, "Large logic die\nGPU / accelerator", fontsize=10)
    _box(ax, 4.6, 3.15, 1.2, 0.95, "HBM\nstack", fontsize=10)
    _box(ax, 6.4, 3.15, 1.2, 0.95, "HBM\nstack", fontsize=10)
    _box(ax, 8.2, 3.15, 1.2, 0.95, "HBM\nstack", fontsize=10)

    # RDL traces
    ax.annotate("", xy=(4.6, 2.55), xytext=(3.8, 2.55), arrowprops=dict(arrowstyle="<->", lw=1.5))
    ax.annotate("", xy=(6.4, 2.55), xytext=(5.8, 2.55), arrowprops=dict(arrowstyle="<->", lw=1.5))
    ax.annotate("", xy=(8.2, 2.55), xytext=(7.6, 2.55), arrowprops=dict(arrowstyle="<->", lw=1.5))
    ax.text(6.1, 2.25, "short dense interposer RDL links", ha="center", fontsize=8)

    ax.text(6.0, 5.15, "2.5D / TSV silicon interposer", ha="center", fontsize=16, weight="bold")
    ax.text(6.0, 4.75, "High bandwidth GPU + HBM style integration, high density, higher cost, TSV interposer",
            ha="center", fontsize=10)
    _draw_scale_notes(ax, data, 0.7, 6.05)

    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6.4)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def draw_3d_hybrid_bonding(data, output_path):
    fig, ax = plt.subplots(figsize=(12, 7))

    _box(ax, 0.7, 0.55, 10.6, 0.50, "PCB / board side", fontsize=9)
    _box(ax, 1.2, 1.05, 9.6, 0.60, "Organic substrate", fontsize=10)
    _micro_bumps(ax, [2.4, 2.8, 3.2, 5.8, 6.2, 6.6, 9.0, 9.4], 1.78, label="C4 bumps")

    _box(ax, 2.0, 1.95, 8.0, 0.65, "Base die / active interposer\npower delivery + global routing", fontsize=10)
    _vias(ax, [2.7, 3.1, 5.8, 6.2, 8.9, 9.3], 1.95, 2.60, label="TSV / backside vias")

    # Hybrid bonding interface
    _micro_bumps(ax, [3.0, 3.25, 3.5, 4.8, 5.05, 5.3, 6.6, 6.85, 7.1, 8.3, 8.55, 8.8], 2.78,
                 radius=0.03, label="hybrid bonding Cu-Cu + oxide-oxide, very fine pitch")

    # Vertical stack
    _box(ax, 2.4, 2.90, 2.0, 0.8, "Compute tile\nlogic tier 1", fontsize=9)
    _box(ax, 2.55, 3.72, 1.7, 0.65, "SRAM / cache\ntier 2", fontsize=9)
    _box(ax, 2.7, 4.39, 1.4, 0.55, "logic / memory\ntier 3", fontsize=8)

    _box(ax, 5.1, 2.90, 1.8, 0.8, "Compute tile\nlogic tier 1", fontsize=9)
    _box(ax, 5.25, 3.72, 1.5, 0.65, "SRAM / cache\ntier 2", fontsize=9)

    _box(ax, 7.7, 2.90, 1.6, 0.8, "I/O or memory\ntile", fontsize=9)
    _box(ax, 7.85, 3.72, 1.3, 0.65, "stacked\nmemory", fontsize=9)

    # Thermal arrows
    ax.annotate("thermal path\nmore difficult",
                xy=(3.4, 4.95), xytext=(3.4, 5.85),
                arrowprops=dict(arrowstyle="->", lw=1.5),
                ha="center", fontsize=9)
    ax.annotate("vertical links\nshort and dense",
                xy=(6.0, 3.75), xytext=(6.0, 5.55),
                arrowprops=dict(arrowstyle="->", lw=1.5),
                ha="center", fontsize=9)

    ax.text(6.0, 6.45, "3D / Hybrid bonding + TSV", ha="center", fontsize=16, weight="bold")
    ax.text(6.0, 6.05, "Maximum vertical interconnect density, short links, critical alignment/CMP/yield/thermal constraints",
            ha="center", fontsize=10)
    _draw_scale_notes(ax, data, 0.7, 6.65)

    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.0)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def load_json_files(data_dir):
    data_dir = Path(data_dir)
    files = sorted(data_dir.glob("*.json"))
    integrations = []
    for file in files:
        if file.name == "constants.json":
            continue
        with open(file, "r", encoding="utf-8") as f:
            integrations.append(json.load(f))
    return integrations


def draw_packaging_from_json(data, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    name = data.get("name", "integration").lower()
    integration_type = data.get("integration_type", "").lower()

    if "2.0" in integration_type or "2d" in integration_type or "organic" in name:
        out = output_dir / "packaging_2d_sip.png"
        draw_2d_sip(data, out)
    elif "2.5" in integration_type or "interposer" in name:
        out = output_dir / "packaging_25d_tsv_interposer.png"
        draw_25d_interposer(data, out)
    elif "3d" in integration_type or "hybrid" in name:
        out = output_dir / "packaging_3d_hybrid_bonding_tsv.png"
        draw_3d_hybrid_bonding(data, out)
    else:
        out = output_dir / f"packaging_{name}.png"
        draw_2d_sip(data, out)

    return out


def draw_all_packaging(data_dir="data", output_dir="outputs/figures"):
    integrations = load_json_files(data_dir)
    outputs = []
    for data in integrations:
        outputs.append(draw_packaging_from_json(data, output_dir))
    return outputs
