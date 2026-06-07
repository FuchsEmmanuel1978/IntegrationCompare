from pathlib import Path
import json
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Ellipse, Polygon, Patch
from matplotlib.transforms import Affine2D


# ============================================================
# Generic helpers
# ============================================================

def _nested_get(data, path, default=None):
    obj = data
    for key in path:
        if not isinstance(obj, dict) or key not in obj:
            return default
        obj = obj[key]
    return obj


def _param(data, key, default):
    """
    Read packaging parameter from:
      data["stack"][key]
      data["cross_section"][key]
      data["geometry"][key]
    in that order.
    """
    for root in ("stack", "cross_section", "geometry"):
        val = _nested_get(data, [root, key], None)
        if val is not None:
            return val
    return default


def _box(ax, x, y, w, h, label, fontsize=9, alpha=0.95, hatch=None,
         facecolor="white", edgecolor="black", lw=1.2):
    rect = Rectangle(
        (x, y), w, h,
        linewidth=lw, edgecolor=edgecolor,
        facecolor=facecolor, alpha=alpha, hatch=hatch
    )
    ax.add_patch(rect)
    if label:
        ax.text(
            x + w / 2, y + h / 2, label,
            ha="center", va="center",
            fontsize=fontsize, wrap=True
        )
    return rect


def _rounded_box(ax, x, y, w, h, label, fontsize=9, facecolor="white"):
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        linewidth=1.2,
        edgecolor="black",
        facecolor=facecolor
    )
    ax.add_patch(rect)
    ax.text(
        x + w / 2, y + h / 2, label,
        ha="center", va="center",
        fontsize=fontsize, wrap=True
    )
    return rect


def _draw_notes(ax, data, x, y):
    g = data.get("geometry", {})
    perf = data.get("performance_model", {})
    notes = [
        f"Package area: {g.get('package_area_mm2', 'NA')} mm²",
        f"RDL layers: {g.get('rdl_layers', 'NA')}",
        f"Interconnect pitch: {g.get('interconnect_pitch_um', 'NA')} µm",
        f"TSV count: {g.get('tsv_count', 'NA')}",
        f"Bandwidth: {perf.get('bandwidth_tb_s', 'NA')} TB/s",
        f"Energy/bit: {perf.get('energy_pj_per_bit', 'NA')} pJ/bit",
        f"Thermal R: {perf.get('thermal_resistance_k_per_w', 'NA')} K/W",
        "Vertical thicknesses are approximately to scale (µm).",
        "Horizontal size remains schematic."
    ]
    ax.text(
        x, y, "\n".join(notes),
        ha="left", va="top", fontsize=8,
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="black")
    )


def _draw_dimension_arrow(ax, x, y0, y1, text, fontsize=8):
    ax.annotate(
        "",
        xy=(x, y0), xytext=(x, y1),
        arrowprops=dict(arrowstyle="<->", lw=1.0)
    )
    ax.text(
        x + 0.08, (y0 + y1) / 2,
        text,
        rotation=90,
        ha="left", va="center",
        fontsize=fontsize
    )


def _draw_layer(ax, x, y, w, h, label, color, fontsize=8, hatch=None, alpha=1.0):
    return _box(
        ax, x, y, w, h,
        label=label,
        fontsize=fontsize,
        hatch=hatch,
        facecolor=color,
        alpha=alpha
    )


# ============================================================
# Primitive cross-section elements
# ============================================================

def _draw_solder_balls(ax, xs, y_base, width=0.34, height=0.24, label=None):
    """
    Large solder balls between substrate and PCB.
    """
    for x in xs:
        ell = Ellipse(
            (x, y_base + height / 2),
            width=width, height=height,
            facecolor="#b5b5b5", edgecolor="black", linewidth=1.0
        )
        ax.add_patch(ell)
    if label:
        ax.text(
            sum(xs) / len(xs), y_base - 0.10,
            label,
            ha="center", va="top", fontsize=8
        )


def _draw_c4_bumps(ax, xs, y_base, width=0.24, height=0.14, label=None):
    """
    C4 bump style (rounded solder bump).
    """
    for x in xs:
        ell = Ellipse(
            (x, y_base + height / 2),
            width=width, height=height,
            facecolor="#d9d9d9", edgecolor="black", linewidth=1.0
        )
        ax.add_patch(ell)
    if label:
        ax.text(
            sum(xs) / len(xs), y_base + height + 0.06,
            label,
            ha="center", va="bottom", fontsize=8
        )


