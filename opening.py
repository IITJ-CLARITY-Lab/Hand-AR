import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import sys



ROOT_BG = "#05070d"
BTN_BG = "#1e90ff"
TXT_CLR = "#e6f1ff"

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(PROJECT_DIR, "models")


def launch_ursina(model_name: str):
    interaction_file = os.path.join(PROJECT_DIR, "trial2.py")

    if not os.path.exists(interaction_file):
        messagebox.showerror("Error", "trial2.py not found")
        return

    subprocess.Popen(
        [sys.executable, interaction_file, model_name],
        cwd=PROJECT_DIR
    )


def open_model_selector():
    if not os.path.exists(MODELS_DIR):
        messagebox.showerror("Error", "models/ folder not found")
        return

    win = tk.Toplevel(root)
    win.title("Select Object")
    win.geometry("500x400")
    win.configure(bg=ROOT_BG)
    win.resizable(False, False)

    tk.Label(
        win,
        text="SELECT OBJECT",
        fg=TXT_CLR,
        bg=ROOT_BG,
        font=("Arial", 18, "bold")
    ).pack(pady=15)

    container = tk.Frame(win, bg=ROOT_BG)
    container.pack(expand=True)

    models = [
        f for f in os.listdir(MODELS_DIR)
        if f.lower().endswith((".glb", ".obj"))
    ]

    if not models:
        tk.Label(
            container,
            text="No models found",
            fg="red",
            bg=ROOT_BG
        ).pack()
        return

    for model in models:
        tk.Button(
            container,
            text=model,
            width=30,
            height=2,
            bg=BTN_BG,
            fg="white",
            font=("Arial", 11, "bold"),
            command=lambda m=model: (
                win.destroy(),
                launch_ursina(m)
            )
        ).pack(pady=8)


def show_controls():
    controls = """
RIGHT HAND
• Index Move → Rotate
• Thumb + Index → Zoom
• Thumbs Up (Paused) → Reset

LEFT HAND
• Wrist Move → Translate
• Open Palm → Pause
"""
    messagebox.showinfo("Gesture Controls", controls)


root = tk.Tk()
root.title("3D Interaction Controller")
root.geometry("700x450")
root.configure(bg=ROOT_BG)
root.resizable(False, False)

tk.Label(
    root,
    text="3D INTERACTION CONTROLLER",
    fg=TXT_CLR,
    bg=ROOT_BG,
    font=("Arial", 26, "bold")
).pack(pady=40)

tk.Label(
    root,
    text="Gesture-based 3D object manipulation",
    fg="#9bbcff",
    bg=ROOT_BG,
    font=("Arial", 12)
).pack(pady=5)

btn_frame = tk.Frame(root, bg=ROOT_BG)
btn_frame.pack(pady=40)

tk.Button(
    btn_frame,
    text="GET STARTED",
    width=22,
    height=2,
    bg=BTN_BG,
    fg="white",
    font=("Arial", 12, "bold"),
    command=open_model_selector
).pack(pady=10)

tk.Button(
    btn_frame,
    text="VIEW CONTROLS",
    width=22,
    height=2,
    bg="#ff9800",
    fg="black",
    font=("Arial", 12, "bold"),
    command=show_controls
).pack(pady=10)

root.mainloop()
