from turtle import color
from ursina import *
from PIL import ImageGrab
import cv2
import mediapipe as mp
import math
import numpy as np
import datetime
import os
import sys
from PIL import Image
import time
from panda3d.core import Texture as P3DTexture
import psutil

selected_model = None
if len(sys.argv) > 1:
    selected_model = sys.argv[1]

app = Ursina()
window.color = color.color(0, 0, 0.08)
os.makedirs("screenshots", exist_ok=True)

car = Entity(
    model=f"models/{selected_model}" if selected_model else "models/vintage_racing_car.glb",
    scale=1
)

try:
    min_b, max_b = car.model.get_tight_bounds()
except:
    min_b, max_b = car.get_tight_bounds()

center = (min_b + max_b) / 2
car.origin = center
car.position = Vec3(0, 0, 0)

size = max(max_b.x - min_b.x, max_b.y - min_b.y, max_b.z - min_b.z)
if size > 0:
    car.scale = 3 / size

camera.position = Vec3(0, 0, -12)
camera.look_at(car.position)

model_locked = False
camera_locked = False
view_mode = "free"

def toggle_model_lock():
    global model_locked
    model_locked = not model_locked
    model_btn.text = f"Model Lock: {'ON' if model_locked else 'OFF'}"
    model_btn.color = color.color(0, 0, 0.30) if model_locked else color.color(0, 0, 0.20)

def set_view(mode):
    global view_mode, camera_locked
    view_mode = mode
    camera_locked = True
    if mode == "front":  camera.position = Vec3(0, 0, -12)
    elif mode == "side": camera.position = Vec3(12, 0, 0)
    elif mode == "top":  camera.position = Vec3(0, 12, 0)
    elif mode == "iso":  camera.position = Vec3(8, 6, -8)
    camera.look_at(car.position)

BTN = dict(
    color=color.color(0, 0, 0.20),
    highlight_color=color.color(0, 0, 0.35),
    text_color=color.white,
)

model_btn = Button("Model Lock: OFF", scale=(0.22, 0.055),
                   position=(-0.67, 0.42), **BTN, on_click=toggle_model_lock)

Text("View Presets", parent=camera.ui,
     position=(-0.67, 0.275), origin=(0, 0), scale=0.8, color=color.gray)

vbtn = dict(scale=(0.10, 0.050), **BTN)
Button("Front", position=(-0.725, 0.22), on_click=lambda: set_view("front"), **vbtn)
Button("Side",  position=(-0.615, 0.22), on_click=lambda: set_view("side"),  **vbtn)
Button("Top",   position=(-0.725, 0.16), on_click=lambda: set_view("top"),   **vbtn)
Button("ISO",   position=(-0.615, 0.16), on_click=lambda: set_view("iso"),   **vbtn)

alpha = 0.25
rot_sens = 2
trans_sens = 15
zoom_sens = 40

Text("Sensitivity", parent=camera.ui,
     position=(0.55, 0.05), scale=0.9, color=color.white)

Text("Rotation", parent=camera.ui,
     position=(0.55, -0.02), scale=0.7)
rot_slider = Slider(min=0.5, max=5, default=rot_sens, step=0.1,
                    position=(0.55, -0.06), scale=0.3)

Text("Translation", parent=camera.ui,
     position=(0.55, -0.14), scale=0.7)
trans_slider = Slider(min=5, max=30, default=trans_sens, step=1,
                      position=(0.55, -0.18), scale=0.3)

Text("Zoom", parent=camera.ui,
     position=(0.55, -0.26), scale=0.7)
zoom_slider = Slider(min=10, max=80, default=zoom_sens, step=1,
                     position=(0.55, -0.30), scale=0.3)

Text(
    "RIGHT HAND\n"
    "  Index finger  ->  Rotate\n"
    "  Pinch         ->  Zoom\n"
    "  Peace sign    ->  Screenshot\n\n"
    "LEFT HAND\n"
    "  Open palm     ->  Pause\n"
    "  Wrist move    ->  Translate",
    parent=camera.ui,
    position=(-0.785, 0.095),
    scale=0.72,
    color=color.color(0, 0, 0.75),
)