def _draw_micro_bumps(ax, xs, y_base, width=0.12, height=0.08, label=None):
    """
    µBump / Cu pillar style:
      - Cu pillar
      - small solder cap
    """
    for x in xs:
        pillar_w = width * 0.70
        pillar_x = x - pillar_w / 2
        pillar = Rectangle(
            (pillar_x, y_base), pillar_w, height * 0.70,
            facecolor="#f2b36d", edgecolor="black", linewidth=0.9
        )
        cap = Ellipse(
            (x, y_base + height * 0.78),
            width=width, height=height * 0.45,
            facecolor="#f48a8a", edgecolor="black", linewidth=0.9
        )
        ax.add_patch(pillar)
        ax.add_patch(cap)
    if label:
        ax.text(
            sum(xs) / len(xs), y_base + height + 0.05,
            label,
            ha="center", va="bottom", fontsize=8
        )


def _draw_tsvs(ax, x0, y0, w, h, count=5, label=None, color="#f28e2b"):
    """
    Copper-filled TSVs inside silicon.
    """
    if count <= 0:
        return

    margin = w * 0.10
    usable = max(w - 2 * margin, 0.2)
    if count == 1:
        xs = [x0 + w / 2]
    else:
        xs = [x0 + margin + i * usable / (count - 1) for i in range(count)]

    tsv_w = min(w * 0.05, usable / max(count, 2) * 0.35)
    for x in xs:
        # Slight taper to look more like etched/fill structure
        poly = Polygon(
            [
                (x - tsv_w / 2, y0),
                (x + tsv_w / 2, y0),
                (x + tsv_w * 0.85 / 2, y0 + h),
                (x - tsv_w * 0.85 / 2, y0 + h),
            ],
            closed=True,
            facecolor=color,
            edgecolor="black",
            linewidth=0.8
        )
        ax.add_patch(poly)

    if label:
        ax.text(
            x0 + w / 2, y0 + h / 2,
            label,
            ha="center", va="center", fontsize=8,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black")
        )


def _draw_hb_interface(ax, x0, y0, w, m_last_h, hb_pad_h, hbv_h, pitch_count=7):
    """
    Hybrid bonding interface:
      - M_last bottom die
      - HB pads
      - M_last top die
      - small HBV indications
    y0 = top of bottom die silicon
    """
    # bottom M_last
    _draw_layer(ax, x0, y0, w, m_last_h, "M_last", "#8ecae6", fontsize=7)
    # bottom HB pads
    pad_margin = w * 0.08
    usable = w - 2 * pad_margin
    xs = [x0 + pad_margin + i * usable / max(pitch_count - 1, 1) for i in range(pitch_count)]
    pad_w = min(0.08, usable / max(pitch_count, 2) * 0.55)

    for x in xs:
        ax.add_patch(Rectangle(
            (x - pad_w / 2, y0 + m_last_h),
            pad_w, hb_pad_h,
            facecolor="#f28e2b", edgecolor="black", linewidth=0.7
        ))

    # interface line
    ax.plot([x0, x0 + w], [y0 + m_last_h + hb_pad_h, y0 + m_last_h + hb_pad_h], linestyle="--", linewidth=0.8)

    # top HB pads
    for x in xs:
        ax.add_patch(Rectangle(
            (x - pad_w / 2, y0 + m_last_h + hb_pad_h),
            pad_w, hb_pad_h,
            facecolor="#f28e2b", edgecolor="black", linewidth=0.7
        ))

    # top M_last
    _draw_layer(ax, x0, y0 + m_last_h + 2 * hb_pad_h, w, m_last_h, "M_last", "#8ecae6", fontsize=7)

    # HBV markers
    hbv_y0 = y0 + m_last_h + 2 * hb_pad_h + m_last_h
    for x in xs[1:-1:2]:
        ax.add_patch(Rectangle(
            (x - pad_w * 0.22, hbv_y0),
            pad_w * 0.44, hbv_h,
            facecolor="#ffb703", edgecolor="black", linewidth=0.6
        ))
    ax.text(
        x0 + w + 0.10, y0 + m_last_h + hb_pad_h,
        "HB pads\nCu-Cu / oxide-oxide",
        ha="left", va="center", fontsize=7
    )
    ax.text(
        x0 + w + 0.10, hbv_y0 + hbv_h / 2,
        "HBV",
        ha="left", va="center", fontsize=7
    )


def _draw_hbm_stack(ax, x0, y0, w, n_dies=6, die_h=0.11, gap=0.018, tsv_label=True):
    """
    HBM stack schematic with stacked memory dies and vertical TSVs.
    """
    total_h = n_dies * die_h + (n_dies - 1) * gap
    # base logic die / controller
    _draw_layer(ax, x0, y0, w, die_h * 1.15, "HBM base", "#d9d9d9", fontsize=7)
    current_y = y0 + die_h * 1.15 + gap

    for i in range(n_dies):
        _draw_layer(ax, x0, current_y, w, die_h, f"HBM die {i+1}", "#efefef", fontsize=6)
        current_y += die_h + gap

    # TSVs through stack
    _draw_tsvs(ax, x0, y0 + die_h * 1.15 + gap * 0.5, w, total_h - gap * 0.5, count=4, label="HBM TSV" if tsv_label else None)


