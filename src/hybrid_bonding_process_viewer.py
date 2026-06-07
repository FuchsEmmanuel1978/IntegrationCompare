"""
hybrid_bonding_process_viewer.py

Interactive step-by-step Hybrid Bonding process viewer.

Run:
    python hybrid_bonding_process_viewer.py

No external dependency required.
Only Python standard library is used.
"""

import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ProcessStep:
    step_id: int
    title: str
    description: str
    cost_params: Dict[str, float]
    lca_params: Dict[str, float]
    critical_params: Dict[str, float] = field(default_factory=dict)


def compute_step_cost(step: ProcessStep) -> float:
    p = step.cost_params
    return (
        p.get("base_cost_usd", 0.0)
        + p.get("wafer_area_mm2", 0.0) * p.get("cost_usd_per_mm2", 0.0)
        + p.get("process_time_min", 0.0) * p.get("machine_rate_usd_per_min", 0.0)
        + p.get("consumables_usd", 0.0)
        + p.get("yield_loss_penalty_usd", 0.0)
    )


def compute_step_lca(step: ProcessStep) -> float:
    p = step.lca_params
    return (
        p.get("electricity_kwh", 0.0) * p.get("kgco2e_per_kwh", 0.06)
        + p.get("water_l", 0.0) * p.get("kgco2e_per_l_water", 0.0003)
        + p.get("chemicals_kg", 0.0) * p.get("kgco2e_per_kg_chemicals", 8.0)
        + p.get("process_gases_kgco2e", 0.0)
    )


def build_default_process() -> List[ProcessStep]:
    wafer_area_mm2 = 70685  # 300 mm wafer approximate area
    return [
        ProcessStep(
            1,
            "Préparation des surfaces",
            "Préparation des surfaces die/wafer. Les pads Cu sont exposés dans le diélectrique et les surfaces sont préparées pour le collage hybride.",
            {"base_cost_usd": 300, "wafer_area_mm2": wafer_area_mm2, "cost_usd_per_mm2": 0.003, "process_time_min": 25, "machine_rate_usd_per_min": 8, "consumables_usd": 120, "yield_loss_penalty_usd": 30},
            {"electricity_kwh": 18, "water_l": 250, "chemicals_kg": 1.2, "process_gases_kgco2e": 0.5},
            {"Cu pad pitch µm": 5, "Cu recess nm": 5, "Particle limit nm": 100},
        ),
        ProcessStep(
            2,
            "Planarisation / CMP",
            "CMP pour obtenir une surface très plane. Le contrôle du Cu recess, de la rugosité et de la topographie est critique.",
            {"base_cost_usd": 500, "wafer_area_mm2": wafer_area_mm2, "cost_usd_per_mm2": 0.004, "process_time_min": 40, "machine_rate_usd_per_min": 12, "consumables_usd": 220, "yield_loss_penalty_usd": 50},
            {"electricity_kwh": 35, "water_l": 900, "chemicals_kg": 2.5, "process_gases_kgco2e": 0.7},
            {"Roughness nm RMS": 0.5, "Cu recess nm": 5, "Dishing nm": 10},
        ),
        ProcessStep(
            3,
            "Nettoyage & activation",
            "Nettoyage final et activation plasma pour enlever les particules et activer les surfaces diélectriques.",
            {"base_cost_usd": 260, "wafer_area_mm2": wafer_area_mm2, "cost_usd_per_mm2": 0.002, "process_time_min": 20, "machine_rate_usd_per_min": 9, "consumables_usd": 160, "yield_loss_penalty_usd": 40},
            {"electricity_kwh": 22, "water_l": 700, "chemicals_kg": 1.8, "process_gases_kgco2e": 1.1},
            {"Particle density cm⁻²": 0.1, "Plasma time s": 45, "Surface energy a.u.": 1.0},
        ),
        ProcessStep(
            4,
            "Alignement de précision",
            "Alignement die-to-wafer ou wafer-to-wafer. Le budget overlay est critique lorsque le pitch descend à quelques microns.",
            {"base_cost_usd": 450, "wafer_area_mm2": wafer_area_mm2, "cost_usd_per_mm2": 0.0035, "process_time_min": 35, "machine_rate_usd_per_min": 15, "consumables_usd": 80, "yield_loss_penalty_usd": 120},
            {"electricity_kwh": 28, "water_l": 120, "chemicals_kg": 0.2, "process_gases_kgco2e": 0.2},
            {"Overlay accuracy µm": 0.2, "Placement force N": 0.1, "Alignment time s": 60},
        ),
        ProcessStep(
            5,
            "Contact / collage initial",
            "Mise en contact initiale. La liaison diélectrique démarre, puis les contacts Cu-Cu sont préparés pour la liaison finale.",
            {"base_cost_usd": 520, "wafer_area_mm2": wafer_area_mm2, "cost_usd_per_mm2": 0.004, "process_time_min": 30, "machine_rate_usd_per_min": 16, "consumables_usd": 60, "yield_loss_penalty_usd": 160},
            {"electricity_kwh": 30, "water_l": 90, "chemicals_kg": 0.1, "process_gases_kgco2e": 0.2},
            {"Bonding pressure MPa": 0.1, "Void density cm⁻²": 0.05, "Initial bond energy J/m²": 1.5},
        ),
        ProcessStep(
            6,
            "Recuit & liaison finale",
            "Recuit thermique pour renforcer la liaison diélectrique et finaliser le contact Cu-Cu. L'interface hybride est formée.",
            {"base_cost_usd": 420, "wafer_area_mm2": wafer_area_mm2, "cost_usd_per_mm2": 0.0025, "process_time_min": 90, "machine_rate_usd_per_min": 6, "consumables_usd": 40, "yield_loss_penalty_usd": 80},
            {"electricity_kwh": 75, "water_l": 60, "chemicals_kg": 0.05, "process_gases_kgco2e": 0.3},
            {"Anneal temperature °C": 300, "Anneal time min": 90, "Final bond strength J/m²": 2.5},
        ),
    ]


