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

# Lock toggle

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

# Shared button style
BTN = dict(
    color=color.color(0, 0, 0.20),
    highlight_color=color.color(0, 0, 0.35),
    text_color=color.white,
)

# Left panel: lock button
model_btn = Button("Model Lock: OFF", scale=(0.22, 0.055),
                   position=(-0.67, 0.42), **BTN, on_click=toggle_model_lock)

# Left panel: view presets
Text("View Presets", parent=camera.ui,
     position=(-0.67, 0.275), origin=(0, 0), scale=0.8, color=color.gray)

vbtn = dict(scale=(0.10, 0.050), **BTN)
Button("Front", position=(-0.725, 0.22), on_click=lambda: set_view("front"), **vbtn)
Button("Side",  position=(-0.615, 0.22), on_click=lambda: set_view("side"),  **vbtn)
Button("Top",   position=(-0.725, 0.16), on_click=lambda: set_view("top"),   **vbtn)
Button("ISO",   position=(-0.615, 0.16), on_click=lambda: set_view("iso"),   **vbtn)

# Left panel: controls reference
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

# Top-centre: gesture status
gesture_text = Text(
    "Gesture: None",
    parent=camera.ui,
    position=(0, 0.46),
    origin=(0, 0),
    scale=1.1,
    color=color.white,
)

# Top-right: stats
fps_text = Text("FPS: --", parent=camera.ui,
                position=(0.68, 0.46), origin=(0, 0),
                scale=0.85, color=color.lime)
cpu_text = Text("CPU: --", parent=camera.ui,
                position=(0.68, 0.41), origin=(0, 0),
                scale=0.85, color=color.orange)
ram_text = Text("RAM: --", parent=camera.ui,
                position=(0.68, 0.36), origin=(0, 0),
                scale=0.85, color=color.cyan)

# Camera feed
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

# Screenshot notification
screenshot_text = Text(
    "Screenshot Saved!",
    parent=camera.ui,
    position=(0, 0.35),
    origin=(0, 0),
    scale=1.2,
    color=color.cyan,
    enabled=False,
)

# Mediapipe
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


alpha = 0.25
smooth_rx = smooth_ry = smooth_tx = smooth_ty = 0
last_rx = last_ry = last_lx = last_ly = None
last_zoom = None
smooth_zoom = 0
paused = False
PAUSE_FRAMES = 0

# --- UI ELEMENTS ---

# Camera feed border (slightly larger quad behind the feed)
Entity(
    parent=camera.ui,
    model='quad',
    scale=(0.42, 0.285),
    position=(0, -0.35),
    color=color.cyan,
    origin=(0, 0),
    z=0.01
)

# Camera feed panel — create without texture, then assign the P3D texture directly
# to the underlying Panda3D node, completely bypassing Ursina's file-loading system.
camera_feed_view = Entity(
    parent=camera.ui,
    model='quad',
    scale=(0.40, 0.27),
    position=(0, -0.35),
    origin=(0, 0)
)
camera_feed_view.setTexture(_p3d_tex, 1)

# "LIVE" label above the feed
Text(
    text="● LIVE",
    parent=camera.ui,
    position=(0, -0.205),
    origin=(0, 0),
    scale=1.2,
    color=color.red
)

# Gesture Display
gesture_text = Text(
    text="GESTURE: NONE",
    parent=camera.ui,
    position=(0, 0.45),
    origin=(0, 0),
    scale=1.5,
    color=color.yellow
)

# Persistent Instructions (Left Side)
Text(
    text="""
    <orange>CONTROLS</orange>
    <b>RIGHT HAND</b>
    • Index: Rotate
    • Pinch: Zoom
    • Peace: Shot (Paused)
    • Thumb Up: Reset (Paused)

    <b>LEFT HAND</b>
    • Wrist: Move
    • Palm: Pause
    """,
    parent=camera.ui,
    position=(-0.85, 0.2),
    scale=0.75
)

# FPS Counter (Top Right)
fps_text = Text(
    text="FPS: 0",
    parent=camera.ui,
    position=(0.75, 0.48),
    color=color.lime
)

# Hand label styles — color-coded per hand
LEFT_STYLE  = mp_drawing.DrawingSpec(color=(0, 220, 0),   thickness=2, circle_radius=3)   # Green
RIGHT_STYLE = mp_drawing.DrawingSpec(color=(50, 150, 255), thickness=2, circle_radius=3)   # Blue
LEFT_CONN   = mp_drawing.DrawingSpec(color=(0, 180, 0),   thickness=2)
RIGHT_CONN  = mp_drawing.DrawingSpec(color=(0, 100, 220), thickness=2)

def update():
    global last_rx, last_ry, last_lx, last_ly, smooth_rx, smooth_ry
    global smooth_tx, smooth_ty, last_zoom, smooth_zoom, PAUSE_FRAMES, paused
    global screenshot_cooldown, screenshot_timer

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

    left = right = None
    if res.multi_hand_landmarks and res.multi_handedness:
        for i, h in enumerate(res.multi_handedness):
            if h.classification[0].label == "Left":
                left  = res.multi_hand_landmarks[i]
            else:
                right = res.multi_hand_landmarks[i]

    if left and is_open_palm_relaxed(left):
        PAUSE_FRAMES += 1
    else:
        PAUSE_FRAMES = 0
    paused = PAUSE_FRAMES >= 3

    current_gest = "None"
    h_px, w_px, _ = frame.shape

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
        if right and not model_locked:
            current_gest = "Rotating"
            ix = int(right.landmark[8].x * w_px)
            iy = int(right.landmark[8].y * h_px)
            if last_rx is not None:
                dx, dy = ix - last_rx, iy - last_ry
                smooth_rx = smooth_rx * (1 - alpha) + (-dy * 2) * alpha
                smooth_ry = smooth_ry * (1 - alpha) + (dx * 2) * alpha
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
                delta = (strength - last_zoom) * 40
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
                smooth_tx = smooth_tx * (1 - alpha) + dx * 15 * alpha
                smooth_ty = smooth_ty * (1 - alpha) - dy * 15 * alpha
                car.position += Vec3(smooth_tx, smooth_ty, 0)
            last_lx, last_ly = lx, ly
        else:
            last_lx = last_ly = None

    gesture_text.text  = f"Gesture: {current_gest}"
    gesture_text.color = color.red if paused else color.white

    if res.multi_hand_landmarks and res.multi_handedness:
        for i, hand_lms in enumerate(res.multi_hand_landmarks):
            label = res.multi_handedness[i].classification[0].label
            if label == "Left":
                node_style = LEFT_STYLE
                conn_style = LEFT_CONN
                # Draw "LEFT" label near wrist
                wx = int(hand_lms.landmark[0].x * w_px)
                wy = int(hand_lms.landmark[0].y * h_px)
                cv2.putText(rgb, "LEFT", (wx - 20, wy + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 0), 2)
            else:
                node_style = RIGHT_STYLE
                conn_style = RIGHT_CONN
                wx = int(hand_lms.landmark[0].x * w_px)
                wy = int(hand_lms.landmark[0].y * h_px)
                cv2.putText(rgb, "RIGHT", (wx - 20, wy + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 150, 255), 2)

            mp_drawing.draw_landmarks(
                rgb, hand_lms, mp_hands.HAND_CONNECTIONS,
                landmark_drawing_spec=node_style,
                connection_drawing_spec=conn_style
            )

    # Overlay paused banner directly on the feed
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


app.run()
cap.release()
cv2.destroyAllWindows()