# ============================================================
# Defaults for physically scaled vertical dimensions
# ============================================================

def _default_dims_2d(data):
    return {
        "pcb_thickness_um": _param(data, "pcb_thickness_um", 900),
        "solder_ball_height_um": _param(data, "solder_ball_height_um", 350),
        "substrate_thickness_um": _param(data, "substrate_thickness_um", 450),
        "c4_height_um": _param(data, "c4_height_um", 120),
        "logic_die_thickness_um": _param(data, "logic_die_thickness_um", 120),
        "memory_die_thickness_um": _param(data, "memory_die_thickness_um", 90),
        "io_die_thickness_um": _param(data, "io_die_thickness_um", 90),
        "m_last_thickness_um": _param(data, "m_last_thickness_um", 3),
    }


def _default_dims_25d(data):
    return {
        "pcb_thickness_um": _param(data, "pcb_thickness_um", 900),
        "solder_ball_height_um": _param(data, "solder_ball_height_um", 350),
        "substrate_thickness_um": _param(data, "substrate_thickness_um", 450),
        "c4_height_um": _param(data, "c4_height_um", 120),
        "interposer_thickness_um": _param(data, "interposer_thickness_um", 120),
        "ubump_height_um": _param(data, "ubump_height_um", 25),
        "logic_die_thickness_um": _param(data, "logic_die_thickness_um", 120),
        "hbm_die_thickness_um": _param(data, "hbm_die_thickness_um", 55),
        "hbm_die_gap_um": _param(data, "hbm_die_gap_um", 8),
        "hbm_die_count": _param(data, "hbm_die_count", 6),
        "m_last_thickness_um": _param(data, "m_last_thickness_um", 3),
        "tsv_count_visual": _param(data, "tsv_count_visual", 6),
    }


def _default_dims_3d(data):
    return {
        "pcb_thickness_um": _param(data, "pcb_thickness_um", 900),
        "solder_ball_height_um": _param(data, "solder_ball_height_um", 350),
        "substrate_thickness_um": _param(data, "substrate_thickness_um", 450),
        "c4_height_um": _param(data, "c4_height_um", 120),
        "base_die_thickness_um": _param(data, "base_die_thickness_um", 120),
        "top_die_thickness_um": _param(data, "top_die_thickness_um", 70),
        "m_last_thickness_um": _param(data, "m_last_thickness_um", 2),
        "hb_pad_height_um": _param(data, "hb_pad_height_um", 3),
        "hbv_height_um": _param(data, "hbv_height_um", 12),
        "hbm_base_thickness_um": _param(data, "hbm_base_thickness_um", 80),
        "hbm_die_thickness_um": _param(data, "hbm_die_thickness_um", 45),
        "hbm_die_gap_um": _param(data, "hbm_die_gap_um", 8),
        "hbm_die_count": _param(data, "hbm_die_count", 6),
        "ubump_height_um": _param(data, "ubump_height_um", 20),
        "tsv_count_visual": _param(data, "tsv_count_visual", 5),
    }


# ============================================================
# Drawings
# ============================================================

