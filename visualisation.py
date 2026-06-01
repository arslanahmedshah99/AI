"""
Visualisation - Project Hail Mary Simulation
Tkinter GUI showing the grid in real-time + stats panel
"""

import tkinter as tk
from tkinter import ttk, font
import threading
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulation import Simulation, BatchRunner
from config import *


CELL_SIZE = 20
CANVAS_W = GRID_WIDTH * CELL_SIZE
CANVAS_H = GRID_HEIGHT * CELL_SIZE

# GUI Color palette (hex strings for tkinter)
GUI_COLORS = {
    EMPTY:            "#0d1117",
    ASTROPHAGE_CLOUD: "#8B0000",
    PLANET_ADRIAN:    "#1a5c3a",
    HAIL_MARY:        "#1a6bb5",
    BLIP_A:           "#b5621a",
    BEETLE_PROBE:     "#d4a017",
    RADIATION_ZONE:   "#5e2d80",
    DEBRIS_FIELD:     "#3d4142",
    TUNNEL:           "#1b6ca8",
    99:               "#ff0000",   # Fallback
}

GRACE_COLOR = "#00ff88"
ROCKY_COLOR = "#ff6b35"
BG = "#0d1117"
PANEL_BG = "#161b22"
TEXT_FG = "#c9d1d9"
ACCENT = "#58a6ff"


