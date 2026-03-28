"""
3D Interaction Controller — Launcher
Aesthetic: Dark terminal / blueprint — sharp, technical, confident.
"""

import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys
import math
import time

# ── Palette ───────────────────────────────────────────────────────────────────
BG        = "#080c10"
BG2       = "#0d1520"
PANEL     = "#0f1923"
PANEL2    = "#141e2b"
ACCENT    = "#00d4ff"       # electric cyan
ACCENT2   = "#0077ff"       # deep blue
ACCENT_DIM= "#003d5c"
GREEN     = "#00ff88"
ORANGE    = "#ff6b35"
TEXT      = "#e8f4fd"
TEXT_DIM  = "#4a7a99"
TEXT_MUTE = "#243447"
BORDER    = "#1a2d3d"
BORDER_HI = "#00d4ff"

# ── Fonts ─────────────────────────────────────────────────────────────────────
# Use Courier New as mono fallback — feels very technical/terminal
FONT_TITLE  = ("Courier New", 26, "bold")
FONT_SUB    = ("Courier New", 10, "normal")
FONT_LABEL  = ("Courier New", 9,  "normal")
FONT_BTN    = ("Courier New", 11, "bold")
FONT_BTN_SM = ("Courier New", 9,  "bold")
FONT_MONO   = ("Courier New", 8,  "normal")
FONT_HDR    = ("Courier New", 12, "bold")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR  = os.path.join(PROJECT_DIR, "models")


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _btn_hover(btn, normal_bg, hover_bg, normal_fg=TEXT, hover_fg=BG):
    btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg, fg=hover_fg))
    btn.bind("<Leave>", lambda e: btn.config(bg=normal_bg, fg=normal_fg))


def _make_toplevel(parent, title, w, h):
    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry(f"{w}x{h}")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.grab_set()
    # Thin accent top border
    tk.Frame(win, bg=ACCENT, height=2).pack(fill="x")
    return win


def _corner_tag(canvas, x, y, size=10, color=ACCENT_DIM):
    """Draw a corner bracket at (x,y). Used for technical framing."""
    canvas.create_line(x, y + size, x, y, x + size, y, fill=color, width=1)


def _draw_grid(canvas, w, h, step=28, color="#0a1520"):
    for x in range(0, w, step):
        canvas.create_line(x, 0, x, h, fill=color, width=1)
    for y in range(0, h, step):
        canvas.create_line(0, y, w, y, fill=color, width=1)


# ─────────────────────────────────────────────────────────────────────────────
#  Animated canvas header
# ─────────────────────────────────────────────────────────────────────────────