def draw_2d_sip(data, output_path):
    dims = _default_dims_2d(data)

    total_um = (
        dims["pcb_thickness_um"]
        + dims["solder_ball_height_um"]
        + dims["substrate_thickness_um"]
        + dims["c4_height_um"]
        + max(
            dims["logic_die_thickness_um"],
            dims["memory_die_thickness_um"],
            dims["io_die_thickness_um"]
        )
        + dims["m_last_thickness_um"]
        + 150
    )

    fig, ax = plt.subplots(figsize=(12, 7))
    y_scale = 6.2 / total_um
    Y = lambda um: um * y_scale

    # X layout
    x_left, x_right = 0.8, 11.2
    x_logic, w_logic = 1.4, 2.5
    x_mem, w_mem = 5.1, 1.8
    x_io, w_io = 8.1, 1.8

    y = 0.50

    # PCB
    pcb_h = Y(dims["pcb_thickness_um"])
    _draw_layer(ax, x_left, y, x_right - x_left, pcb_h, "PCB / board", "#c9c9c9", fontsize=10)
    _draw_dimension_arrow(ax, 11.45, y, y + pcb_h, f"{dims['pcb_thickness_um']} µm")

    y += pcb_h

    # solder balls
    sb_h = Y(dims["solder_ball_height_um"])
    solder_xs = [2.0, 2.6, 3.2, 5.8, 6.4, 7.0, 8.9, 9.5]
    _draw_solder_balls(ax, solder_xs, y, width=0.34, height=max(sb_h, 0.18), label="Solder balls")
    y += sb_h

    # substrate
    sub_h = Y(dims["substrate_thickness_um"])
    _draw_layer(ax, 1.0, y, 10.0, sub_h, "Organic package substrate", "#b7d7a8", fontsize=10)
    _draw_dimension_arrow(ax, 10.85, y, y + sub_h, f"{dims['substrate_thickness_um']} µm")
    y_sub_top = y + sub_h

    # C4
    c4_h = Y(dims["c4_height_um"])
    _draw_c4_bumps(ax, [2.3, 2.8, 3.3, 5.7, 6.2, 8.7, 9.2], y_sub_top, height=max(c4_h, 0.10), label="C4 bumps")

    # Dies
    logic_h = Y(dims["logic_die_thickness_um"])
    mem_h = Y(dims["memory_die_thickness_um"])
    io_h = Y(dims["io_die_thickness_um"])
    m_last_h = max(Y(dims["m_last_thickness_um"]), 0.03)

    logic_y = y_sub_top + c4_h
    mem_y = y_sub_top + c4_h
    io_y = y_sub_top + c4_h

    _draw_layer(ax, x_logic, logic_y, w_logic, logic_h, "Logic die\nCPU / GPU / ASIC", "#d9d9d9", fontsize=9)
    _draw_layer(ax, x_logic, logic_y, w_logic, m_last_h, "M_last", "#8ecae6", fontsize=7)

    _draw_layer(ax, x_mem, mem_y, w_mem, mem_h, "Memory die", "#efefef", fontsize=9)
    _draw_layer(ax, x_mem, mem_y, w_mem, m_last_h, "M_last", "#8ecae6", fontsize=7)

    _draw_layer(ax, x_io, io_y, w_io, io_h, "I/O die", "#efefef", fontsize=9)
    _draw_layer(ax, x_io, io_y, w_io, m_last_h, "M_last", "#8ecae6", fontsize=7)

    # lateral routing arrows
    ax.annotate("", xy=(x_mem, mem_y + mem_h * 0.55), xytext=(x_logic + w_logic, logic_y + logic_h * 0.55),
                arrowprops=dict(arrowstyle="<->", lw=1.2))
    ax.annotate("", xy=(x_io, io_y + io_h * 0.48), xytext=(x_mem + w_mem, mem_y + mem_h * 0.48),
                arrowprops=dict(arrowstyle="<->", lw=1.2))
    ax.text(4.45, logic_y + logic_h * 0.72, "longer substrate traces", ha="center", fontsize=8)
    ax.text(7.55, io_y + io_h * 0.68, "package routing", ha="center", fontsize=8)

    ax.text(6.0, 6.8, "2.0D / SiP on Organic Substrate", ha="center", fontsize=16, weight="bold")
    ax.text(6.0, 6.45, "Solder balls + substrate + C4 bumps + side-by-side dies", ha="center", fontsize=10)

    _draw_notes(ax, data, 0.7, 6.15)

    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.1)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def draw_25d_interposer(data, output_path):
    dims = _default_dims_25d(data)

    hbm_stack_um = dims["hbm_die_count"] * dims["hbm_die_thickness_um"] + (dims["hbm_die_count"] - 1) * dims["hbm_die_gap_um"] + dims["hbm_base_thickness_um"] if "hbm_base_thickness_um" in dims else dims["hbm_die_count"] * dims["hbm_die_thickness_um"]
    total_um = (
        dims["pcb_thickness_um"]
        + dims["solder_ball_height_um"]
        + dims["substrate_thickness_um"]
        + dims["c4_height_um"]
        + dims["interposer_thickness_um"]
        + dims["ubump_height_um"]
        + max(dims["logic_die_thickness_um"], hbm_stack_um)
        + 220
    )

    fig, ax = plt.subplots(figsize=(13, 7))
    y_scale = 6.3 / total_um
    Y = lambda um: um * y_scale

    x_left, x_right = 0.7, 11.4
    y = 0.45

    # PCB
    pcb_h = Y(dims["pcb_thickness_um"])
    _draw_layer(ax, x_left, y, x_right - x_left, pcb_h, "PCB / board", "#c9c9c9", fontsize=10)
    y += pcb_h

    # solder balls
    sb_h = Y(dims["solder_ball_height_um"])
    _draw_solder_balls(ax, [2.0, 2.6, 3.2, 5.7, 6.3, 6.9, 8.8, 9.4, 10.0], y,
                       width=0.34, height=max(sb_h, 0.18), label="Solder balls")
    y += sb_h

    # organic substrate
    sub_h = Y(dims["substrate_thickness_um"])
    _draw_layer(ax, 1.0, y, 10.0, sub_h, "Organic package substrate", "#b7d7a8", fontsize=10)
    y_sub_top = y + sub_h

    # C4 bumps
    c4_h = Y(dims["c4_height_um"])
    _draw_c4_bumps(ax, [2.0, 2.5, 3.0, 5.6, 6.1, 6.6, 9.0, 9.5], y_sub_top,
                   height=max(c4_h, 0.10), label="C4 bumps")

    # silicon interposer
    int_h = Y(dims["interposer_thickness_um"])
    int_y = y_sub_top + c4_h
    _draw_layer(ax, 1.2, int_y, 9.6, int_h, "Silicon interposer", "#dddddd", fontsize=10, hatch="//")
    _draw_tsvs(ax, 1.2, int_y, 9.6, int_h, count=dims["tsv_count_visual"], label="TSV")
    # Interposer RDL top/bottom
    rdl_h = max(int_h * 0.08, 0.03)
    _draw_layer(ax, 1.2, int_y, 9.6, rdl_h, "RDL", "#8ecae6", fontsize=7)
    _draw_layer(ax, 1.2, int_y + int_h - rdl_h, 9.6, rdl_h, "RDL", "#8ecae6", fontsize=7)

    # microbumps
    ub_h = Y(dims["ubump_height_um"])
    ub_y = int_y + int_h
    _draw_micro_bumps(ax, [2.1, 2.35, 2.6, 2.85, 5.0, 5.25, 5.5, 7.1, 7.35, 7.6, 8.9, 9.15],
                      ub_y, height=max(ub_h, 0.08), label="µBumps / Cu pillar + solder cap")

    # logic die
    logic_h = Y(dims["logic_die_thickness_um"])
    logic_y = ub_y + ub_h
    _draw_layer(ax, 1.6, logic_y, 2.3, logic_h, "Logic die\nGPU / accelerator", "#d9d9d9", fontsize=9)
    _draw_layer(ax, 1.6, logic_y, 2.3, max(Y(dims["m_last_thickness_um"]), 0.03), "M_last", "#8ecae6", fontsize=7)

    # HBM stacks
    hbm_y = ub_y + ub_h
    _draw_hbm_stack(ax, 4.7, hbm_y, 1.15,
                    n_dies=dims["hbm_die_count"],
                    die_h=max(Y(dims["hbm_die_thickness_um"]), 0.07),
                    gap=max(Y(dims["hbm_die_gap_um"]), 0.015),
                    tsv_label=True)
    _draw_hbm_stack(ax, 6.5, hbm_y, 1.15,
                    n_dies=dims["hbm_die_count"],
                    die_h=max(Y(dims["hbm_die_thickness_um"]), 0.07),
                    gap=max(Y(dims["hbm_die_gap_um"]), 0.015),
                    tsv_label=False)
    _draw_hbm_stack(ax, 8.3, hbm_y, 1.15,
                    n_dies=dims["hbm_die_count"],
                    die_h=max(Y(dims["hbm_die_thickness_um"]), 0.07),
                    gap=max(Y(dims["hbm_die_gap_um"]), 0.015),
                    tsv_label=False)

    # link arrows inside interposer
    ax.annotate("", xy=(4.7, int_y + int_h * 0.55), xytext=(3.9, int_y + int_h * 0.55),
                arrowprops=dict(arrowstyle="<->", lw=1.2))
    ax.annotate("", xy=(6.5, int_y + int_h * 0.55), xytext=(5.85, int_y + int_h * 0.55),
                arrowprops=dict(arrowstyle="<->", lw=1.2))
    ax.annotate("", xy=(8.3, int_y + int_h * 0.55), xytext=(7.65, int_y + int_h * 0.55),
                arrowprops=dict(arrowstyle="<->", lw=1.2))
    ax.text(6.2, int_y + int_h * 0.28, "dense short interposer RDL links", ha="center", fontsize=8)

    ax.text(6.1, 6.85, "2.5D / TSV Silicon Interposer", ha="center", fontsize=16, weight="bold")
    ax.text(6.1, 6.48, "Solder balls + substrate + C4 + silicon interposer with TSV + µBumps + logic + HBM",
            ha="center", fontsize=10)

    _draw_notes(ax, data, 0.7, 6.18)

    ax.set_xlim(0, 12.2)
    ax.set_ylim(0, 7.1)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def draw_3d_hybrid_bonding(data, output_path):
    dims = _default_dims_3d(data)

    hbm_stack_um = dims["hbm_base_thickness_um"] + dims["hbm_die_count"] * dims["hbm_die_thickness_um"] + (dims["hbm_die_count"] - 1) * dims["hbm_die_gap_um"]

    hb_interface_um = (
        dims["m_last_thickness_um"]
        + dims["hb_pad_height_um"]
        + dims["hb_pad_height_um"]
        + dims["m_last_thickness_um"]
        + dims["hbv_height_um"]
    )

    total_um = (
        dims["pcb_thickness_um"]
        + dims["solder_ball_height_um"]
        + dims["substrate_thickness_um"]
        + dims["c4_height_um"]
        + max(
            dims["base_die_thickness_um"] + hb_interface_um + dims["top_die_thickness_um"],
            dims["base_die_thickness_um"] + dims["ubump_height_um"] + hbm_stack_um
        )
        + 260
    )

    fig, ax = plt.subplots(figsize=(13, 7.4))
    y_scale = 6.5 / total_um
    Y = lambda um: um * y_scale

    x_left, x_right = 0.7, 11.4
    y = 0.42

    # PCB
    pcb_h = Y(dims["pcb_thickness_um"])
    _draw_layer(ax, x_left, y, x_right - x_left, pcb_h, "PCB / board", "#c9c9c9", fontsize=10)
    y += pcb_h

    # solder balls
    sb_h = Y(dims["solder_ball_height_um"])
    _draw_solder_balls(ax, [2.1, 2.7, 3.3, 5.9, 6.5, 7.1, 9.0, 9.6], y,
                       width=0.34, height=max(sb_h, 0.18), label="Solder balls")
    y += sb_h

    # substrate
    sub_h = Y(dims["substrate_thickness_um"])
    _draw_layer(ax, 1.1, y, 9.8, sub_h, "Organic substrate", "#b7d7a8", fontsize=10)
    y_sub_top = y + sub_h

    # C4
    c4_h = Y(dims["c4_height_um"])
    _draw_c4_bumps(ax, [2.4, 2.9, 3.4, 6.1, 6.6, 7.1, 9.2], y_sub_top,
                   height=max(c4_h, 0.10), label="C4 bumps")

    # -------------------------
    # Left: hybrid bonded logic stack
    # -------------------------
    base_x = 1.8
    base_w = 3.3
    base_y = y_sub_top + c4_h
    base_die_h = Y(dims["base_die_thickness_um"])

    _draw_layer(ax, base_x, base_y, base_w, base_die_h, "Bottom die / wafer", "#d9d9d9", fontsize=9)
    _draw_tsvs(ax, base_x, base_y, base_w, base_die_h, count=dims["tsv_count_visual"], label="TSV")

    m_last_h = max(Y(dims["m_last_thickness_um"]), 0.028)
    hb_pad_h = max(Y(dims["hb_pad_height_um"]), 0.028)
    hbv_h = max(Y(dims["hbv_height_um"]), 0.07)

    hb_if_y = base_y + base_die_h
    _draw_hb_interface(ax, base_x, hb_if_y, base_w, m_last_h, hb_pad_h, hbv_h, pitch_count=7)

    top_die_y = hb_if_y + m_last_h + 2 * hb_pad_h + m_last_h
    top_die_h = Y(dims["top_die_thickness_um"])
    _draw_layer(ax, base_x, top_die_y, base_w, top_die_h, "Top die / wafer", "#e8e8e8", fontsize=9)

    # Add top side local metal
    _draw_layer(ax, base_x, top_die_y + top_die_h - m_last_h, base_w, m_last_h, "Top metal", "#8ecae6", fontsize=7)

    # label the hybrid bonding stack
    ax.text(base_x + base_w / 2, top_die_y + top_die_h + 0.20,
            "Hybrid bonding stack:\nM_last + HB pads + HBV",
            ha="center", va="bottom", fontsize=9)

    # -------------------------
    # Right: HBM stack on same package
    # -------------------------
    hbm_base_x = 7.1
    hbm_base_w = 1.5

    # small logic base die under HBM
    hbm_logic_y = y_sub_top + c4_h
    hbm_logic_h = Y(dims["base_die_thickness_um"])
    _draw_layer(ax, hbm_base_x, hbm_logic_y, hbm_base_w, hbm_logic_h, "Logic base", "#d9d9d9", fontsize=8)
    _draw_tsvs(ax, hbm_base_x, hbm_logic_y, hbm_base_w, hbm_logic_h, count=3, label=None)

    # µBumps between logic base and HBM base
    ub_h = max(Y(dims["ubump_height_um"]), 0.07)
    ub_y = hbm_logic_y + hbm_logic_h
    _draw_micro_bumps(ax, [7.35, 7.60, 7.85, 8.10, 8.35], ub_y, height=ub_h, label="µBumps")

    hbm_y = ub_y + ub_h
    _draw_hbm_stack(ax, hbm_base_x, hbm_y, hbm_base_w,
                    n_dies=dims["hbm_die_count"],
                    die_h=max(Y(dims["hbm_die_thickness_um"]), 0.07),
                    gap=max(Y(dims["hbm_die_gap_um"]), 0.015),
                    tsv_label=True)

    ax.text(hbm_base_x + hbm_base_w / 2, hbm_y + 1.1,
            "HBM stack", ha="center", fontsize=9)

    # arrows / thermal notes
    ax.annotate("short vertical links",
                xy=(3.45, hb_if_y + 0.10), xytext=(3.45, 6.35),
                arrowprops=dict(arrowstyle="->", lw=1.2),
                ha="center", fontsize=9)

    ax.annotate("thermal challenge",
                xy=(2.8, top_die_y + top_die_h), xytext=(2.8, 6.7),
                arrowprops=dict(arrowstyle="->", lw=1.2),
                ha="center", fontsize=9)

    ax.text(6.1, 7.05, "3D / Hybrid Bonding + TSV", ha="center", fontsize=16, weight="bold")
    ax.text(6.1, 6.67,
            "Solder balls + substrate + C4 + bottom die with TSV + hybrid bonding (M_last / HB pads / HBV) + HBM example",
            ha="center", fontsize=10)

    _draw_notes(ax, data, 0.7, 6.32)

    ax.set_xlim(0, 12.2)
    ax.set_ylim(0, 7.35)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)



