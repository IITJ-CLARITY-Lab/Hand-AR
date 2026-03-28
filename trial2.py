
from ursina import *
from panda3d.core import Texture as P3DTexture, Filename
from direct.showbase.ShowBase import ShowBase
import cv2
import mediapipe as mp
import math
import numpy as np
import datetime
import os
import sys
import time
import psutil

selected_model = None
if len(sys.argv) > 1:
    selected_model = sys.argv[1]

if selected_model:
    model_path = selected_model  # already absolute, trust it
    if not os.path.exists(model_path):
        print(f"ERROR: Model file not found: {model_path}")
        sys.exit(1)
else:
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(PROJECT_DIR, "models", "Old_Rusty_Car.glb")
    if not os.path.exists(model_path):
        print(f"ERROR: Default model not found: {model_path}")
        sys.exit(1)

app = Ursina()
window.color = color.color(0, 0, 0.08)
os.makedirs("screenshots", exist_ok=True)
# Load GLB directly via Panda3D loader, bypassing Ursina's asset system
panda_path = Filename.from_os_specific(model_path)  # model_path is your absolute path
loaded = base.loader.load_model(panda_path) 

if loaded is None:
    print(f"ERROR: Panda3D could not load model: {model_path}")
    sys.exit(1)

car = Entity()
loaded.reparent_to(car)
car.scale = 1

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

model_locked  = False
camera_locked = False
view_mode     = "free"

def toggle_model_lock():
    global model_locked
    model_locked = not model_locked
    model_btn.text  = f"Model Lock: {'ON' if model_locked else 'OFF'}"
    model_btn.color = color.color(0, 0, 0.30) if model_locked else color.color(0, 0, 0.20)

def set_view(mode):
    global view_mode, camera_locked
    view_mode     = mode
    camera_locked = True
    if mode == "front":  camera.position = Vec3(0,  0, -12)
    elif mode == "side": camera.position = Vec3(12, 0,   0)
    elif mode == "top":  camera.position = Vec3(0,  12,  0)
    elif mode == "iso":  camera.position = Vec3(8,  6,  -8)
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
btn_front = Button("Front", position=(-0.725, 0.22), on_click=lambda: set_view("front"), **vbtn)
btn_side  = Button("Side",  position=(-0.615, 0.22), on_click=lambda: set_view("side"),  **vbtn)
btn_top   = Button("Top",   position=(-0.725, 0.16), on_click=lambda: set_view("top"),   **vbtn)
btn_iso   = Button("ISO",   position=(-0.615, 0.16), on_click=lambda: set_view("iso"),   **vbtn)

# ── Smoothing constants ───────────────────────────────────────────────────────
ALPHA_ROT   = 0.12
ALPHA_TRANS = 0.10
ALPHA_ZOOM  = 0.10

ROT_DECAY   = 0.82
TRANS_DECAY = 0.80
ZOOM_DECAY  = 0.78

MAX_ROT_DELTA   = 60
MAX_TRANS_DELTA = 0.12
MAX_ZOOM_DELTA  = 0.06

# Pause needs this many CONSECUTIVE frames of open-palm before engaging,
# and will only RELEASE once open-palm is gone for PAUSE_RELEASE_FRAMES frames.
PAUSE_ENGAGE_FRAMES  = 8   # ~0.25 s  — quick enough to feel responsive
PAUSE_RELEASE_FRAMES = 6   # prevents flicker on the way out

rot_sens   = 2
trans_sens = 15
zoom_sens  = 40

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
    "  Pinch closer  ->  Zoom in\n"
    "  Pinch apart   ->  Zoom out\n"
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
    buf   = _p3d_tex.modifyRamImage()
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