class HeaderCanvas(tk.Canvas):
    """Draws an animated blueprint-style graphic behind the title."""

    SPEED = 0.6   # rotation speed (degrees per 16 ms tick)

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self._angle = 0.0
        self._after_id = None
        self.bind("<Destroy>", lambda e: self._stop())
        self._draw()
        self._tick()

    def _stop(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    def _tick(self):
        self._angle = (self._angle + self.SPEED) % 360
        self._draw()
        self._after_id = self.after(16, self._tick)

    def _draw(self):
        self.delete("all")
        w = int(self["width"])
        h = int(self["height"])
        cx, cy = w // 2, h // 2

        # Background grid
        _draw_grid(self, w, h, step=24, color="#090f18")

        # Rotating outer ring
        r_outer = 54
        r_inner = 40
        a = math.radians(self._angle)

        # Dashed orbit ring
        for i in range(0, 360, 6):
            ia = math.radians(i)
            x0 = cx + r_outer * math.cos(ia)
            y0 = cy + r_outer * math.sin(ia)
            if i % 12 == 0:
                self.create_oval(x0-1.5, y0-1.5, x0+1.5, y0+1.5, fill=ACCENT_DIM, outline="")

        # 3 rotating spoke tips
        for k in range(3):
            ak = a + math.radians(k * 120)
            x1 = cx + r_inner * math.cos(ak)
            y1 = cy + r_inner * math.sin(ak)
            x2 = cx + r_outer * math.cos(ak)
            y2 = cy + r_outer * math.sin(ak)
            self.create_line(cx, cy, x2, y2, fill=ACCENT_DIM, width=1)
            self.create_oval(x2-3, y2-3, x2+3, y2+3, fill=ACCENT, outline="")
            # small crosshair at spoke tip
            self.create_line(x2-5, y2, x2+5, y2, fill=ACCENT, width=1)
            self.create_line(x2, y2-5, x2, y2+5, fill=ACCENT, width=1)

        # Counter-rotating inner triangle
        for k in range(3):
            ak = -a * 1.5 + math.radians(k * 120)
            bk = -a * 1.5 + math.radians((k+1) * 120)
            x1 = cx + 22 * math.cos(ak)
            y1 = cy + 22 * math.sin(ak)
            x2 = cx + 22 * math.cos(bk)
            y2 = cy + 22 * math.sin(bk)
            self.create_line(x1, y1, x2, y2, fill=ACCENT2, width=1)

        # Centre dot
        self.create_oval(cx-5, cy-5, cx+5, cy+5, fill=ACCENT, outline=BG, width=2)
        self.create_oval(cx-2, cy-2, cx+2, cy+2, fill="white", outline="")

        # Corner brackets around canvas
        pad = 8
        size = 14
        for bx, by in [(pad, pad), (w-pad-size, pad),
                       (pad, h-pad-size), (w-pad-size, h-pad-size)]:
            _corner_tag(self, bx, by, size, ACCENT_DIM)

        # Scanline overlay — subtle horizontal lines
        for y in range(0, h, 4):
            self.create_line(0, y, w, y, fill="#0a0f18", width=1)


# ─────────────────────────────────────────────────────────────────────────────
#  Model selector window
# ─────────────────────────────────────────────────────────────────────────────

def launch_ursina(model_name: str):
    interaction_file = os.path.join(PROJECT_DIR, "main.py")
    if not os.path.exists(interaction_file):
        # fallback to trial2.py
        interaction_file = os.path.join(PROJECT_DIR, "trial2.py")
    if not os.path.exists(interaction_file):
        messagebox.showerror("Error", "main.py not found")
        return
    subprocess.Popen([sys.executable, interaction_file, model_name],
                     cwd=PROJECT_DIR)


def open_model_selector():
    if not os.path.exists(MODELS_DIR):
        messagebox.showerror("Error", "models/ folder not found")
        return

    win = _make_toplevel(root, "Select Model", 460, 460)

    # Header
    hdr = tk.Frame(win, bg=PANEL, pady=0)
    hdr.pack(fill="x")
    tk.Label(hdr, text="// SELECT MODEL", fg=ACCENT, bg=PANEL,
             font=FONT_HDR, padx=20, pady=14).pack(side="left")
    tk.Label(hdr, text=".glb  .obj", fg=TEXT_DIM, bg=PANEL,
             font=FONT_MONO).pack(side="right", padx=20)
    tk.Frame(win, bg=BORDER, height=1).pack(fill="x")

    # Status bar
    status = tk.Label(win, text="SCANNING models/ ...", fg=TEXT_DIM, bg=BG2,
                      font=FONT_MONO, anchor="w", padx=16, pady=6)
    status.pack(fill="x")

    # Scrollable model list
    outer = tk.Frame(win, bg=BG, padx=16, pady=12)
    outer.pack(fill="both", expand=True)

    canvas  = tk.Canvas(outer, bg=BG, highlightthickness=0, bd=0)
    sb      = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                           bg=BG, troughcolor=BG2, width=8)
    inner   = tk.Frame(canvas, bg=BG)

    inner.bind("<Configure>",
               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    # Mouse-wheel scroll
    canvas.bind_all("<MouseWheel>",
                    lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

    models = sorted([f for f in os.listdir(MODELS_DIR)
                     if f.lower().endswith((".glb", ".obj"))])

    if not models:
        tk.Label(inner, text="No models found in models/",
                 fg=ORANGE, bg=BG, font=FONT_LABEL, pady=20).pack()
        status.config(text="0 models found")
        return

    status.config(text=f"{len(models)} model(s) found")

    for idx, model in enumerate(models):
        ext  = os.path.splitext(model)[1].upper()
        name = os.path.splitext(model)[0]

        row = tk.Frame(inner, bg=PANEL, pady=0, cursor="hand2")
        row.pack(fill="x", pady=3)

        # Left accent bar
        accent_bar = tk.Frame(row, bg=ACCENT_DIM, width=3)
        accent_bar.pack(side="left", fill="y")

        # Index number
        tk.Label(row, text=f"{idx+1:02d}", fg=TEXT_MUTE, bg=PANEL,
                 font=FONT_MONO, padx=8, pady=10).pack(side="left")

        # Name + ext
        info = tk.Frame(row, bg=PANEL)
        info.pack(side="left", fill="both", expand=True, padx=4, pady=6)
        tk.Label(info, text=name, fg=TEXT, bg=PANEL,
                 font=("Courier New", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(info, text=ext, fg=ACCENT, bg=PANEL,
                 font=FONT_MONO, anchor="w").pack(fill="x")

        # Launch icon label
        arrow = tk.Label(row, text="  LOAD  >", fg=TEXT_DIM, bg=PANEL,
                         font=FONT_BTN_SM, padx=12)
        arrow.pack(side="right", fill="y")

        # Hover effects for the whole row
        def _make_hover(r, ab, ar):
            def on_enter(e):
                r.config(bg=PANEL2)
                ab.config(bg=ACCENT)
                ar.config(fg=ACCENT, bg=PANEL2)
                for child in r.winfo_children():
                    if child not in (ab, ar):
                        try:
                            child.config(bg=PANEL2)
                            for c2 in child.winfo_children():
                                c2.config(bg=PANEL2)
                        except Exception:
                            pass
            def on_leave(e):
                r.config(bg=PANEL)
                ab.config(bg=ACCENT_DIM)
                ar.config(fg=TEXT_DIM, bg=PANEL)
                for child in r.winfo_children():
                    if child not in (ab, ar):
                        try:
                            child.config(bg=PANEL)
                            for c2 in child.winfo_children():
                                c2.config(bg=PANEL)
                        except Exception:
                            pass
            r.bind("<Enter>",  on_enter)
            r.bind("<Leave>",  on_leave)
            for child in r.winfo_children():
                child.bind("<Enter>",  on_enter)
                child.bind("<Leave>",  on_leave)
                for c2 in child.winfo_children():
                    c2.bind("<Enter>",  on_enter)
                    c2.bind("<Leave>",  on_leave)

        def _make_click(m, r=row):
            def on_click(e):
                win.destroy()
                launch_ursina(m)
            for widget in _all_children(r):
                widget.bind("<Button-1>", on_click)
            r.bind("<Button-1>", on_click)

        _make_hover(row, accent_bar, arrow)
        _make_click(model)

    # Footer
    tk.Frame(win, bg=BORDER, height=1).pack(fill="x")
    tk.Label(win, text="Click a model to launch the viewer",
             fg=TEXT_DIM, bg=BG, font=FONT_MONO, pady=8).pack()


def _all_children(widget):
    children = list(widget.winfo_children())
    for child in widget.winfo_children():
        children.extend(_all_children(child))
    return children


# ─────────────────────────────────────────────────────────────────────────────
#  Controls window
# ─────────────────────────────────────────────────────────────────────────────

def show_controls():
    win = _make_toplevel(root, "Gesture Controls", 420, 400)

    tk.Label(win, text="// GESTURE CONTROLS", fg=ACCENT, bg=BG,
             font=FONT_HDR, pady=14).pack()
    tk.Frame(win, bg=BORDER, height=1).pack(fill="x", padx=20)

    card = tk.Frame(win, bg=PANEL, padx=24, pady=16)
    card.pack(padx=20, pady=16, fill="x")

    sections = [
        ("RIGHT HAND", [
            ("Index finger move",    "Rotate model"),
            ("Pinch (close)",        "Zoom in"),
            ("Pinch (apart)",        "Zoom out"),
            ("Peace sign [paused]",  "Screenshot"),
        ]),
        ("LEFT HAND", [
            ("Open palm",            "Pause all input"),
            ("Wrist move",           "Translate model"),
        ]),
    ]

    for section, rows in sections:
        # Section header with left stripe
        hdr_row = tk.Frame(card, bg=PANEL)
        hdr_row.pack(fill="x", pady=(10, 4))
        tk.Frame(hdr_row, bg=ACCENT, width=3, height=16).pack(side="left", padx=(0, 8))
        tk.Label(hdr_row, text=section, fg=ACCENT, bg=PANEL,
                 font=("Courier New", 9, "bold")).pack(side="left")

        for gesture, action in rows:
            row = tk.Frame(card, bg=PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"  {gesture}", fg=TEXT_DIM, bg=PANEL,
                     font=FONT_MONO, width=26, anchor="w").pack(side="left")
            tk.Label(row, text="->", fg=ACCENT_DIM, bg=PANEL,
                     font=FONT_MONO).pack(side="left", padx=4)
            tk.Label(row, text=action, fg=TEXT, bg=PANEL,
                     font=("Courier New", 9, "bold"), anchor="w").pack(side="left")

    # Tip box
    tip = tk.Frame(win, bg=ACCENT_DIM, padx=14, pady=10)
    tip.pack(padx=20, fill="x")
    tk.Label(tip, text="TIP  Hold open palm for ~0.25s to engage pause.",
             fg=ACCENT, bg=ACCENT_DIM, font=FONT_MONO, anchor="w").pack(fill="x")

    close_btn = tk.Button(
        win, text="[ CLOSE ]", width=14,
        bg=PANEL, fg=TEXT_DIM,
        activebackground=BORDER, activeforeground=TEXT,
        font=FONT_BTN_SM, relief="flat", bd=0, cursor="hand2",
        command=win.destroy
    )
    close_btn.pack(pady=16)
    _btn_hover(close_btn, PANEL, ACCENT, TEXT_DIM, BG)


# ─────────────────────────────────────────────────────────────────────────────
#  Main window
# ─────────────────────────────────────────────────────────────────────────────

root = tk.Tk()
root.title("3D Interaction Controller")
root.geometry("620x420")
root.configure(bg=BG)
root.resizable(False, False)

# Top accent line
tk.Frame(root, bg=ACCENT, height=2).pack(fill="x")

# ── Main layout: left graphic | right content ─────────────────────────────────
body = tk.Frame(root, bg=BG)
body.pack(fill="both", expand=True)

# Left panel — animated graphic
left = tk.Frame(body, bg=BG2, width=180)
left.pack(side="left", fill="y")
left.pack_propagate(False)

anim = HeaderCanvas(left, width=180, height=300,
                    bg=BG2, highlightthickness=0)
anim.pack(pady=(30, 0))

# Version / build tag
tk.Label(left, text="v2.0.0", fg=TEXT_MUTE, bg=BG2,
         font=FONT_MONO).pack(side="bottom", pady=10)
tk.Label(left, text="BUILD", fg=TEXT_MUTE, bg=BG2,
         font=FONT_MONO).pack(side="bottom")

# Vertical separator
tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

# Right panel — title + buttons
right = tk.Frame(body, bg=BG, padx=36)
right.pack(side="left", fill="both", expand=True)

# Spacer
tk.Frame(right, bg=BG, height=40).pack()

# Tag line above title
tk.Label(right, text="// GESTURE-BASED 3D VIEWER",
         fg=ACCENT, bg=BG, font=FONT_LABEL, anchor="w").pack(fill="x")

# Title
tk.Label(right, text="3D INTERACTION\nCONTROLLER",
         fg=TEXT, bg=BG, font=FONT_TITLE,
         justify="left", anchor="w", pady=4).pack(fill="x")

# Subtitle
tk.Label(right, text="Real-time hand gesture control for 3D model viewing",
         fg=TEXT_DIM, bg=BG, font=FONT_SUB,
         wraplength=340, justify="left", anchor="w").pack(fill="x", pady=(0, 28))

# Horizontal rule
tk.Frame(right, bg=BORDER, height=1).pack(fill="x", pady=(0, 24))

# Buttons
btn_area = tk.Frame(right, bg=BG)
btn_area.pack(anchor="w")

start_btn = tk.Button(
    btn_area,
    text="  GET STARTED  >",
    width=18, height=1,
    bg=ACCENT, fg=BG,
    activebackground=ACCENT2, activeforeground=TEXT,
    font=FONT_BTN, relief="flat", bd=0, cursor="hand2",
    pady=10,
    command=open_model_selector,
)
start_btn.grid(row=0, column=0, padx=(0, 10), pady=4)
_btn_hover(start_btn, ACCENT, ACCENT2, BG, TEXT)

ctrl_btn = tk.Button(
    btn_area,
    text="  VIEW CONTROLS",
    width=18, height=1,
    bg=PANEL, fg=TEXT_DIM,
    activebackground=PANEL2, activeforeground=TEXT,
    font=FONT_BTN, relief="flat", bd=0, cursor="hand2",
    pady=10,
    command=show_controls,
)
ctrl_btn.grid(row=0, column=1, pady=4)
_btn_hover(ctrl_btn, PANEL, PANEL2, TEXT_DIM, TEXT)

# Status row
tk.Frame(right, bg=BG, height=20).pack()
status_row = tk.Frame(right, bg=BG)
status_row.pack(anchor="w")

# Models count indicator
def _count_models():
    if os.path.exists(MODELS_DIR):
        n = len([f for f in os.listdir(MODELS_DIR)
                 if f.lower().endswith((".glb", ".obj"))])
        return n
    return 0

n = _count_models()
dot_color = GREEN if n > 0 else ORANGE
tk.Label(status_row, text="●", fg=dot_color, bg=BG,
         font=("Courier New", 10)).pack(side="left")
tk.Label(status_row, text=f"  {n} model(s) in models/",
         fg=TEXT_DIM, bg=BG, font=FONT_MONO).pack(side="left")

# Bottom bar
tk.Frame(root, bg=BORDER, height=1).pack(fill="x")
foot = tk.Frame(root, bg=BG2, pady=6)
foot.pack(fill="x")
tk.Label(foot, text="Place .glb or .obj files in the models/ folder",
         fg=TEXT_MUTE, bg=BG2, font=FONT_MONO).pack(side="left", padx=16)
tk.Label(foot, text="[  READY  ]",
         fg=GREEN, bg=BG2, font=FONT_MONO).pack(side="right", padx=16)

root.mainloop()