gesture_text = Text(
    "Gesture: None",
    parent=camera.ui,
    position=(0, 0.46),
    origin=(0, 0),
    scale=1.1,
    color=color.white,
)

fps_text = Text("FPS: --", parent=camera.ui,
                position=(0.68, 0.46), origin=(0, 0),
                scale=0.85, color=color.lime)
cpu_text = Text("CPU: --", parent=camera.ui,
                position=(0.68, 0.41), origin=(0, 0),
                scale=0.85, color=color.orange)
ram_text = Text("RAM: --", parent=camera.ui,
                position=(0.68, 0.36), origin=(0, 0),
                scale=0.85, color=color.cyan)

FEED_W, FEED_H = 320, 240

_p3d_tex = P3DTexture('camera_feed')
_p3d_tex.setup2dTexture(FEED_W, FEED_H, P3DTexture.TUnsignedByte, P3DTexture.FRgb)
_p3d_tex.setMagfilter(P3DTexture.FTLinear)
_p3d_tex.setMinfilter(P3DTexture.FTLinear)
buf = _p3d_tex.modifyRamImage()
memoryview(buf).cast('B')[:] = b'\x00' * (FEED_W * FEED_H * 3)

def _upload_frame(rgb_frame):
    small = cv2.resize(rgb_frame, (FEED_W, FEED_H), interpolation=cv2.INTER_LINEAR)
    small = np.flipud(small)
    small = np.ascontiguousarray(small, dtype=np.uint8)
    buf = _p3d_tex.modifyRamImage()
    memoryview(buf).cast('B')[:] = small.tobytes()
    _p3d_tex.setRamImage(buf)

Entity(parent=camera.ui, model='quad',
       scale=(0.445, 0.315), position=(-0.67, -0.335),
       color=color.color(0, 0, 0.35), origin=(0, 0), z=0.01)

camera_feed_view = Entity(
    parent=camera.ui, model='quad',
    scale=(0.44, 0.31), position=(-0.67, -0.335),
    origin=(0, 0),
)
camera_feed_view.model.setTexture(_p3d_tex)

Text("● LIVE", parent=camera.ui,
     position=(-0.67, -0.168), origin=(0, 0),
     scale=0.9, color=color.red)

screenshot_text = Text(
    "Screenshot Saved!",
    parent=camera.ui,
    position=(0, 0.35),
    origin=(0, 0),
    scale=1.2,
    color=color.cyan,
    enabled=False,
)

# ─────────────────────────────────────────────────────────────
#  HAND INITIALIZATION OVERLAY
# ─────────────────────────────────────────────────────────────
# States: "waiting"  -> no hand seen yet
#         "scanning" -> hand detected, filling progress bar
#         "locked"   -> hand registered, session active
#         "lost"     -> registered hand left frame, need re-init

INIT_HOLD_FRAMES  = 45   # frames hand must stay to lock (~1.5s @ 30fps)
LOST_GRACE_FRAMES = 10   # frames allowed out of frame before reset

init_state       = "waiting"
init_frames      = 0        # progress counter
lost_frames      = 0        # consecutive frames with missing registered hand
registered_hands = {}       # label -> True  (labels that are registered)

# Overlay panel — dark translucent quad behind the text
init_panel = Entity(
    parent=camera.ui, model='quad',
    scale=(0.55, 0.13), position=(0, 0.0),
    color=color.color(0, 0, 0.12, 0.88), origin=(0, 0), z=0.02,
    enabled=True,
)

init_status_text = Text(
    "✋  Show your hand(s) to begin",
    parent=camera.ui,
    position=(0, 0.03),
    origin=(0, 0),
    scale=1.05,
    color=color.yellow,
    enabled=True,
)

init_sub_text = Text(
    "Hold still while scanning…",
    parent=camera.ui,
    position=(0, -0.02),
    origin=(0, 0),
    scale=0.75,
    color=color.color(0, 0, 0.80),
    enabled=True,
)

