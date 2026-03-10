import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys

ROOT_BG   = "#0d1117"
CARD_BG   = "#161b22"
BTN_BG    = "#1e90ff"
BTN_HOV   = "#3aa0ff"
TXT_CLR   = "#e6f1ff"
MUTED     = "#8b949e"
BORDER    = "#30363d"
ORANGE    = "#f0883e"
ORANGE_HOV= "#f5a461"

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR  = os.path.join(PROJECT_DIR, "models")


def hover(btn, normal, hovered):
    btn.bind("<Enter>", lambda e: btn.config(bg=hovered))
    btn.bind("<Leave>", lambda e: btn.config(bg=normal))


def launch_ursina(model_name: str):
    interaction_file = os.path.join(PROJECT_DIR, "trial2.py")
    if not os.path.exists(interaction_file):
        messagebox.showerror("Error", "trial2.py not found")
        return
    subprocess.Popen([sys.executable, interaction_file, model_name], cwd=PROJECT_DIR)


def open_model_selector():
    if not os.path.exists(MODELS_DIR):
        messagebox.showerror("Error", "models/ folder not found")
        return

    win = tk.Toplevel(root)
    win.title("Select Model")
    win.geometry("440x420")
    win.configure(bg=ROOT_BG)
    win.resizable(False, False)
    win.grab_set()

    # Header
    tk.Label(win, text="Select a Model", fg=TXT_CLR, bg=ROOT_BG,
             font=("Segoe UI", 16, "bold")).pack(pady=(24, 4))
    tk.Label(win, text="Choose a .glb or .obj file to open", fg=MUTED, bg=ROOT_BG,
             font=("Segoe UI", 10)).pack(pady=(0, 16))

    # Scrollable list area
    frame = tk.Frame(win, bg=ROOT_BG)
    frame.pack(fill="both", expand=True, padx=28, pady=(0, 24))

    canvas  = tk.Canvas(frame, bg=ROOT_BG, highlightthickness=0)
    scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    inner   = tk.Frame(canvas, bg=ROOT_BG)

    inner.bind("<Configure>",
               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    models = [f for f in os.listdir(MODELS_DIR)
              if f.lower().endswith((".glb", ".obj"))]

    if not models:
        tk.Label(inner, text="No models found in models/",
                 fg="red", bg=ROOT_BG, font=("Segoe UI", 11)).pack(pady=20)
        return

    for model in models:
        btn = tk.Button(
            inner,
            text=model,
            anchor="w",
            padx=14,
            width=34,
            height=1,
            bg=CARD_BG,
            fg=TXT_CLR,
            activebackground=BTN_BG,
            activeforeground="white",
            font=("Segoe UI", 11),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=lambda m=model: (win.destroy(), launch_ursina(m))
        )
        btn.pack(pady=4, fill="x")
        hover(btn, CARD_BG, BTN_BG)


def show_controls():
    win = tk.Toplevel(root)
    win.title("Gesture Controls")
    win.geometry("380x340")
    win.configure(bg=ROOT_BG)
    win.resizable(False, False)
    win.grab_set()

    tk.Label(win, text="Gesture Controls", fg=TXT_CLR, bg=ROOT_BG,
             font=("Segoe UI", 15, "bold")).pack(pady=(22, 4))
    tk.Label(win, text="Use your hands to control the viewer",
             fg=MUTED, bg=ROOT_BG, font=("Segoe UI", 10)).pack(pady=(0, 16))

    card = tk.Frame(win, bg=CARD_BG, padx=20, pady=14)
    card.pack(padx=28, fill="x")

    rows = [
        ("RIGHT HAND", None),
        ("Index finger move", "Rotate"),
        ("Pinch gesture",     "Zoom"),
        ("Peace sign (paused)", "Screenshot"),
        ("", None),
        ("LEFT HAND", None),
        ("Open palm",         "Pause"),
        ("Wrist move",        "Translate"),
    ]

    for label, value in rows:
        if value is None:
            tk.Label(card, text=label, fg=BTN_BG, bg=CARD_BG,
                     font=("Segoe UI", 10, "bold"),
                     anchor="w").pack(fill="x", pady=(6, 2))
        else:
            row = tk.Frame(card, bg=CARD_BG)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, fg=MUTED, bg=CARD_BG,
                     font=("Segoe UI", 10), anchor="w", width=24).pack(side="left")
            tk.Label(row, text=value, fg=TXT_CLR, bg=CARD_BG,
                     font=("Segoe UI", 10, "bold"), anchor="w").pack(side="left")

    close_btn = tk.Button(
        win, text="Close", width=14, height=1,
        bg=CARD_BG, fg=TXT_CLR, activebackground=BORDER,
        font=("Segoe UI", 10), relief="flat", bd=0, cursor="hand2",
        command=win.destroy
    )
    close_btn.pack(pady=20)
    hover(close_btn, CARD_BG, BORDER)


# ── Main window ───────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("3D Interaction Controller")
root.geometry("560x380")
root.configure(bg=ROOT_BG)
root.resizable(False, False)

# Thin top accent line
tk.Frame(root, bg=BTN_BG, height=3).pack(fill="x")

# Title section
tk.Label(root, text="3D Interaction Controller",
         fg=TXT_CLR, bg=ROOT_BG,
         font=("Segoe UI", 22, "bold")).pack(pady=(36, 6))

tk.Label(root, text="Gesture-based 3D object manipulation",
         fg=MUTED, bg=ROOT_BG,
         font=("Segoe UI", 11)).pack()

# Divider
tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=48, pady=30)

# Buttons
btn_frame = tk.Frame(root, bg=ROOT_BG)
btn_frame.pack()

start_btn = tk.Button(
    btn_frame, text="Get Started", width=18, height=2,
    bg=BTN_BG, fg="white", activebackground=BTN_HOV, activeforeground="white",
    font=("Segoe UI", 12, "bold"), relief="flat", bd=0, cursor="hand2",
    command=open_model_selector
)
start_btn.grid(row=0, column=0, padx=10)
hover(start_btn, BTN_BG, BTN_HOV)

ctrl_btn = tk.Button(
    btn_frame, text="View Controls", width=18, height=2,
    bg=CARD_BG, fg=TXT_CLR, activebackground=BORDER, activeforeground=TXT_CLR,
    font=("Segoe UI", 12, "bold"), relief="flat", bd=0, cursor="hand2",
    command=show_controls
)
ctrl_btn.grid(row=0, column=1, padx=10)
hover(ctrl_btn, CARD_BG, BORDER)

# Footer
tk.Label(root, text="Place .glb or .obj files in the models/ folder",
         fg=MUTED, bg=ROOT_BG,
         font=("Segoe UI", 9)).pack(side="bottom", pady=18)

root.mainloop()