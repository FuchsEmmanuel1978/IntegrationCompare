from pathlib import Path
import json
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon


# ============================================================
# Utilities
# ============================================================

def _ng(data, path, default=None):
    obj = data
    for key in path:
        if not isinstance(obj, dict) or key not in obj:
            return default
        obj = obj[key]
    return obj


def _get_param(data, key, default):
    """
    Search parameter in:
      data["hb_hbm_detail"][key]
      data["stack"][key]
      data["geometry"][key]
    """
    for root in ("hb_hbm_detail", "stack", "geometry"):
        val = _ng(data, [root, key], None)
        if val is not None:
            return val
    return default


def _layer(ax, x, y, w, h, color, label=None, fontsize=8, edgecolor="black", lw=1.0, alpha=1.0):
    rect = Rectangle(
        (x, y), w, h,
        facecolor=color,
        edgecolor=edgecolor,
        linewidth=lw,
        alpha=alpha
    )
    ax.add_patch(rect)
    if label:
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=fontsize)
    return rect


def _label(ax, x, y, text, fontsize=8, ha="center", va="center", color="black"):
    ax.text(x, y, text, fontsize=fontsize, ha=ha, va=va, color=color)


def _dimension(ax, x, y0, y1, text, fontsize=8):
    ax.annotate("", xy=(x, y0), xytext=(x, y1), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text(x + 0.2, (y0 + y1) / 2, text, rotation=90, ha="left", va="center", fontsize=fontsize)


def _pitch_dimension(ax, x0, x1, y, text, fontsize=8):
    ax.annotate("", xy=(x0, y), xytext=(x1, y), arrowprops=dict(arrowstyle="<->", lw=0.9))
    ax.text((x0 + x1) / 2, y + 0.12, text, ha="center", va="bottom", fontsize=fontsize)


# ============================================================
# Main drawing
# ============================================================

def draw_hb_hbm_detail(data, output_path):
    """
    Draw a zoomed hybrid-bonding / HBM / HBV cross-section.

    Main driver inputs:
      - HBM width / height / pitch
      - HBV width / height / pitch

    Zoom principle:
      - The real bottom silicon thickness can be 775 µm.
      - Only the last useful visible part, e.g. 100 µm, is drawn.
      - A truncation mark indicates that the bottom Si continues below.
    """

    # ---------------------------
    # Inputs in µm
    # ---------------------------
    bottom_die_thickness_um = _get_param(data, "bottom_die_thickness_um", 775)
    visible_bottom_si_um = _get_param(data, "visible_bottom_si_um", 100)
    zoom_mode = _get_param(data, "zoom_mode", True)
    show_bottom_truncation = _get_param(data, "show_bottom_truncation", True)

    top_die_thickness_um = _get_param(data, "top_die_thickness_um", 120)

    metal_layer_count = _get_param(data, "metal_layer_count", 4)
    metal_thickness_um = _get_param(data, "metal_thickness_um", 2)
    dielectric_thickness_um = _get_param(data, "dielectric_thickness_um", 3)

    hbm_width_um = _get_param(data, "hbm_width_um", 10)
    hbm_height_um = _get_param(data, "hbm_height_um", 6)
    hbm_pitch_um = _get_param(data, "hbm_pitch_um", 22)
    hbm_count = _get_param(data, "hbm_count", 5)

    hbv_width_um = _get_param(data, "hbv_width_um", 4)
    hbv_height_um = _get_param(data, "hbv_height_um", 18)
    hbv_pitch_um = _get_param(data, "hbv_pitch_um", 28)
    hbv_count = _get_param(data, "hbv_count", 4)

    ubm_width_um = _get_param(data, "ubm_width_um", 26)
    ubm_height_cu_um = _get_param(data, "ubm_height_cu_um", 5)
    ubm_height_ni_um = _get_param(data, "ubm_height_ni_um", 2)
    ubm_height_au_um = _get_param(data, "ubm_height_au_um", 0.3)

    top_die_width_um = _get_param(data, "top_die_width_um", 150)
    detail_width_um = _get_param(data, "detail_width_um", 320)

    tsv_width_um = _get_param(data, "tsv_width_um", 16)
    tsv_height_um = _get_param(data, "tsv_height_um", visible_bottom_si_um)

    # ---------------------------
    # Derived dimensions
    # ---------------------------
    beol_stack_thickness_um = (
        metal_layer_count * metal_thickness_um
        + (metal_layer_count + 1) * dielectric_thickness_um
    )

    if zoom_mode:
        drawn_bottom_si_um = visible_bottom_si_um
        bottom_si_label = (
            f"Si bottom wafer\nvisible last {visible_bottom_si_um} µm "
            f"of {bottom_die_thickness_um} µm"
        )
    else:
        drawn_bottom_si_um = bottom_die_thickness_um
        bottom_si_label = f"Si bottom (wafer1) {bottom_die_thickness_um} µm"

    # ---------------------------
    # Scaling
    # ---------------------------
    total_height_um = (
        drawn_bottom_si_um
        + beol_stack_thickness_um
        + beol_stack_thickness_um
        + top_die_thickness_um
        + 45
    )

    total_width_um = detail_width_um

    sx = 1.0 / 18.0
    sy = 1.0 / max(total_height_um / 6.2, 1.0)

    def X(v):
        return v * sx

    def Y(v):
        return v * sy

    fig, ax = plt.subplots(figsize=(12, 5.8))

    # ---------------------------
    # Colors
    # ---------------------------
    c_si = "#6f6ea8"
    c_cu = "#f57c00"
    c_ni = "#b85bbd"
    c_au = "#f4ea2a"
    c_dielectric = "#f3d79b"
    c_hbv = "#f57c00"
    c_tsv = "#e60000"
    c_outline = "#7ac900"
    c_interface = "#3f51b5"
    c_cut = "#ffffff"

    # ---------------------------
    # Baseline positions
    # ---------------------------
    x0 = 10
    y0 = 0.8

    bottom_si_x = X(x0)
    bottom_si_y = y0
    bottom_si_w = X(total_width_um)
    bottom_si_h = Y(drawn_bottom_si_um)

    # ---------------------------
    # Bottom Si, zoomed
    # ---------------------------
    _layer(
        ax,
        bottom_si_x,
        bottom_si_y,
        bottom_si_w,
        bottom_si_h,
        c_si,
        label=bottom_si_label,
        fontsize=13
    )

    # Truncation symbol at bottom of silicon
    if zoom_mode and show_bottom_truncation:
        cut_y = bottom_si_y + 0.10
        zigzag_amp = 0.08
        n_zigzag = 12
        xs = [
            bottom_si_x + i * bottom_si_w / n_zigzag
            for i in range(n_zigzag + 1)
        ]
        ys = [
            cut_y + (zigzag_amp if i % 2 == 0 else -zigzag_amp)
            for i in range(n_zigzag + 1)
        ]
        ax.plot(xs, ys, color="white", linewidth=3.0)
        ax.plot(xs, ys, color="black", linewidth=0.8)

        ax.text(
            bottom_si_x + bottom_si_w * 0.98,
            cut_y + 0.16,
            f"substrate truncated\nreal thickness = {bottom_die_thickness_um} µm",
            ha="right",
            va="bottom",
            fontsize=8,
            color="black",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black")
        )

    # ---------------------------
    # TSVs in visible bottom Si
    # ---------------------------
    def draw_tsv(center_x_um):
        x = X(center_x_um - tsv_width_um / 2)
        w = X(tsv_width_um)

        visible_tsv_h_um = min(tsv_height_um, drawn_bottom_si_um)
        h = Y(visible_tsv_h_um)

        _layer(
            ax,
            x,
            bottom_si_y,
            w,
            h,
            c_tsv,
            label=None,
            lw=0.8
        )

        if zoom_mode and visible_tsv_h_um < tsv_height_um:
            ax.text(
                x + w / 2,
                bottom_si_y + 0.12,
                "TSV\ncontinues",
                ha="center",
                va="bottom",
                fontsize=7,
                color="white"
            )

    draw_tsv(x0 + 55)
    draw_tsv(x0 + detail_width_um - 55)

    # ---------------------------
    # Bottom BEOL stack
    # ---------------------------
    beol_y = bottom_si_y + bottom_si_h
    current_y = beol_y

    metal_ys = []

    for i in range(metal_layer_count):
        diel_h = Y(dielectric_thickness_um)
        _layer(
            ax,
            bottom_si_x,
            current_y,
            bottom_si_w,
            diel_h,
            c_dielectric,
            label=None,
            lw=0.5
        )
        current_y += diel_h

        metal_h = Y(metal_thickness_um)
        _layer(
            ax,
            bottom_si_x,
            current_y,
            bottom_si_w,
            metal_h,
            c_interface,
            label=None,
            lw=0.5
        )
        metal_ys.append((current_y, metal_h))
        current_y += metal_h

    diel_h = Y(dielectric_thickness_um)
    _layer(
        ax,
        bottom_si_x,
        current_y,
        bottom_si_w,
        diel_h,
        c_dielectric,
        label=None,
        lw=0.5
    )
    current_y += diel_h

    beol_top_y = current_y

    ax.text(
        bottom_si_x + bottom_si_w * 0.02,
        beol_y + Y(beol_stack_thickness_um) / 2,
        "Bottom BEOL\nmetals + dielectric",
        ha="left",
        va="center",
        fontsize=8,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="black")
    )

    # Dotted hybrid bonding reference line
    ax.plot(
        [bottom_si_x - 0.2, bottom_si_x + bottom_si_w + 0.2],
        [beol_y + Y(beol_stack_thickness_um * 0.55)] * 2,
        linestyle="--",
        linewidth=1.0,
        color="gray"
    )

    # ---------------------------
    # HBM pads
    # ---------------------------
    hbm_start_x_um = x0 + 55
    hbm_centers_um = [
        hbm_start_x_um + i * hbm_pitch_um
        for i in range(hbm_count)
    ]

    hbm_y = beol_y + Y(dielectric_thickness_um + metal_thickness_um * 0.3)

    for i, cx_um in enumerate(hbm_centers_um):
        x = X(cx_um - hbm_width_um / 2)
        w = X(hbm_width_um)
        h = max(Y(hbm_height_um), 0.055)

        _layer(
            ax,
            x,
            hbm_y,
            w,
            h,
            c_cu,
            label=None,
            lw=0.8
        )

        label = "HBM" if i == 0 else ""
        if label:
            _label(ax, x + w / 2, hbm_y + h + 0.10, label, fontsize=8, va="bottom")

    if len(hbm_centers_um) >= 2:
        _pitch_dimension(
            ax,
            X(hbm_centers_um[0]),
            X(hbm_centers_um[1]),
            hbm_y + max(Y(hbm_height_um), 0.055) + 0.35,
            f"HBM pitch = {hbm_pitch_um} µm",
            fontsize=8
        )

    # ---------------------------
    # HBV pillars
    # ---------------------------
    hbv_start_x_um = x0 + 80
    hbv_centers_um = [
        hbv_start_x_um + i * hbv_pitch_um
        for i in range(hbv_count)
    ]

    hbv_y0 = beol_y + Y(dielectric_thickness_um + metal_thickness_um)
    hbv_h = max(Y(hbv_height_um), 0.10)

    for i, cx_um in enumerate(hbv_centers_um):
        x = X(cx_um - hbv_width_um / 2)
        w = X(hbv_width_um)

        _layer(
            ax,
            x,
            hbv_y0,
            w,
            hbv_h,
            c_hbv,
            label=None,
            lw=0.8
        )

        if i == 0:
            _label(ax, x + w / 2, hbv_y0 - 0.10, "HBV", fontsize=8, va="top")

    if len(hbv_centers_um) >= 2:
        _pitch_dimension(
            ax,
            X(hbv_centers_um[0]),
            X(hbv_centers_um[1]),
            hbv_y0 + hbv_h + 0.48,
            f"HBV pitch = {hbv_pitch_um} µm",
            fontsize=8
        )

    _dimension(
        ax,
        X(hbv_centers_um[-1] + 12),
        hbv_y0,
        hbv_y0 + hbv_h,
        f"HBV h = {hbv_height_um} µm",
        fontsize=8
    )

    # ---------------------------
    # Top die BEOL + top Si
    # ---------------------------
    top_die_x_um = x0 + (detail_width_um - top_die_width_um) / 2
    top_die_x = X(top_die_x_um)
    top_die_w = X(top_die_width_um)

    top_beol_y = beol_top_y
    top_beol_h = Y(beol_stack_thickness_um)

    _layer(
        ax,
        top_die_x,
        top_beol_y,
        top_die_w,
        top_beol_h,
        c_dielectric,
        label=None,
        lw=0.8
    )

    ty = top_beol_y

    for i in range(metal_layer_count):
        dh = Y(dielectric_thickness_um)
        _layer(
            ax,
            top_die_x,
            ty,
            top_die_w,
            dh,
            c_dielectric,
            label=None,
            lw=0.5
        )
        ty += dh

        mh = Y(metal_thickness_um)
        _layer(
            ax,
            top_die_x,
            ty,
            top_die_w,
            mh,
            c_interface,
            label=None,
            lw=0.5
        )
        ty += mh

    top_si_y = top_beol_y + top_beol_h
    top_si_h = Y(top_die_thickness_um)

    _layer(
        ax,
        top_die_x,
        top_si_y,
        top_die_w,
        top_si_h,
        c_si,
        label=f"Si top die\n{top_die_thickness_um} µm",
        fontsize=13
    )

    _dimension(
        ax,
        top_die_x + top_die_w + 0.35,
        top_si_y,
        top_si_y + top_si_h,
        f"{top_die_thickness_um} µm",
        fontsize=8
    )

    # ---------------------------
    # Side UBM structures
    # ---------------------------
    def draw_side_ubm(center_x_um):
        base_y = beol_top_y + Y(8)

        cu_x = X(center_x_um - ubm_width_um / 2)
        cu_w = X(ubm_width_um)
        cu_h = max(Y(ubm_height_cu_um), 0.06)

        _layer(
            ax,
            cu_x,
            base_y,
            cu_w,
            cu_h,
            c_cu,
            label="Cu\n5 µm",
            fontsize=7,
            lw=0.9
        )

        ni_x = X(center_x_um - ubm_width_um * 0.43)
        ni_w = X(ubm_width_um * 0.86)
        ni_y = base_y + cu_h
        ni_h = max(Y(ubm_height_ni_um), 0.04)

        _layer(
            ax,
            ni_x,
            ni_y,
            ni_w,
            ni_h,
            c_ni,
            label="Ni 2 µm",
            fontsize=7,
            lw=0.9
        )

        au_x = X(center_x_um - ubm_width_um * 0.52)
        au_w = X(ubm_width_um * 1.04)
        au_y = ni_y + ni_h
        au_h = max(Y(ubm_height_au_um), 0.025)

        _layer(
            ax,
            au_x,
            au_y,
            au_w,
            au_h,
            c_au,
            label=None,
            lw=0.8
        )

        ax.text(
            au_x + au_w * 0.86,
            au_y + au_h + 0.03,
            f"Au {ubm_height_au_um} µm",
            fontsize=7,
            ha="left",
            va="bottom"
        )

        # green passivation / opening outline
        outline = Polygon(
            [
                (cu_x - X(3), base_y - Y(1)),
                (cu_x - X(3), au_y + au_h + Y(8)),
                (cu_x + X(3), au_y + au_h + Y(8)),
                (cu_x + X(3), base_y + Y(1)),
                (cu_x + cu_w + X(3), base_y + Y(1)),
                (cu_x + cu_w + X(3), au_y + au_h + Y(8)),
                (cu_x + cu_w + X(9), au_y + au_h + Y(8)),
                (cu_x + cu_w + X(9), base_y - Y(1)),
            ],
            closed=False,
            fill=False,
            edgecolor=c_outline,
            linewidth=2.5
        )
        ax.add_patch(outline)

    left_ubm_center = x0 + 35
    right_ubm_center = x0 + detail_width_um - 35

    draw_side_ubm(left_ubm_center)
    draw_side_ubm(right_ubm_center)

    ax.text(
        X(left_ubm_center),
        beol_top_y + Y(22),
        "F1UBM1",
        fontsize=9,
        ha="center",
        va="bottom"
    )

    # ---------------------------
    # Labels for metals
    # ---------------------------
    if metal_ys:
        y_line = metal_ys[0][0] + metal_ys[0][1] / 2
        ax.text(
            X(x0 + 75),
            y_line - 0.08,
            "F1LNE1",
            fontsize=8,
            ha="center",
            va="top"
        )

    ax.text(
        X(x0 + detail_width_um * 0.52),
        beol_top_y + 0.15,
        "Hybrid bonding interface zoom",
        fontsize=10,
        ha="center",
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black")
    )

    # ---------------------------
    # Notes box
    # ---------------------------
    notes = [
        "ZOOM MODE",
        f"Visible bottom Si: {visible_bottom_si_um} µm",
        f"Real bottom Si: {bottom_die_thickness_um} µm",
        "",
        f"HBM: {hbm_width_um} x {hbm_height_um} µm",
        f"HBM pitch: {hbm_pitch_um} µm",
        f"HBV: {hbv_width_um} x {hbv_height_um} µm",
        f"HBV pitch: {hbv_pitch_um} µm",
        f"Metal layers: {metal_layer_count}"
    ]

    ax.text(
        X(x0 + detail_width_um + 10),
        bottom_si_y + bottom_si_h + Y(beol_stack_thickness_um) * 0.9,
        "\n".join(notes),
        fontsize=8,
        ha="left",
        va="top",
        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="black")
    )

    # ---------------------------
    # Final formatting
    # ---------------------------
    ax.set_title(
        "Zoomed Hybrid Bonding Cross-Section — HBM / HBV pitch-driven",
        fontsize=14,
        weight="bold"
    )

    ymax = top_si_y + top_si_h + 0.8

    ax.set_xlim(0, X(total_width_um + 110))
    ax.set_ylim(0, ymax)
    ax.axis("off")

    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


# ============================================================
# Optional JSON loader / batch helper
# ============================================================

def load_json_file(json_path):
    json_path = Path(json_path)
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def draw_hb_hbm_detail_from_json(json_path, output_path):
    data = load_json_file(json_path)
    draw_hb_hbm_detail(data, output_path)