# Progress bar: background + fill
init_bar_bg = Entity(
    parent=camera.ui, model='quad',
    scale=(0.42, 0.018), position=(0, -0.06),
    color=color.color(0, 0, 0.25), origin=(0, 0), z=0.02,
    enabled=True,
)
init_bar_fill = Entity(
    parent=camera.ui, model='quad',
    scale=(0.0, 0.014), position=(-0.21, -0.06),
    color=color.cyan, origin=(-0.5, 0), z=0.01,
    enabled=True,
)

def _set_init_overlay(enabled: bool):
    init_panel.enabled       = enabled
    init_status_text.enabled = enabled
    init_sub_text.enabled    = enabled
    init_bar_bg.enabled      = enabled
    init_bar_fill.enabled    = enabled

def _update_init_bar(fraction: float):
    """fraction in [0, 1]"""
    init_bar_fill.scale_x = 0.42 * max(0.0, min(1.0, fraction))


mp_hands   = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands      = mp_hands.Hands(max_num_hands=2,
                             min_detection_confidence=0.8,
                             min_tracking_confidence=0.8)
cap        = cv2.VideoCapture(0)

LEFT_STYLE  = mp_drawing.DrawingSpec(color=(0, 220, 0),    thickness=2, circle_radius=3)
RIGHT_STYLE = mp_drawing.DrawingSpec(color=(50, 180, 255), thickness=2, circle_radius=3)
LEFT_CONN   = mp_drawing.DrawingSpec(color=(0, 180, 0),    thickness=2)
RIGHT_CONN  = mp_drawing.DrawingSpec(color=(0, 130, 230),  thickness=2)

def is_open_palm_relaxed(hand):
    lm = hand.landmark
    tips, bases = [8, 12, 16], [5, 9, 13]
    return sum(lm[t].y < lm[b].y - 0.01 for t, b in zip(tips, bases)) >= 2

def is_peace(hand):
    lm = hand.landmark
    return lm[8].y < lm[6].y and lm[12].y < lm[10].y and lm[16].y > lm[14].y

def is_pinch(hand):
    lm = hand.landmark
    return math.dist((lm[4].x, lm[4].y), (lm[8].x, lm[8].y)) < 0.05


smooth_rx = smooth_ry = smooth_tx = smooth_ty = 0
last_rx = last_ry = last_lx = last_ly = None
last_zoom = None
smooth_zoom = 0
paused = False
PAUSE_FRAMES = 0
screenshot_cooldown = 0
screenshot_timer = 0


def _reset_init():
    """Go back to waiting state, clear registered hands."""
    global init_state, init_frames, lost_frames, registered_hands
    global last_rx, last_ry, last_lx, last_ly, last_zoom
    global smooth_rx, smooth_ry, smooth_tx, smooth_ty, smooth_zoom, paused, PAUSE_FRAMES
    init_state       = "waiting"
    init_frames      = 0
    lost_frames      = 0
    registered_hands = {}
    last_rx = last_ry = last_lx = last_ly = last_zoom = None
    smooth_rx = smooth_ry = smooth_tx = smooth_ty = smooth_zoom = 0
    paused = False
    PAUSE_FRAMES = 0
    _update_init_bar(0)
    _set_init_overlay(True)
    init_status_text.text  = "✋  Show your hand(s) to begin"
    init_status_text.color = color.yellow
    init_sub_text.text     = "Hold still while scanning…"