# ============================================================
# Top-view layout drawing
# ============================================================

def _component_color(component_type):
    colors = {
        "logic": "#404040",
        "ai_tile": "#8e24aa",
        "hbm": "#6a1b9a",
        "memory": "#7b1fa2",
        "io": "#546e7a",
        "substrate": "#ffffff",
        "interposer": "#f5f5f5"
    }
    return colors.get(component_type, "#bdbdbd")


def _link_style(link_type):
    styles = {
        "ucie_plain": {
            "color": "#00a86b",
            "linestyle": "-",
            "linewidth": 1.4,
            "label": "UCIe plain vanilla"
        },
        "ucie_validation": {
            "color": "#1e88e5",
            "linestyle": "-",
            "linewidth": 1.4,
            "label": "UCIe interoperability validation"
        },
        "rdl": {
            "color": "#f28e2b",
            "linestyle": "-",
            "linewidth": 1.2,
            "label": "RDL connection"
        },
        "high_speed": {
            "color": "#d81b60",
            "linestyle": "--",
            "linewidth": 1.5,
            "label": "High-speed link"
        }
    }
    return styles.get(link_type, {
        "color": "black",
        "linestyle": "-",
        "linewidth": 1.0,
        "label": link_type
    })


def _component_center(component):
    return (
        component["x_mm"] + component["width_mm"] / 2,
        component["y_mm"] + component["height_mm"] / 2
    )