class ProcessCanvas:
    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas

    def clear(self):
        self.canvas.delete("all")

    def text(self, x, y, txt, size=12, fill="#0b1b4d", weight="normal", anchor="center"):
        self.canvas.create_text(x, y, text=txt, fill=fill, font=("Segoe UI", size, weight), anchor=anchor, justify="center")

    def rect(self, x1, y1, x2, y2, fill, outline="#0b1b4d", width=2, dash=None):
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=width, dash=dash)

    def line(self, x1, y1, x2, y2, fill="#0b1b4d", width=2, dash=None, arrow=None):
        self.canvas.create_line(x1, y1, x2, y2, fill=fill, width=width, dash=dash, arrow=arrow)

    def oval(self, x1, y1, x2, y2, fill, outline="#0b1b4d", width=2):
        self.canvas.create_oval(x1, y1, x2, y2, fill=fill, outline=outline, width=width)

    def draw_die_pair(self, separated=True, activated=False, contact=False, final=False, alignment=False):
        cx, die_w, die_h, dielectric_h = 500, 620, 72, 28
        gap = 120 if separated else 0
        top_y = 155
        bottom_y = top_y + die_h + gap
        if contact or final:
            bottom_y = top_y + die_h

        # Top die
        self.rect(cx - die_w/2, top_y, cx + die_w/2, top_y + die_h - dielectric_h, "#d8d8d8")
        self.rect(cx - die_w/2, top_y + die_h - dielectric_h, cx + die_w/2, top_y + die_h, "#d9edf7")
        # Bottom wafer
        self.rect(cx - die_w/2, bottom_y, cx + die_w/2, bottom_y + dielectric_h, "#d9edf7")
        self.rect(cx - die_w/2, bottom_y + dielectric_h, cx + die_w/2, bottom_y + die_h, "#d8d8d8")

        pad_w, pad_h = 55, 18
        for px in [cx - 210, cx, cx + 210]:
            self.rect(px - pad_w/2, top_y + die_h - dielectric_h + 6, px + pad_w/2, top_y + die_h, "#c97c3a", "#7a3e10")
            self.rect(px - pad_w/2, bottom_y, px + pad_w/2, bottom_y + pad_h, "#c97c3a", "#7a3e10")
            if contact or final:
                if final:
                    self.rect(px - pad_w/2 + 7, top_y + die_h - 2, px + pad_w/2 - 7, bottom_y + pad_h + 2, "#c97c3a", "#7a3e10")
                else:
                    self.line(px - pad_w/2, top_y + die_h, px + pad_w/2, top_y + die_h, "#8b4513")

        # Labels
        self.text(cx + die_w/2 + 35, top_y + die_h - 18, "Cu", 10, "#111", anchor="w")
        self.text(cx + die_w/2 + 35, top_y + die_h - 42, "Diélectrique", 10, "#111", anchor="w")
        if separated:
            self.text(cx - die_w/2 - 55, top_y + die_h/2, "Die", 12, "#111", "bold")
            self.text(cx - die_w/2 - 55, bottom_y + die_h/2, "Wafer", 12, "#111", "bold")

        if contact or final:
            self.line(cx - die_w/2, top_y + die_h, cx + die_w/2, top_y + die_h, "#0b1b4d", 2)
            if final:
                self.text(cx + die_w/2 + 35, top_y + die_h, "Interface\nhybride\nformée", 12, "#0b1b4d", "bold", anchor="w")
            else:
                self.text(cx + die_w/2 + 35, top_y + die_h, "Liaison\ndiélectrique\nD2D", 11, "#0b1b4d", anchor="w")
                self.text(cx + die_w/2 + 35, top_y + die_h + 55, "Contact initial\nCu-Cu", 11, "#8b4513", anchor="w")

        if alignment:
            self.line(cx, top_y - 25, cx, bottom_y + die_h + 25, "#666", 1, dash=(5, 4))
            self.line(cx, top_y + die_h + 25, cx, top_y + die_h + 55, "#0b1b4d", 4, arrow=tk.LAST)
            self.line(cx, bottom_y - 25, cx, bottom_y - 55, "#0b1b4d", 4, arrow=tk.LAST)
            for x in [cx - die_w/2 - 25, cx + die_w/2 + 25]:
                self.oval(x - 12, top_y + die_h - 12, x + 12, top_y + die_h + 12, "", "#0b1b4d")
                self.oval(x - 12, bottom_y - 12, x + 12, bottom_y + 12, "", "#0b1b4d")

        if activated:
            for x in [cx - 190, cx - 130, cx + 130, cx + 190]:
                self.text(x, top_y + die_h + 35, "✦", 28, "#6a1b9a", "bold")
            self.text(cx, top_y + die_h + 42, "Plasma", 15, "#6a1b9a", "bold")
            for x in [cx - 90, cx - 50, cx + 50, cx + 90]:
                self.line(x, top_y + die_h + 10, x + 22, bottom_y - 10, "#6a1b9a", 2, dash=(2, 6))

    def draw_cmp(self):
        cx, die_w = 500, 720
        top_y, bottom_y = 245, 340
        self.oval(cx - 80, 105, cx + 80, 155, "#d8d8d8")
        self.oval(cx - 50, 118, cx + 50, 142, "#c4c4c4", width=1)
        self.rect(cx - 12, 70, cx + 12, 108, "#bfbfbf")
        self.canvas.create_arc(cx - 140, 95, cx + 140, 175, start=20, extent=140, style=tk.ARC, outline="#004f9e", width=3)
        self.canvas.create_arc(cx - 140, 95, cx + 140, 175, start=200, extent=140, style=tk.ARC, outline="#004f9e", width=3)
        self.line(cx + 112, 118, cx + 135, 107, "#004f9e", 3, arrow=tk.LAST)
        self.line(cx - 112, 152, cx - 135, 163, "#004f9e", 3, arrow=tk.LAST)
        self.rect(cx - die_w/2, top_y, cx + die_w/2, top_y + 34, "#d9edf7")
        self.rect(cx - die_w/2, bottom_y, cx + die_w/2, bottom_y + 34, "#d9edf7")
        self.rect(cx - die_w/2, bottom_y + 34, cx + die_w/2, bottom_y + 65, "#d8d8d8")
        for px in [cx - 240, cx, cx + 240]:
            self.rect(px - 40, top_y + 10, px + 40, top_y + 34, "#c97c3a", "#7a3e10")
            self.rect(px - 40, bottom_y, px + 40, bottom_y + 24, "#c97c3a", "#7a3e10")
        self.line(cx - die_w/2, top_y - 12, cx + die_w/2, top_y - 12, "#777", 1, dash=(4, 4))
        self.text(cx, top_y - 28, "objectif : topographie faible, Cu recess contrôlé", 11, "#333")

    def draw_anneal(self):
        self.draw_die_pair(separated=False, final=True)
        for x in [420, 500, 580]:
            self.canvas.create_line(x, 400, x - 12, 430, x + 12, 455, x, 485, smooth=True, fill="#cc0000", width=3)
        self.text(500, 505, "Recuit", 14, "#cc0000", "bold")
        self.line(450, 488, 550, 488, "#cc0000")

    def draw_step(self, step: ProcessStep, cumulative_cost: float, cumulative_lca: float):
        self.clear()
        self.text(500, 30, "Hybrid Bonding — Processus étape par étape", 22, "#0b1b4d", "bold")
        self.text(500, 62, "Vue simplifiée avec calcul fictif coût / LCA", 12, "#333")
        self.text(500, 105, f"{step.step_id}. {step.title}", 20, "#0b1b4d", "bold")
        if step.step_id == 1:
            self.draw_die_pair(separated=True)
        elif step.step_id == 2:
            self.draw_cmp()
        elif step.step_id == 3:
            self.draw_die_pair(separated=True, activated=True)
        elif step.step_id == 4:
            self.draw_die_pair(separated=True, alignment=True)
        elif step.step_id == 5:
            self.draw_die_pair(separated=False, contact=True)
        elif step.step_id == 6:
            self.draw_anneal()

        self.rect(35, 410, 965, 505, "#ffffff", "#0b1b4d")
        self.text(55, 428, "Description", 13, "#0b1b4d", "bold", anchor="w")
        self.canvas.create_text(55, 455, text=step.description, fill="#111", font=("Segoe UI", 10), anchor="nw", justify="left", width=530)
        step_cost = compute_step_cost(step)
        step_lca = compute_step_lca(step)
        self.rect(625, 425, 945, 492, "#f8fbff", "#0b1b4d", 1)
        self.text(645, 440, f"Coût étape : {step_cost:,.0f} $", 11, "#0b1b4d", "bold", anchor="w")
        self.text(645, 462, f"LCA étape : {step_lca:.2f} kg CO₂e", 11, "#0b1b4d", "bold", anchor="w")
        self.text(645, 484, f"Cumul : {cumulative_cost:,.0f} $ / {cumulative_lca:.2f} kg CO₂e", 10, "#333", anchor="w")
        y = 525
        self.text(45, y, "Paramètres critiques :", 11, "#0b1b4d", "bold", anchor="w")
        x = 210
        for k, v in step.critical_params.items():
            self.text(x, y, f"{k} = {v}", 9, "#333", anchor="w")
            x += 240


class HybridBondingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Hybrid Bonding Process Viewer — Cost / LCA")
        self.root.geometry("1060x760")
        self.root.minsize(1000, 720)
        self.steps = build_default_process()
        self.index = 0
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(main, width=1000, height=580, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.drawer = ProcessCanvas(self.canvas)
        controls = ttk.Frame(main)
        controls.pack(fill=tk.X, pady=10)
        self.prev_btn = ttk.Button(controls, text="← Étape précédente", command=self.previous_step)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        self.next_btn = ttk.Button(controls, text="Étape suivante →", command=self.next_step)
        self.next_btn.pack(side=tk.LEFT, padx=5)
        self.reset_btn = ttk.Button(controls, text="Reset", command=self.reset)
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        self.export_btn = ttk.Button(controls, text="Exporter CSV", command=self.export_csv)
        self.export_btn.pack(side=tk.LEFT, padx=5)
        self.step_label = ttk.Label(controls, text="")
        self.step_label.pack(side=tk.RIGHT, padx=5)

        table_frame = ttk.LabelFrame(main, text="Résumé coût / LCA")
        table_frame.pack(fill=tk.X, pady=5)
        columns = ("step", "title", "cost", "lca", "cum_cost", "cum_lca")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=6)
        for col, text, width, anchor in [
            ("step", "Étape", 60, "center"),
            ("title", "Process", 260, "w"),
            ("cost", "Coût étape [$]", 130, "e"),
            ("lca", "LCA étape [kg CO₂e]", 150, "e"),
            ("cum_cost", "Coût cumulé [$]", 130, "e"),
            ("cum_lca", "LCA cumulée [kg CO₂e]", 150, "e"),
        ]:
            self.table.heading(col, text=text)
            self.table.column(col, width=width, anchor=anchor)
        self.table.pack(fill=tk.X)

    def cumulative_until_current(self):
        cost = sum(compute_step_cost(s) for s in self.steps[: self.index + 1])
        lca = sum(compute_step_lca(s) for s in self.steps[: self.index + 1])
        return cost, lca

    def refresh(self):
        step = self.steps[self.index]
        cumulative_cost, cumulative_lca = self.cumulative_until_current()
        self.drawer.draw_step(step, cumulative_cost, cumulative_lca)
        self.step_label.config(text=f"Étape {self.index + 1} / {len(self.steps)}")
        self.prev_btn.config(state=tk.NORMAL if self.index > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.index < len(self.steps) - 1 else tk.DISABLED)
        self.refresh_table()

    def refresh_table(self):
        for item in self.table.get_children():
            self.table.delete(item)
        cum_cost = 0.0
        cum_lca = 0.0
        for i, step in enumerate(self.steps):
            cost = compute_step_cost(step)
            lca = compute_step_lca(step)
            cum_cost += cost
            cum_lca += lca
            tag = "current" if i == self.index else ""
            self.table.insert("", tk.END, values=(step.step_id, step.title, f"{cost:,.0f}", f"{lca:.2f}", f"{cum_cost:,.0f}", f"{cum_lca:.2f}"), tags=(tag,))
        self.table.tag_configure("current", background="#dbeafe")

    def next_step(self):
        if self.index < len(self.steps) - 1:
            self.index += 1
            self.refresh()

    def previous_step(self):
        if self.index > 0:
            self.index -= 1
            self.refresh()

    def reset(self):
        self.index = 0
        self.refresh()

    def export_csv(self):
        path = filedialog.asksaveasfilename(title="Exporter le résumé coût / LCA", defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        cum_cost = 0.0
        cum_lca = 0.0
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["step_id", "title", "step_cost_usd", "step_lca_kgco2e", "cumulative_cost_usd", "cumulative_lca_kgco2e"])
            for step in self.steps:
                cost = compute_step_cost(step)
                lca = compute_step_lca(step)
                cum_cost += cost
                cum_lca += lca
                writer.writerow([step.step_id, step.title, round(cost, 2), round(lca, 4), round(cum_cost, 2), round(cum_lca, 4)])
        messagebox.showinfo("Export CSV", f"Fichier exporté :\n{path}")


def main():
    root = tk.Tk()
    HybridBondingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