def update():
    global last_rx, last_ry, last_lx, last_ly, smooth_rx, smooth_ry
    global smooth_tx, smooth_ty, last_zoom, smooth_zoom, PAUSE_FRAMES, paused
    global screenshot_cooldown, screenshot_timer
    global rot_sens, trans_sens, zoom_sens
    global init_state, init_frames, lost_frames, registered_hands

    rot_sens   = rot_slider.value
    trans_sens = trans_slider.value
    zoom_sens  = zoom_slider.value

    fps = int(1 / time.dt) if time.dt > 0 else 0
    fps_text.text = f"FPS: {fps}"
    cpu_text.text = f"CPU: {psutil.cpu_percent(interval=None):.0f}%"
    ram_text.text = f"RAM: {psutil.virtual_memory().percent:.0f}%"

    ok, frame = cap.read()
    if not ok:
        return

    frame = cv2.flip(frame, 1)
    rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res   = hands.process(rgb)

    # Build a dict of what mediapipe sees this frame: label -> landmark object
    seen_this_frame = {}   # {"Left": lm, "Right": lm}
    if res.multi_hand_landmarks and res.multi_handedness:
        for i, h in enumerate(res.multi_handedness):
            label = h.classification[0].label
            seen_this_frame[label] = res.multi_hand_landmarks[i]

    h_px, w_px, _ = frame.shape

    # ── INITIALIZATION STATE MACHINE ──────────────────────────────────────────
    if init_state != "locked":
        if not seen_this_frame:
            # No hand visible → reset progress
            init_frames = 0
            _update_init_bar(0)
            if init_state != "waiting":
                init_state = "waiting"
                init_status_text.text  = "✋  Show your hand(s) to begin"
                init_status_text.color = color.yellow
                init_sub_text.text     = "Hold still while scanning…"
        else:
            # Hand(s) visible → accumulate
            init_state   = "scanning"
            init_frames += 1
            fraction     = init_frames / INIT_HOLD_FRAMES
            _update_init_bar(fraction)

            # Pulse status text
            if init_frames % 10 < 5:
                init_status_text.text = "🔍  Scanning…"
            else:
                init_status_text.text = "🔍  Hold steady…"
            init_status_text.color = color.orange

            if init_frames >= INIT_HOLD_FRAMES:
                # Lock whatever hands are currently in view
                registered_hands = {label: True for label in seen_this_frame}
                init_state       = "locked"
                lost_frames      = 0
                _update_init_bar(1.0)
                _set_init_overlay(False)   # hide overlay — session is live

        # While not locked, draw skeletons but do NOT control model
        _draw_skeletons(rgb, seen_this_frame, res)
        _upload_frame(rgb)
        gesture_text.text  = f"Init: {init_state.upper()}"
        gesture_text.color = color.orange
        return   # ← skip all gesture/model logic until locked

    # ── SESSION ACTIVE (locked) ────────────────────────────────────────────────
    # Filter: only allow registered hands
    left  = seen_this_frame.get("Left")  if "Left"  in registered_hands else None
    right = seen_this_frame.get("Right") if "Right" in registered_hands else None

    # Check if registered hand(s) are still in frame
    any_registered_visible = any(lbl in seen_this_frame for lbl in registered_hands)
    if not any_registered_visible:
        lost_frames += 1
        if lost_frames >= LOST_GRACE_FRAMES:
            # Hand gone too long — reset
            _reset_init()
            _upload_frame(rgb)
            gesture_text.text  = "Gesture: None"
            gesture_text.color = color.white
            return
    else:
        lost_frames = 0

    # Warn user if hand is about to be lost (grace period in progress)
    if lost_frames > 0:
        gesture_text.text  = f"⚠ Hand lost! Re-init in {LOST_GRACE_FRAMES - lost_frames}…"
        gesture_text.color = color.red
    
    # ── PAUSE DETECTION ───────────────────────────────────────────────────────
    if left and is_open_palm_relaxed(left):
        PAUSE_FRAMES += 1
    else:
        PAUSE_FRAMES = 0
    paused = PAUSE_FRAMES >= 3

    current_gest = "None"

    if paused:
        current_gest = "Paused"
        last_rx = last_ry = last_lx = last_ly = last_zoom = None
        if right and is_peace(right) and screenshot_cooldown == 0:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            ImageGrab.grab().save(f"screenshots/shot_{ts}.png")
            screenshot_text.enabled = True
            screenshot_timer        = 2.0
            screenshot_cooldown     = 25
    else:
        if right and not model_locked and not is_pinch(right):
            current_gest = "Rotating"
            ix = int(right.landmark[8].x * w_px)
            iy = int(right.landmark[8].y * h_px)
            if last_rx is not None:
                dx, dy = ix - last_rx, iy - last_ry
                smooth_rx = smooth_rx * (1 - alpha) + (dy * rot_sens) * alpha
                smooth_ry = smooth_ry * (1 - alpha) + (-dx * rot_sens) * alpha
                car.rotation_x += smooth_rx
                car.rotation_y += smooth_ry
            last_rx, last_ry = ix, iy
        else:
            last_rx = last_ry = None

        if right and not camera_locked:
            current_gest += " + Zoom" if current_gest != "None" else "Zooming"
            lm = right.landmark
            pd = math.dist((lm[4].x, lm[4].y), (lm[8].x, lm[8].y))
            strength = 1 - min(1, max(0, (pd - 0.02) / 0.15))
            if last_zoom is not None:
                delta = (strength - last_zoom) * zoom_sens
                smooth_zoom = smooth_zoom * 0.65 + delta * 0.35
                camera.z = clamp(camera.z - smooth_zoom, -35, -3)
            last_zoom = strength
        else:
            last_zoom = None

        if left and not model_locked:
            current_gest = "Moving"
            lx = int(left.landmark[0].x * w_px)
            ly = int(left.landmark[0].y * h_px)
            if last_lx is not None:
                dx = (lx - last_lx) / w_px
                dy = (ly - last_ly) / h_px
                smooth_tx = smooth_tx * (1 - alpha) + dx * trans_sens * alpha
                smooth_ty = smooth_ty * (1 - alpha) + dy * trans_sens * alpha
                car.position += Vec3(smooth_tx, smooth_ty, 0)
            last_lx, last_ly = lx, ly
        else:
            last_lx = last_ly = None

    if lost_frames == 0:
        gesture_text.text  = f"Gesture: {current_gest}"
        gesture_text.color = color.red if paused else color.white

    # ── DRAW SKELETONS ────────────────────────────────────────────────────────
    _draw_skeletons(rgb, seen_this_frame, res, registered_hands)

    if paused:
        cv2.rectangle(rgb, (0, h_px // 2 - 20), (w_px, h_px // 2 + 20), (18, 18, 28), -1)
        cv2.putText(rgb, "-- PAUSED --", (w_px // 2 - 95, h_px // 2 + 7),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 210, 255), 2)

    _upload_frame(rgb)

    if screenshot_cooldown > 0:
        screenshot_cooldown -= 1
    if screenshot_timer > 0:
        screenshot_timer -= time.dt
    if screenshot_timer <= 0:
        screenshot_text.enabled = False


def _draw_skeletons(rgb, seen_this_frame, res, registered_hands=None):
    """Draw landmarks; ghost out unregistered hands when session is locked."""
    if not (res.multi_hand_landmarks and res.multi_handedness):
        return

    h_px, w_px, _ = rgb.shape

    for i, hand_lms in enumerate(res.multi_hand_landmarks):
        label = res.multi_handedness[i].classification[0].label

        # Decide colour: registered → normal, unregistered → dim red ghost
        if registered_hands is not None and label not in registered_hands:
            ns  = mp_drawing.DrawingSpec(color=(60, 30, 30),  thickness=1, circle_radius=2)
            cs  = mp_drawing.DrawingSpec(color=(50, 20, 20),  thickness=1)
            tag_col = (80, 30, 30)
            tag_label = f"{label.upper()} (ignored)"
        else:
            ns      = LEFT_STYLE  if label == "Left" else RIGHT_STYLE
            cs      = LEFT_CONN   if label == "Left" else RIGHT_CONN
            tag_col = (0, 220, 0) if label == "Left" else (50, 180, 255)
            tag_label = label.upper()

        wx = int(hand_lms.landmark[0].x * w_px)
        wy = int(hand_lms.landmark[0].y * h_px)
        cv2.putText(rgb, tag_label, (wx - 20, wy + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, tag_col, 2)
        mp_drawing.draw_landmarks(rgb, hand_lms, mp_hands.HAND_CONNECTIONS,
                                  landmark_drawing_spec=ns,
                                  connection_drawing_spec=cs)


app.run()
cap.release()
cv2.destroyAllWindows()