def _draw_rotated_component(ax, comp):
    x = comp["x_mm"]
    y = comp["y_mm"]
    w = comp["width_mm"]
    h = comp["height_mm"]
    rotation = comp.get("rotation_deg", 0)
    label = comp.get("label", comp.get("name", "component"))
    comp_type = comp.get("type", "component")

    cx = x + w / 2
    cy = y + h / 2

    rect = Rectangle(
        (x, y),
        w,
        h,
        linewidth=1.2,
        edgecolor="black",
        facecolor=_component_color(comp_type)
    )

    transform = (
        Affine2D()
        .rotate_deg_around(cx, cy, rotation)
        + ax.transData
    )

    rect.set_transform(transform)
    ax.add_patch(rect)

    text_color = "white" if comp_type in ("logic", "ai_tile", "hbm", "memory") else "black"

    ax.text(
        cx,
        cy,
        label,
        ha="center",
        va="center",
        fontsize=9,
        color=text_color,
        weight="bold" if comp_type in ("logic", "ai_tile") else "normal",
        rotation=rotation,
        rotation_mode="anchor"
    )

    # Optional local sub-blocks, useful for chiplet small annotations
    for block in comp.get("sub_blocks", []):
        bx = x + block["x_mm"]
        by = y + block["y_mm"]
        bw = block["width_mm"]
        bh = block["height_mm"]

        sub = Rectangle(
            (bx, by),
            bw,
            bh,
            linewidth=0.6,
            edgecolor="black",
            facecolor=block.get("color", "#d9d9d9")
        )
        sub.set_transform(transform)
        ax.add_patch(sub)

        if block.get("label"):
            ax.text(
                bx + bw / 2,
                by + bh / 2,
                block["label"],
                ha="center",
                va="center",
                fontsize=5,
                color="black",
                rotation=rotation,
                rotation_mode="anchor"
            )