class HailMaryGUI:
    """
    Real-time Tkinter visualisation for the simulation.
    Shows:
    - 2D grid (space environment)
    - Agent positions (Grace=green, Rocky=orange)
    - Live stats panel
    - Event log
    - Controls: step, run, pause, batch-run
    """

    def __init__(self):
        self.sim = Simulation(run_id=1, seed=42, verbose=False)
        self.running = False
        self.paused = False
        self.speed_delay = 0.15   # seconds between auto-steps

        self._build_window()
        self._draw_grid()
        self._update_stats()

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title("Project Hail Mary — Multi-Agent Simulation")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        # ── Top: title ──────────────────────────────────────────────────
        title = tk.Label(self.root,
                         text="⚡ PROJECT HAIL MARY — AI SIMULATION",
                         bg=BG, fg=ACCENT,
                         font=("Courier New", 14, "bold"),
                         pady=6)
        title.pack(side=tk.TOP, fill=tk.X)

        # ── Main frame ──────────────────────────────────────────────────
        main_frame = tk.Frame(self.root, bg=BG)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # Left: canvas + controls
        left_frame = tk.Frame(main_frame, bg=BG)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH)

        self.canvas = tk.Canvas(left_frame,
                                width=CANVAS_W, height=CANVAS_H,
                                bg=BG, highlightthickness=1,
                                highlightbackground=ACCENT)
        self.canvas.pack()

        self._build_controls(left_frame)
        self._build_legend(left_frame)

        # Right: stats + log
        right_frame = tk.Frame(main_frame, bg=PANEL_BG,
                               width=360, padx=10, pady=8)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))
        right_frame.pack_propagate(False)

        self._build_stats_panel(right_frame)
        self._build_log_panel(right_frame)

    def _build_controls(self, parent):
        ctrl = tk.Frame(parent, bg=BG, pady=4)
        ctrl.pack(fill=tk.X)

        btn_style = {"bg": "#21262d", "fg": TEXT_FG,
                     "activebackground": "#30363d", "activeforeground": "#fff",
                     "relief": tk.FLAT, "padx": 10, "pady": 4,
                     "font": ("Courier New", 10), "cursor": "hand2"}

        tk.Button(ctrl, text="▶ Step",    command=self._step_once,     **btn_style).pack(side=tk.LEFT, padx=3)
        tk.Button(ctrl, text="⏩ Run",    command=self._start_run,     **btn_style).pack(side=tk.LEFT, padx=3)
        tk.Button(ctrl, text="⏸ Pause",  command=self._pause,         **btn_style).pack(side=tk.LEFT, padx=3)
        tk.Button(ctrl, text="↺ Reset",   command=self._reset,         **btn_style).pack(side=tk.LEFT, padx=3)
        tk.Button(ctrl, text="📊 Batch 20", command=self._run_batch,   **btn_style).pack(side=tk.LEFT, padx=3)

        # Speed slider
        tk.Label(ctrl, text="  Speed:", bg=BG, fg=TEXT_FG,
                 font=("Courier New", 9)).pack(side=tk.LEFT)
        self.speed_var = tk.DoubleVar(value=0.15)
        speed_slider = tk.Scale(ctrl, from_=0.02, to=0.5,
                                resolution=0.01, orient=tk.HORIZONTAL,
                                variable=self.speed_var, length=80,
                                bg=BG, fg=TEXT_FG, troughcolor="#21262d",
                                highlightthickness=0, showvalue=False)
        speed_slider.pack(side=tk.LEFT)

    def _build_legend(self, parent):
        leg = tk.Frame(parent, bg=BG, pady=2)
        leg.pack(fill=tk.X)

        items = [
            (HAIL_MARY,        "Hail Mary"),
            (BLIP_A,           "Blip-A"),
            (PLANET_ADRIAN,    "Adrian"),
            (ASTROPHAGE_CLOUD, "Astrophage"),
            (RADIATION_ZONE,   "Radiation"),
            (DEBRIS_FIELD,     "Debris"),
            (TUNNEL,           "Tunnel"),
        ]
        for cell_type, label in items:
            color = GUI_COLORS[cell_type]
            f = tk.Frame(leg, bg=BG)
            f.pack(side=tk.LEFT, padx=3)
            tk.Canvas(f, width=12, height=12, bg=color,
                      highlightthickness=0).pack(side=tk.LEFT)
            tk.Label(f, text=label, bg=BG, fg=TEXT_FG,
                     font=("Courier New", 8)).pack(side=tk.LEFT)

        # Agent legend
        for color, name in [(GRACE_COLOR, "Grace"), (ROCKY_COLOR, "Rocky")]:
            f = tk.Frame(leg, bg=BG)
            f.pack(side=tk.LEFT, padx=3)
            tk.Canvas(f, width=12, height=12, bg=color,
                      highlightthickness=0).pack(side=tk.LEFT)
            tk.Label(f, text=name, bg=BG, fg=TEXT_FG,
                     font=("Courier New", 8)).pack(side=tk.LEFT)

    def _build_stats_panel(self, parent):
        tk.Label(parent, text="MISSION STATUS", bg=PANEL_BG, fg=ACCENT,
                 font=("Courier New", 11, "bold")).pack(anchor="w", pady=(0, 4))

        self.stats_vars = {}
        fields = [
            ("turn",            "Turn"),
            ("phase",           "Phase"),
            ("grace_hp",        "Grace HP"),
            ("grace_energy",    "Grace Energy"),
            ("grace_knowledge", "Knowledge"),
            ("mission_score",   "Mission Score"),
            ("beetles",         "Beetles Deployed"),
            ("taumoeba_bred",   "Taumoeba Viable"),
            ("taumoeba_deploy", "Taumoeba Deployed"),
            ("experiments",     "Experiments"),
            ("rocky_trust",     "Rocky Trust"),
            ("astrophage_cnt",  "Astrophage Cells"),
            ("flashbacks",      "Flashbacks"),
        ]
        for key, label in fields:
            row = tk.Frame(parent, bg=PANEL_BG)
            row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=f"{label}:", bg=PANEL_BG, fg="#8b949e",
                     font=("Courier New", 9), width=18, anchor="w").pack(side=tk.LEFT)
            var = tk.StringVar(value="—")
            self.stats_vars[key] = var
            tk.Label(row, textvariable=var, bg=PANEL_BG, fg=TEXT_FG,
                     font=("Courier New", 9, "bold"), anchor="w").pack(side=tk.LEFT)

    def _build_log_panel(self, parent):
        tk.Label(parent, text="\nEVENT LOG", bg=PANEL_BG, fg=ACCENT,
                 font=("Courier New", 11, "bold")).pack(anchor="w")

        log_frame = tk.Frame(parent, bg=PANEL_BG)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_box = tk.Text(log_frame, bg="#0d1117", fg="#8b949e",
                               font=("Courier New", 8), wrap=tk.WORD,
                               state=tk.DISABLED, height=20,
                               yscrollcommand=scrollbar.set,
                               insertbackground=TEXT_FG)
        self.log_box.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_box.yview)

        # Color tags
        self.log_box.tag_config("grace",     foreground="#00ff88")
        self.log_box.tag_config("rocky",     foreground="#ff6b35")
        self.log_box.tag_config("flashback", foreground="#ffd700")
        self.log_box.tag_config("mission",   foreground="#58a6ff")
        self.log_box.tag_config("warning",   foreground="#f85149")
        self.log_box.tag_config("env",       foreground="#3d444d")

    # ─────────────────── DRAWING ───────────────────────────────────────

    def _draw_grid(self):
        """Redraw the entire canvas from current simulation state."""
        self.canvas.delete("all")
        env = self.sim.environment
        grace = self.sim.grace
        rocky = self.sim.rocky

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                cell = env.grid[y][x]
                color = GUI_COLORS.get(cell.cell_type, BG)

                # Adjust Astrophage color by intensity (darker=less dense, brighter=denser)
                if cell.cell_type == ASTROPHAGE_CLOUD:
                    intensity = cell.astrophage_intensity
                    r = int(100 + intensity * 120)
                    g = 0
                    b = 0
                    color = f"#{r:02x}{g:02x}{b:02x}"

                x1 = x * CELL_SIZE
                y1 = y * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE
                self.canvas.create_rectangle(x1, y1, x2, y2,
                                             fill=color, outline="#0d1117",
                                             width=0.3)

                # Taumoeba indicator (small dot)
                if cell.taumoeba_present:
                    cx, cy = x1 + CELL_SIZE // 2, y1 + CELL_SIZE // 2
                    r = 2
                    self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                            fill="#00ff44", outline="")

        # Draw agents (on top)
        self._draw_agent(grace.x, grace.y, GRACE_COLOR, "G")
        if rocky.alive:
            self._draw_agent(rocky.x, rocky.y, ROCKY_COLOR, "R")

        # Draw beetle probes
        for probe in grace.deployed_beetles:
            self._draw_agent(probe.x, probe.y, "#f1c40f", "B")

        self.canvas.update()

    def _draw_agent(self, x, y, color, letter):
        x1 = x * CELL_SIZE + 2
        y1 = y * CELL_SIZE + 2
        x2 = x * CELL_SIZE + CELL_SIZE - 2
        y2 = y * CELL_SIZE + CELL_SIZE - 2
        self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline="#fff", width=1.5)
        cx = x * CELL_SIZE + CELL_SIZE // 2
        cy = y * CELL_SIZE + CELL_SIZE // 2
        self.canvas.create_text(cx, cy, text=letter, fill="#000",
                                font=("Courier New", 8, "bold"))

    # ─────────────────── STATS UPDATE ──────────────────────────────────

    def _update_stats(self):
        g = self.sim.grace
        r = self.sim.rocky
        env = self.sim.environment

        self.stats_vars["turn"].set(str(self.sim.turn))
        self.stats_vars["phase"].set(g.mission_phase)
        self.stats_vars["grace_hp"].set(f"{g.health} / {g.max_health}")
        self.stats_vars["grace_energy"].set(f"{g.energy} / {g.max_energy}")
        self.stats_vars["grace_knowledge"].set(str(g.knowledge_score))
        self.stats_vars["mission_score"].set(str(g.mission_success_score))
        self.stats_vars["beetles"].set(f"{len(g.deployed_beetles)} / 4")
        self.stats_vars["taumoeba_bred"].set(
            "YES ✓" if (g.best_taumoeba and g.best_taumoeba.is_viable_for_earth()) else "No"
        )
        self.stats_vars["taumoeba_deploy"].set("YES ✓" if g.taumoeba_deployed else "No")
        self.stats_vars["experiments"].set(
            f"{g.experiments_total} ({g.experiments_successful} ok)"
        )
        trust_names = {0: "Strangers", 1: "Colleagues", 2: "Friends", 3: "Allies"}
        self.stats_vars["rocky_trust"].set(
            trust_names.get(r.trust_level, "?") + f" ({r.trust_level}/3)"
        )
        self.stats_vars["astrophage_cnt"].set(str(env.count_astrophage_cells()))
        self.stats_vars["flashbacks"].set(
            f"{len(g.flashbacks_seen)} / {len(FLASHBACK_EVENTS)}"
        )

    def _append_log(self, text):
        self.log_box.config(state=tk.NORMAL)
        # Colour by content
        tag = "env"
        tl = text.lower()
        if "grace" in tl:    tag = "grace"
        elif "rocky" in tl:  tag = "rocky"
        elif "flashback" in tl: tag = "flashback"
        elif "mission" in tl or "complete" in tl: tag = "mission"
        elif "abort" in tl or "died" in tl or "depleted" in tl: tag = "warning"

        self.log_box.insert(tk.END, text + "\n", tag)
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    # ─────────────────── CONTROLS ──────────────────────────────────────

    def _step_once(self):
        if self.sim.running:
            self.sim._tick()
            self._draw_grid()
            self._update_stats()
            # Log recent events
            if self.sim.event_log:
                self._append_log(self.sim.event_log[-1])

    def _start_run(self):
        if not self.running:
            self.running = True
            self.paused = False
            t = threading.Thread(target=self._auto_run, daemon=True)
            t.start()

    def _auto_run(self):
        while self.running and self.sim.running and self.sim.turn < self.sim.max_turns:
            if not self.paused:
                delay = self.speed_var.get()
                self.sim._tick()
                self.root.after(0, self._draw_grid)
                self.root.after(0, self._update_stats)
                if self.sim.event_log:
                    msg = self.sim.event_log[-1]
                    self.root.after(0, self._append_log, msg)
                time.sleep(delay)
        self.running = False
        self.root.after(0, self._append_log, "=== Simulation ended ===")

    def _pause(self):
        self.paused = not self.paused

    def _reset(self):
        self.running = False
        time.sleep(0.2)
        import random
        new_seed = random.randint(0, 99999)
        self.sim = Simulation(run_id=1, seed=new_seed, verbose=False)
        self._draw_grid()
        self._update_stats()
        self.log_box.config(state=tk.NORMAL)
        self.log_box.delete(1.0, tk.END)
        self.log_box.config(state=tk.DISABLED)
        self._append_log(f"New simulation started (seed={new_seed})")

    def _run_batch(self):
        """Run 20 simulations in a background thread and show results."""
        self._append_log("Starting batch run of 20 simulations...")

        def batch_thread():
            runner = BatchRunner(n_runs=20, verbose=False)
            runner.run_all()
            stats = runner.compute_statistics()
            self.root.after(0, self._show_batch_results, stats)

        t = threading.Thread(target=batch_thread, daemon=True)
        t.start()

    def _show_batch_results(self, stats):
        """Display batch results in a popup window."""
        win = tk.Toplevel(self.root)
        win.title("Batch Run Results — 20 Simulations")
        win.configure(bg=PANEL_BG)
        win.geometry("500x500")

        tk.Label(win, text="BATCH SIMULATION RESULTS (n=20)",
                 bg=PANEL_BG, fg=ACCENT,
                 font=("Courier New", 12, "bold"), pady=8).pack()

        text = tk.Text(win, bg="#0d1117", fg=TEXT_FG,
                       font=("Courier New", 10), wrap=tk.WORD, padx=10, pady=8)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        lines = [
            f"Runs:                    {stats['n_runs']}",
            f"Mission Complete Rate:   {stats['mission_complete_rate']:.1f}%",
            f"Grace Survival Rate:     {stats['grace_survival_rate']:.1f}%",
            f"Avg Turns Survived:      {stats['avg_turns_survived']:.1f}",
            f"Avg Knowledge (final):   {stats['avg_knowledge_final']:.1f}",
            f"Avg Mission Score:       {stats['avg_mission_score']:.1f}",
            f"Avg Beetles Deployed:    {stats['avg_beetles_deployed']:.2f} / 4",
            f"Taumoeba Bred Rate:       {stats['taumoeba_bred_rate']:.1f}%",
            f"Taumoeba Deployed Rate:  {stats['taumoeba_deployed_rate']:.1f}%",
            f"Avg Experiments:         {stats['avg_experiments']:.1f}",
            f"Avg Experiment Success:  {stats['avg_experiment_success_rate']*100:.1f}%",
            f"Avg Rocky Trust Level:   {stats['avg_trust_level']:.2f} / 3",
            f"Avg Astrophage (final):  {stats['avg_astrophage_final']:.1f} cells",
            f"Avg Flashbacks Seen:     {stats['avg_flashbacks']:.1f}",
            "",
            "End Conditions:",
        ]
        for k, v in stats["cause_of_end_breakdown"].items():
            lines.append(f"  {k:25s}: {v}")

        text.insert(tk.END, "\n".join(lines))
        text.config(state=tk.DISABLED)

        self._append_log(f"Batch complete: {stats['mission_complete_rate']:.1f}% mission success rate")

    def launch(self):
        self.root.mainloop()


def main():
    gui = HailMaryGUI()
    gui.launch()


if __name__ == "__main__":
    main()