Text("LIVE", parent=camera.ui,
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
INIT_HOLD_FRAMES  = 45
LOST_GRACE_FRAMES = 10

init_state       = "waiting"
init_frames      = 0
lost_frames      = 0
registered_hands = {}

init_panel = Entity(
    parent=camera.ui, model='quad',
    scale=(0.60, 0.13), position=(0, 0.0),
    color=color.color(0, 0, 0.12, 0.88), origin=(0, 0), z=0.02,
    enabled=True,
)

# No emoji — Ursina's default font doesn't support them (causes console spam)
init_status_text = Text(
    "Show your hand(s) to begin",
    parent=camera.ui,
    position=(0, 0.03),
    origin=(0, 0),
    scale=1.05,
    color=color.yellow,
    enabled=True,
)

init_sub_text = Text(
    "Hold still while scanning...",
    parent=camera.ui,
    position=(0, -0.02),
    origin=(0, 0),
    scale=0.75,
    color=color.color(0, 0, 0.80),
    enabled=True,
)

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
    init_bar_fill.scale_x = 0.42 * max(0.0, min(1.0, fraction))


mp_hands   = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands_det  = mp_hands.Hands(max_num_hands=2,
                              min_detection_confidence=0.8,
                              min_tracking_confidence=0.8)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("ERROR: Could not open camera.")
    for i in range(1, 5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"Successfully opened camera at index {i}")
            break
    else:
        print("FATAL: No camera found on any index")
        sys.exit(1)

LEFT_STYLE  = mp_drawing.DrawingSpec(color=(0,   220,   0), thickness=2, circle_radius=3)
RIGHT_STYLE = mp_drawing.DrawingSpec(color=(50,  180, 255), thickness=2, circle_radius=3)
LEFT_CONN   = mp_drawing.DrawingSpec(color=(0,   180,   0), thickness=2)
RIGHT_CONN  = mp_drawing.DrawingSpec(color=(0,   130, 230), thickness=2)

def is_open_palm_relaxed(hand):
    lm = hand.landmark
    tips, bases = [8, 12, 16], [5, 9, 13]
    return sum(lm[t].y < lm[b].y - 0.01 for t, b in zip(tips, bases)) >= 2

def is_peace(hand):
    lm = hand.landmark
    return (lm[8].y  < lm[6].y and
            lm[12].y < lm[10].y and
            lm[16].y > lm[14].y)

def pinch_distance(hand):
    """Raw distance between thumb tip (4) and index tip (8)."""
    lm = hand.landmark
    return math.dist((lm[4].x, lm[4].y), (lm[8].x, lm[8].y))

def is_pinch(hand):
    return pinch_distance(hand) < 0.05


# ── Motion state ──────────────────────────────────────────────────────────────
smooth_rx = smooth_ry = 0.0
smooth_tx = smooth_ty = 0.0
smooth_zoom = 0.0

last_rx = last_ry = None
last_lx = last_ly = None
last_zoom = None          # stores previous pinch distance

# Pause state — hysteresis counters
PAUSE_FRAMES   = 0        # consecutive open-palm frames
UNPAUSE_FRAMES = 0        # consecutive non-open-palm frames while paused
paused         = False

screenshot_cooldown = 0
screenshot_timer    = 0


def _full_motion_reset():
    global last_rx, last_ry, last_lx, last_ly, last_zoom
    global smooth_rx, smooth_ry, smooth_tx, smooth_ty, smooth_zoom
    global paused, PAUSE_FRAMES, UNPAUSE_FRAMES
    last_rx = last_ry = None
    last_lx = last_ly = None
    last_zoom = None
    smooth_rx = smooth_ry = 0.0
    smooth_tx = smooth_ty = 0.0
    smooth_zoom = 0.0
    paused         = False
    PAUSE_FRAMES   = 0
    UNPAUSE_FRAMES = 0


def _reset_init():
    global init_state, init_frames, lost_frames, registered_hands
    init_state       = "waiting"
    init_frames      = 0
    lost_frames      = 0
    registered_hands = {}
    _full_motion_reset()
    _update_init_bar(0)
    _set_init_overlay(True)
    init_status_text.text  = "Show your hand(s) to begin"
    init_status_text.color = color.yellow
    init_sub_text.text     = "Hold still while scanning..."


def update():
    global last_rx, last_ry, last_lx, last_ly, smooth_rx, smooth_ry
    global smooth_tx, smooth_ty, last_zoom, smooth_zoom
    global PAUSE_FRAMES, UNPAUSE_FRAMES, paused
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
    res   = hands_det.process(rgb)

    seen_this_frame = {}
    if res.multi_hand_landmarks and res.multi_handedness:
        for i, h in enumerate(res.multi_handedness):
            label = h.classification[0].label
            seen_this_frame[label] = res.multi_hand_landmarks[i]

    h_px, w_px, _ = frame.shape

    # ── INITIALIZATION STATE MACHINE ─────────────────────────────────────────
    if init_state != "locked":
        if not seen_this_frame:
            init_frames = 0
            _update_init_bar(0)
            if init_state != "waiting":
                init_state             = "waiting"
                init_status_text.text  = "Show your hand(s) to begin"
                init_status_text.color = color.yellow
                init_sub_text.text     = "Hold still while scanning..."
        else:
            init_state   = "scanning"
            init_frames += 1
            _update_init_bar(init_frames / INIT_HOLD_FRAMES)

            init_status_text.text  = "Scanning..." if init_frames % 10 < 5 else "Hold steady..."
            init_status_text.color = color.orange

            if init_frames >= INIT_HOLD_FRAMES:
                registered_hands = {label: True for label in seen_this_frame}
                init_state       = "locked"
                lost_frames      = 0
                _full_motion_reset()
                _update_init_bar(1.0)
                _set_init_overlay(False)

        _draw_skeletons(rgb, seen_this_frame, res)
        _upload_frame(rgb)
        gesture_text.text  = f"Init: {init_state.upper()}"
        gesture_text.color = color.orange
        return

    # ── SESSION ACTIVE ────────────────────────────────────────────────────────
    left  = seen_this_frame.get("Left")  if "Left"  in registered_hands else None
    right = seen_this_frame.get("Right") if "Right" in registered_hands else None

    any_registered_visible = any(lbl in seen_this_frame for lbl in registered_hands)
    if not any_registered_visible:
        lost_frames += 1
        if lost_frames >= LOST_GRACE_FRAMES:
            _reset_init()
            _upload_frame(rgb)
            gesture_text.text  = "Gesture: None"
            gesture_text.color = color.white
            return
    else:
        lost_frames = 0

    if lost_frames > 0:
        gesture_text.text  = f"Hand lost! Re-init in {LOST_GRACE_FRAMES - lost_frames}..."
        gesture_text.color = color.red

    # ── PAUSE — hysteresis so it doesn't flicker ──────────────────────────────
    # Engage: need PAUSE_ENGAGE_FRAMES consecutive open-palm frames
    # Release: need PAUSE_RELEASE_FRAMES consecutive non-open-palm frames
    left_is_open = left is not None and is_open_palm_relaxed(left)

    if not paused:
        if left_is_open:
            PAUSE_FRAMES  += 1
            UNPAUSE_FRAMES = 0
        else:
            PAUSE_FRAMES = 0
        if PAUSE_FRAMES >= PAUSE_ENGAGE_FRAMES:
            paused         = True
            UNPAUSE_FRAMES = 0
            # Wipe tracking so resuming never jumps
            last_rx = last_ry = None
            last_lx = last_ly = None
            last_zoom = None
            smooth_rx = smooth_ry = 0.0
            smooth_tx = smooth_ty = 0.0
            smooth_zoom = 0.0
    else:
        if not left_is_open:
            UNPAUSE_FRAMES += 1
            PAUSE_FRAMES    = 0
        else:
            UNPAUSE_FRAMES = 0
        if UNPAUSE_FRAMES >= PAUSE_RELEASE_FRAMES:
            paused         = False
            PAUSE_FRAMES   = 0
            UNPAUSE_FRAMES = 0
            # Reset tracking so first move after unpause doesn't jump
            last_rx = last_ry = None
            last_lx = last_ly = None
            last_zoom = None
            smooth_rx = smooth_ry = 0.0
            smooth_tx = smooth_ty = 0.0
            smooth_zoom = 0.0

    current_gest = "None"

    if paused:
        current_gest = "Paused"
        if right and is_peace(right) and screenshot_cooldown == 0:
            ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.abspath(f"screenshots/shot_{ts}.png")
            app.win.saveScreenshot(Filename.fromOsSpecific(path))
            screenshot_text.enabled = True
            screenshot_timer        = 2.0
            screenshot_cooldown     = 25

    else:
        # ── ROTATION (right index finger, only when NOT pinching) ─────────────
        if right and not model_locked and not is_pinch(right):
            current_gest = "Rotating"
            ix = int(right.landmark[8].x * w_px)
            iy = int(right.landmark[8].y * h_px)
            if last_rx is not None:
                dx = max(-MAX_ROT_DELTA, min(MAX_ROT_DELTA, ix - last_rx))
                dy = max(-MAX_ROT_DELTA, min(MAX_ROT_DELTA, iy - last_ry))
                smooth_rx = smooth_rx * (1 - ALPHA_ROT) + ( dy * rot_sens) * ALPHA_ROT
                smooth_ry = smooth_ry * (1 - ALPHA_ROT) + (-dx * rot_sens) * ALPHA_ROT
                car.rotation_x += smooth_rx
                car.rotation_y += smooth_ry
            else:
                smooth_rx = smooth_ry = 0.0
            last_rx, last_ry = ix, iy
        else:
            smooth_rx *= ROT_DECAY
            smooth_ry *= ROT_DECAY
            last_rx = last_ry = None

        # ── ZOOM (right pinch distance) ───────────────────────────────────────
        # Pinching closer  → zoom IN  (camera moves toward model, z increases)
        # Pulling apart    → zoom OUT (camera moves away,          z decreases)
        if right and not camera_locked:
            label_suffix = " + Zoom" if current_gest != "None" else "Zooming"
            current_gest += label_suffix
            pd = pinch_distance(right)
            if last_zoom is not None:
                delta = pd - last_zoom          # positive = fingers moving apart
                if abs(delta) < 0.003:
                    delta = 0.0
                delta = max(-MAX_ZOOM_DELTA, min(MAX_ZOOM_DELTA, delta))
                # Fingers apart  (delta > 0) → zoom OUT → camera.z decreases (more negative)
                # Fingers closer (delta < 0) → zoom IN  → camera.z increases (less negative)
                delta_scaled = delta * zoom_sens * 2
                smooth_zoom  = smooth_zoom * (1 - ALPHA_ZOOM) + delta_scaled * ALPHA_ZOOM
                camera.z     = clamp(camera.z - smooth_zoom, -35, -3)
            else:
                smooth_zoom = 0.0
            last_zoom = pd
        else:
            smooth_zoom *= ZOOM_DECAY
            last_zoom = None

        # ── TRANSLATION (left wrist) ──────────────────────────────────────────
        # Webcam is already flipped horizontally (mirror mode).
        # lm[0].x increases left→right on screen, y increases top→bottom.
        # We want moving the hand right  → model moves right  (+x)
        #           moving the hand up   → model moves up     (+y)
        if left and not model_locked:
            current_gest = "Moving"
            lx = int(left.landmark[0].x * w_px)
            ly = int(left.landmark[0].y * h_px)
            if last_lx is not None:
                # dx: positive = hand moved right on screen → +x in world
                dx =  (lx - last_lx) / w_px
                # dy: positive = hand moved DOWN on screen  → -y in world
                dy = -(ly - last_ly) / h_px
                dx = max(-MAX_TRANS_DELTA, min(MAX_TRANS_DELTA, dx))
                dy = max(-MAX_TRANS_DELTA, min(MAX_TRANS_DELTA, dy))
                smooth_tx = smooth_tx * (1 - ALPHA_TRANS) + dx * trans_sens * ALPHA_TRANS
                smooth_ty = smooth_ty * (1 - ALPHA_TRANS) + dy * trans_sens * ALPHA_TRANS
                car.position += Vec3(smooth_tx, smooth_ty, 0)
            else:
                smooth_tx = smooth_ty = 0.0
            last_lx, last_ly = lx, ly
        else:
            smooth_tx *= TRANS_DECAY
            smooth_ty *= TRANS_DECAY
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
    if screenshot_timer <= 0 and screenshot_text.enabled:
        screenshot_text.enabled = False


def _draw_skeletons(rgb, seen_this_frame, res, registered_hands=None):
    if not (res.multi_hand_landmarks and res.multi_handedness):
        return

    h_px, w_px, _ = rgb.shape

    for i, hand_lms in enumerate(res.multi_hand_landmarks):
        label = res.multi_handedness[i].classification[0].label

        if registered_hands is not None and label not in registered_hands:
            ns        = mp_drawing.DrawingSpec(color=(60, 30, 30), thickness=1, circle_radius=2)
            cs        = mp_drawing.DrawingSpec(color=(50, 20, 20), thickness=1)
            tag_col   = (80, 30, 30)
            tag_label = f"{label.upper()} (ignored)"
        else:
            ns        = LEFT_STYLE  if label == "Left" else RIGHT_STYLE
            cs        = LEFT_CONN   if label == "Left" else RIGHT_CONN
            tag_col   = (0, 220, 0) if label == "Left" else (50, 180, 255)
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