def _draw_link(ax, comp_a, comp_b, link):
    x1, y1 = _component_center(comp_a)
    x2, y2 = _component_center(comp_b)

    style = _link_style(link.get("type", "link"))

    # simple orthogonal routing: vertical-horizontal-vertical
    mid_y = (y1 + y2) / 2

    ax.plot(
        [x1, x1, x2, x2],
        [y1, mid_y, mid_y, y2],
        color=style["color"],
        linestyle=style["linestyle"],
        linewidth=style["linewidth"]
    )


def draw_top_view_layout(data, output_path):
    layout = data.get("top_view_layout")
    if not layout:
        return None

    substrate = layout.get("substrate", {})
    interposer = layout.get("interposer", {})

    substrate_w = substrate.get(
        "width_mm",
        _nested_get(data, ["geometry", "substrate_width_mm"], 60)
    )
    substrate_h = substrate.get(
        "height_mm",
        _nested_get(data, ["geometry", "substrate_height_mm"], 50)
    )

    interposer_x = interposer.get("x_mm", 5)
    interposer_y = interposer.get("y_mm", 5)
    interposer_w = interposer.get(
        "width_mm",
        _nested_get(data, ["geometry", "interposer_width_mm"], substrate_w - 10)
    )
    interposer_h = interposer.get(
        "height_mm",
        _nested_get(data, ["geometry", "interposer_height_mm"], substrate_h - 10)
    )

    components = layout.get("components", [])
    links = layout.get("links", [])

    fig, ax = plt.subplots(figsize=(10, 8))

    # Substrate outline
    substrate_rect = Rectangle(
        (0, 0),
        substrate_w,
        substrate_h,
        linewidth=1.8,
        edgecolor="#00acc1",
        facecolor="white"
    )
    ax.add_patch(substrate_rect)

    # Interposer outline
    interposer_rect = Rectangle(
        (interposer_x, interposer_y),
        interposer_w,
        interposer_h,
        linewidth=1.4,
        edgecolor="#00a86b",
        facecolor="#f8f8f8",
        linestyle="-"
    )
    ax.add_patch(interposer_rect)

    ax.text(
        interposer_x + 1,
        interposer_y + interposer_h - 1.2,
        "interposer",
        ha="left",
        va="top",
        fontsize=8,
        color="#00a86b"
    )

    # Component dictionary
    comp_by_name = {comp["name"]: comp for comp in components}

    # Draw links first, below dies
    for link in links:
        source_name = link.get("from")
        target_name = link.get("to")

        if source_name not in comp_by_name or target_name not in comp_by_name:
            print(f"Warning: link ignored, missing component: {link}")
            continue

        _draw_link(ax, comp_by_name[source_name], comp_by_name[target_name], link)

    # Draw components
    for comp in components:
        _draw_rotated_component(ax, comp)

    # Title
    title = layout.get("title", f"{data.get('name', 'Integration')} top view layout")
    ax.text(
        substrate_w / 2,
        substrate_h + 2.0,
        title,
        ha="center",
        va="bottom",
        fontsize=14,
        weight="bold"
    )

    # Legend for links
    used_link_types = []
    for link in links:
        lt = link.get("type", "link")
        if lt not in used_link_types:
            used_link_types.append(lt)

    legend_items = []
    for lt in used_link_types:
        style = _link_style(lt)
        legend_items.append(
            plt.Line2D(
                [0],
                [0],
                color=style["color"],
                linestyle=style["linestyle"],
                linewidth=style["linewidth"],
                label=style["label"]
            )
        )

    component_types = []
    for comp in components:
        ct = comp.get("type", "component")
        if ct not in component_types:
            component_types.append(ct)

    for ct in component_types:
        legend_items.append(
            Patch(
                facecolor=_component_color(ct),
                edgecolor="black",
                label=ct
            )
        )

    if legend_items:
        ax.legend(
            handles=legend_items,
            loc="lower left",
            bbox_to_anchor=(0.0, -0.18),
            fontsize=8,
            frameon=False,
            ncol=2
        )

    # Axes formatting
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-2, substrate_w + 2)
    ax.set_ylim(-2, substrate_h + 5)
    ax.set_xlabel("X position [mm]")
    ax.set_ylabel("Y position [mm]")
    ax.grid(True, linewidth=0.4, alpha=0.35)

    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)

    return output_path

# ============================================================
# Loader / dispatcher
# ============================================================

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

    outputs = []

    if "2.0" in integration_type or "2d" in integration_type or "organic" in name:
        out = output_dir / "packaging_2d_sip.png"
        draw_2d_sip(data, out)
        outputs.append(out)

    elif "2.5" in integration_type or "interposer" in name:
        out = output_dir / "packaging_25d_tsv_interposer.png"
        draw_25d_interposer(data, out)
        outputs.append(out)

    elif "3d" in integration_type or "hybrid" in name:
        out = output_dir / "packaging_3d_hybrid_bonding_tsv.png"
        draw_3d_hybrid_bonding(data, out)
        outputs.append(out)

    else:
        out = output_dir / f"packaging_{name}.png"
        draw_2d_sip(data, out)
        outputs.append(out)

    # Optional top view layout
    if data.get("top_view_layout"):
        top_view_out = output_dir / f"top_view_{name}.png"
        draw_top_view_layout(data, top_view_out)
        outputs.append(top_view_out)

    return outputs


def draw_all_packaging(data_dir="data", output_dir="outputs/figures"):
    integrations = load_json_files(data_dir)
    outputs = []

    for data in integrations:
        generated = draw_packaging_from_json(data, output_dir)

        if isinstance(generated, list):
            outputs.extend(generated)
        else:
            outputs.append(generated)

    return outputs