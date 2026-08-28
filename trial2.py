"""
Interactive 3D Model & Point Cloud Viewer for Hand-AR Project.
Supports Inspect Mode (object rotation/zoom/translation via gestures) and Explore Mode (first-person point cloud navigation).
"""

import pandas as pd
from covariance_align import auto_align_up_axis
from ursina import *
from panda3d.core import Texture as P3DTexture, Filename
from ursina.prefabs.first_person_controller import FirstPersonController
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

# Arguments Parsing
selected_model = None
viewer_mode = "inspect"

if len(sys.argv) > 1:
    selected_model = sys.argv[1]

if len(sys.argv) > 2:
    viewer_mode = sys.argv[2]

if selected_model:
    model_path = selected_model
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

# Conditional Scene Setup
if viewer_mode == "inspect":
    print("--- SETUP: INSPECT MODE ---")
    car = Entity()
    
    if model_path.lower().endswith(".csv"):
        df = pd.read_csv(model_path)
        df = df.iloc[::10]
        df = auto_align_up_axis(df)
        vertices = [Vec3(x, y, z) for x, y, z in zip(df["x"], df["y"], df["z"])]
        point_colors = [(r / 255.0, g / 255.0, b / 255.0, 1.0) for r, g, b in zip(df["r"], df["g"], df["b"])]
        car.model = Mesh(vertices=vertices, colors=point_colors, mode='point', thickness=0.009)
    else:
        panda_path = Filename.from_os_specific(model_path)
        loaded = base.loader.load_model(panda_path) 
        if loaded is None:
            sys.exit(1)
        loaded.reparent_to(car)
        
    car.scale = 1
    try:
        min_b, max_b = car.model.get_tight_bounds()
    except Exception:
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

    def toggle_model_lock() -> None:
        """Toggles lock state preventing gesture-based rotation and translation of model."""
        global model_locked
        model_locked = not model_locked
        model_btn.text  = f"Model Lock: {'ON' if model_locked else 'OFF'}"
        model_btn.color = color.color(0, 0, 0.30) if model_locked else color.color(0, 0, 0.20)

    def set_view(mode: str) -> None:
        """
        Sets predefined camera position preset (front, side, top, iso).

        Args:
            mode (str): View mode name.
        """
        global view_mode, camera_locked
        view_mode = mode
        camera_locked = True
        if mode == "front":  camera.position = Vec3(0,  0, -12)
        elif mode == "side": camera.position = Vec3(12, 0,   0)
        elif mode == "top":  camera.position = Vec3(0,  12,  0)
        elif mode == "iso":  camera.position = Vec3(8,  6,  -8)
        camera.look_at(car.position)

    BTN = dict(color=color.color(0, 0, 0.20), highlight_color=color.color(0, 0, 0.35), text_color=color.white)
    model_btn = Button("Model Lock: OFF", scale=(0.22, 0.055), position=(-0.67, 0.42), **BTN, on_click=toggle_model_lock)
    Text("View Presets", parent=camera.ui, position=(-0.67, 0.275), origin=(0, 0), scale=0.8, color=color.gray)
    vbtn = dict(scale=(0.10, 0.050), **BTN)
    btn_front = Button("Front", position=(-0.725, 0.22), on_click=lambda: set_view("front"), **vbtn)
    btn_side  = Button("Side",  position=(-0.615, 0.22), on_click=lambda: set_view("side"),  **vbtn)
    btn_top   = Button("Top",   position=(-0.725, 0.16), on_click=lambda: set_view("top"),   **vbtn)
    btn_iso   = Button("ISO",   position=(-0.615, 0.16), on_click=lambda: set_view("iso"),   **vbtn)

    rot_sens, trans_sens, zoom_sens = 2, 15, 40
    Text("Sensitivity", parent=camera.ui, position=(0.55, 0.05), scale=0.9, color=color.white)
    Text("Rotation", parent=camera.ui, position=(0.55, -0.02), scale=0.7)
    rot_slider = Slider(min=0.5, max=5, default=rot_sens, step=0.1, position=(0.55, -0.06), scale=0.3)
    Text("Translation", parent=camera.ui, position=(0.55, -0.14), scale=0.7)
    trans_slider = Slider(min=5, max=30, default=trans_sens, step=1, position=(0.55, -0.18), scale=0.3)
    Text("Zoom", parent=camera.ui, position=(0.55, -0.26), scale=0.7)
    zoom_slider = Slider(min=10, max=80, default=zoom_sens, step=1, position=(0.55, -0.30), scale=0.3)

    Text("RIGHT HAND\n  Index finger  ->  Rotate\n  Pinch closer  ->  Zoom in\n  Pinch apart   ->  Zoom out\n  Peace sign    ->  Screenshot\n\nLEFT HAND\n  Open palm     ->  Pause\n  Wrist move    ->  Translate", parent=camera.ui, position=(-0.785, 0.095), scale=0.72, color=color.color(0, 0, 0.75))
    gesture_text = Text("Gesture: None", parent=camera.ui, position=(0, 0.46), origin=(0, 0), scale=1.1, color=color.white)
    
    player = None


elif viewer_mode == "explore":
    print("--- SETUP: EXPLORE MODE ---")
    df = pd.read_csv(model_path)
    df = df.iloc[::10] 
    df = auto_align_up_axis(df)

    global_points_xz = np.array([df["x"], df["z"]]).T
    global_points_y = np.array(df["y"])

    min_x, max_x = np.min(global_points_xz[:, 0]) + 1.0, np.max(global_points_xz[:, 0]) - 1.0
    min_z, max_z = np.min(global_points_xz[:, 1]) + 1.0, np.max(global_points_xz[:, 1]) - 1.0

    vertices = [Vec3(x, y, z) for x, y, z in zip(df["x"], df["y"], df["z"])]
    point_colors = [(r / 255.0, g / 255.0, b / 255.0, 1.0) for r, g, b in zip(df["r"], df["g"], df["b"])]
    mesh = Mesh(vertices=vertices, colors=point_colors, mode='point', thickness=0.009)
    Entity(model=mesh)

    player = FirstPersonController()
    player.gravity = 0 
    player.speed = 0 
    player.mouse_sensitivity = Vec2(0, 0) 
    player.prev_x, player.prev_z = player.x, player.z
    
    is_flying = False
    flight_toggle_cooldown = 4 
    reset_cooldown = 0
    spawn_position = None
    spawn_rotation = None
    spawn_initialized = False

    legend = Text(text="<yellow>HAND CONTROLS\n\n<orange>RIGHT HAND (ALWAYS ACTIVE)\n<white>🖐 Open Palm   : Enable View Control\n<white>✊ Fist        : Freeze View\n<white>← Move Left   : Look Left\n<white>→ Move Right  : Look Right\n<white>↑ Move Up     : Look Up\n<white>↓ Move Down   : Look Down\n\n<cyan>LEFT HAND (WALK MODE)\n<white>✌ Peace       : Toggle Flight Mode\n<white>🖐 move palm up   : Move Forward\n<white>🖐 move palm Down   : Move Backward\n<white>✊ Fist        : Stop\n\n<lime>LEFT HAND (FLIGHT MODE)\n<white> thumbs up     : position Reset\n<white>✌ Peace       : Toggle Walk Mode\n<white>☝  Index Up    : Fly Up\n<white>👇  Index Down  : Fly Down\n<white>🖐 move Palm up  : Fly Forward\n<white>🖐 move Palm Down   : Fly Backward\n<white>✊ Fist        : ...", position=window.top_left + Vec2(0.02, -0.02), origin=(-0.5, 0.5), scale=0.8, background=True)
    right_status = Text(text="Right: Not Detected", position=(0.3, -0.35), scale=1.2, color=color.orange)
    left_status = Text(text="Left: Not Detected", position=(0.3, -0.40), scale=1.2, color=color.cyan)
    flight_status = Text(text="Mode: Grounded", position=(0.3, -0.45), scale=1.2, color=color.green)

    car = None
    gesture_text = None
    rot_slider = trans_slider = zoom_slider = None

# Shared Performance & Camera Feed UI
fps_text = Text("FPS: --", parent=camera.ui, position=(0.68, 0.46), origin=(0, 0), scale=0.85, color=color.lime)
cpu_text = Text("CPU: --", parent=camera.ui, position=(0.68, 0.41), origin=(0, 0), scale=0.85, color=color.orange)
ram_text = Text("RAM: --", parent=camera.ui, position=(0.68, 0.36), origin=(0, 0), scale=0.85, color=color.cyan)

FEED_W, FEED_H = 320, 240
_p3d_tex = P3DTexture('camera_feed')
_p3d_tex.setup2dTexture(FEED_W, FEED_H, P3DTexture.TUnsignedByte, P3DTexture.FRgb)
_p3d_tex.setMagfilter(P3DTexture.FTLinear)
_p3d_tex.setMinfilter(P3DTexture.FTLinear)
buf = _p3d_tex.modifyRamImage()
memoryview(buf).cast('B')[:] = b'\x00' * (FEED_W * FEED_H * 3)


def _upload_frame(rgb_frame: np.ndarray) -> None:
    """
    Resizes and updates the webcam feed texture displayed in the UI overlay.

    Args:
        rgb_frame (np.ndarray): The latest RGB video frame.
    """
    small = cv2.resize(rgb_frame, (FEED_W, FEED_H), interpolation=cv2.INTER_LINEAR)
    small = np.flipud(small)
    small = np.ascontiguousarray(small, dtype=np.uint8)
    buf   = _p3d_tex.modifyRamImage()
    memoryview(buf).cast('B')[:] = small.tobytes()
    _p3d_tex.setRamImage(buf)


Entity(parent=camera.ui, model='quad', scale=(0.445, 0.315), position=(-0.67, -0.335), color=color.color(0, 0, 0.35), origin=(0, 0), z=0.01)
camera_feed_view = Entity(parent=camera.ui, model='quad', scale=(0.44, 0.31), position=(-0.67, -0.335), origin=(0, 0))
camera_feed_view.model.setTexture(_p3d_tex)
Text("LIVE", parent=camera.ui, position=(-0.67, -0.168), origin=(0, 0), scale=0.9, color=color.red)

screenshot_text = Text("Screenshot Saved!", parent=camera.ui, position=(0, 0.35), origin=(0, 0), scale=1.2, color=color.cyan, enabled=False)

# Initialization Scanning Overlay Setup
INIT_HOLD_FRAMES  = 45
LOST_GRACE_FRAMES = 10
init_state       = "waiting"
init_frames      = 0
lost_frames      = 0
registered_hands = {}

init_panel = Entity(parent=camera.ui, model='quad', scale=(0.60, 0.13), position=(0, 0.0), color=color.color(0, 0, 0.12, 0.88), origin=(0, 0), z=0.02, enabled=True)
init_status_text = Text("Show your hand(s) to begin", parent=camera.ui, position=(0, 0.03), origin=(0, 0), scale=1.05, color=color.yellow, enabled=True)
init_sub_text = Text("Hold still while scanning...", parent=camera.ui, position=(0, -0.02), origin=(0, 0), scale=0.75, color=color.color(0, 0, 0.80), enabled=True)
init_bar_bg = Entity(parent=camera.ui, model='quad', scale=(0.42, 0.018), position=(0, -0.06), color=color.color(0, 0, 0.25), origin=(0, 0), z=0.02, enabled=True)
init_bar_fill = Entity(parent=camera.ui, model='quad', scale=(0.0, 0.014), position=(-0.21, -0.06), color=color.cyan, origin=(-0.5, 0), z=0.01, enabled=True)


def _set_init_overlay(enabled: bool) -> None:
    """
    Enables or disables visibility of the hand scanner initialization UI overlay.

    Args:
        enabled (bool): True to show overlay, False to hide.
    """
    init_panel.enabled       = enabled
    init_status_text.enabled = enabled
    init_sub_text.enabled    = enabled
    init_bar_bg.enabled      = enabled
    init_bar_fill.enabled    = enabled


def _update_init_bar(fraction: float) -> None:
    """
    Updates progress bar fill scale during initial hand scanning hold.

    Args:
        fraction (float): Progress ratio between 0.0 and 1.0.
    """
    init_bar_fill.scale_x = 0.42 * max(0.0, min(1.0, fraction))


mp_hands   = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

LEFT_STYLE  = mp_drawing.DrawingSpec(color=(0,   220,   0), thickness=2, circle_radius=3)
RIGHT_STYLE = mp_drawing.DrawingSpec(color=(50,  180, 255), thickness=2, circle_radius=3)
LEFT_CONN   = mp_drawing.DrawingSpec(color=(0,   180,   0), thickness=2)
RIGHT_CONN  = mp_drawing.DrawingSpec(color=(0,   130, 230), thickness=2)


def _draw_skeletons(display_frame: np.ndarray, res, registered_hands: dict = None) -> None:
    """
    Renders MediaPipe hand skeleton landmarks and connection lines onto a frame.

    Args:
        display_frame (np.ndarray): Video frame to draw on.
        res: MediaPipe hands detection results object.
        registered_hands (dict): Dict of actively registered hand labels.
    """
    if not (res and res.multi_hand_landmarks and res.multi_handedness):
        return
    h_px, w_px, _ = display_frame.shape
    for i, hand_lms in enumerate(res.multi_hand_landmarks):
        label = res.multi_handedness[i].classification[0].label
        if registered_hands is not None and label not in registered_hands and len(registered_hands) > 0:
            ns = mp_drawing.DrawingSpec(color=(60, 30, 30), thickness=1, circle_radius=2)
            cs = mp_drawing.DrawingSpec(color=(50, 20, 20), thickness=1)
            tag_col, tag_label = (80, 30, 30), f"{label.upper()} (ignored)"
        else:
            ns = LEFT_STYLE if label == "Left" else RIGHT_STYLE
            cs = LEFT_CONN if label == "Left" else RIGHT_CONN
            tag_col, tag_label = ((0, 220, 0) if label == "Left" else (50, 180, 255)), label.upper()
        wx, wy = int(hand_lms.landmark[0].x * w_px), int(hand_lms.landmark[0].y * h_px)
        cv2.putText(display_frame, tag_label, (wx - 20, wy + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, tag_col, 2)
        mp_drawing.draw_landmarks(display_frame, hand_lms, mp_hands.HAND_CONNECTIONS, landmark_drawing_spec=ns, connection_drawing_spec=cs)


def _full_motion_reset() -> None:
    """Resets all smoothed motion accumulators, tracking deltas, and pause state."""
    global last_rx, last_ry, last_lx, last_ly, last_zoom, smooth_rx, smooth_ry, smooth_tx, smooth_ty, smooth_zoom, paused, PAUSE_FRAMES, UNPAUSE_FRAMES
    last_rx = last_ry = last_lx = last_ly = last_zoom = None
    smooth_rx = smooth_ry = smooth_tx = smooth_ty = smooth_zoom = 0.0
    paused = False; PAUSE_FRAMES = 0; UNPAUSE_FRAMES = 0


def _reset_init() -> None:
    """Resets hand registration scanning state machine when tracking is lost."""
    global init_state, init_frames, lost_frames, registered_hands
    init_state = "waiting"; init_frames = lost_frames = 0; registered_hands = {}
    if viewer_mode == "inspect":
        _full_motion_reset()
    _update_init_bar(0); _set_init_overlay(True)
    init_status_text.text = "Show your hand(s) to begin"
    init_status_text.color = color.yellow
    init_sub_text.text = "Hold still while scanning..."


# Mode-Specific Tracking Setup
if viewer_mode == "inspect":
    hands_det  = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.8, min_tracking_confidence=0.8)
    cap = cv2.VideoCapture(0)
    
    def is_open_palm_relaxed(hand) -> bool:
        """Checks if hand landmarks match a relaxed open palm gesture."""
        lm = hand.landmark
        tips, bases = [8, 12, 16], [5, 9, 13]
        return sum(lm[t].y < lm[b].y - 0.01 for t, b in zip(tips, bases)) >= 2

    def is_peace(hand) -> bool:
        """Checks if hand landmarks match a peace sign gesture."""
        lm = hand.landmark
        return (lm[8].y < lm[6].y and lm[12].y < lm[10].y and lm[16].y > lm[14].y)

    def pinch_distance(hand) -> float:
        """Calculates distance between index tip and thumb tip."""
        return math.dist((hand.landmark[4].x, hand.landmark[4].y), (hand.landmark[8].x, hand.landmark[8].y))

    def is_pinch(hand) -> bool:
        """Returns True if index and thumb tips are pinched close together."""
        return pinch_distance(hand) < 0.05

    smooth_rx = smooth_ry = smooth_tx = smooth_ty = smooth_zoom = 0.0
    last_rx = last_ry = last_lx = last_ly = last_zoom = None
    PAUSE_FRAMES = UNPAUSE_FRAMES = 0
    paused = False
    screenshot_cooldown = screenshot_timer = 0

elif viewer_mode == "explore":
    import threading

    class HandTracker:
        """Threaded MediaPipe hand tracker for explore mode."""

        def __init__(self):
            """Starts camera capture and background frame processing thread."""
            self.hands = mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
            self.cap = cv2.VideoCapture(0)
            self.state = {
                'Left': {'visible': False, 'x': 0.5, 'y': 0.5, 'gesture': 'None'},
                'Right': {'visible': False, 'x': 0.5, 'y': 0.5, 'gesture': 'None'}
            }
            self.latest_frame = None
            self.running = True
            self.thread = threading.Thread(target=self._update_frames, daemon=True)
            self.thread.start()

        def _update_frames(self) -> None:
            """Continuously captures camera frames, evaluates gestures, and updates state."""
            global registered_hands, init_state
            while self.running:
                success, img = self.cap.read()
                if not success:
                    continue
                img = cv2.flip(img, 1)
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                results = self.hands.process(img_rgb)
                
                self.state['Left']['visible'] = False
                self.state['Right']['visible'] = False
                
                if results.multi_hand_landmarks:
                    for idx, hand_lms in enumerate(results.multi_hand_landmarks):
                        hand_type = results.multi_handedness[idx].classification[0].label
                        st = self.state[hand_type]
                        st['visible'] = True
                        st['x'], st['y'] = hand_lms.landmark[0].x, hand_lms.landmark[0].y
                        
                        ring_up = hand_lms.landmark[16].y < hand_lms.landmark[14].y
                        index_up = hand_lms.landmark[8].y < hand_lms.landmark[6].y
                        middle_up = hand_lms.landmark[12].y < hand_lms.landmark[10].y
                        ring_down = hand_lms.landmark[16].y > hand_lms.landmark[14].y
                        pinky_up = hand_lms.landmark[20].y < hand_lms.landmark[18].y
                        pinky_down = hand_lms.landmark[20].y > hand_lms.landmark[18].y
                        
                        st['peace'] = (index_up and middle_up and ring_down and pinky_down)
                        st['open_palm'] = (index_up and middle_up and ring_up and pinky_up)
                        st['fist'] = (not index_up and not middle_up and not ring_up and not pinky_up)
                        
                        wrist_y = hand_lms.landmark[0].y
                        wrist = hand_lms.landmark[0]

                        thumb_dist = ((hand_lms.landmark[4].x - wrist.x)**2 + (hand_lms.landmark[4].y - wrist.y)**2) ** 0.5
                        index_dist = ((hand_lms.landmark[8].x - wrist.x)**2 + (hand_lms.landmark[8].y - wrist.y)**2) ** 0.5
                        middle_dist = ((hand_lms.landmark[12].x - wrist.x)**2 + (hand_lms.landmark[12].y - wrist.y)**2) ** 0.5
                        ring_dist = ((hand_lms.landmark[16].x - wrist.x)**2 + (hand_lms.landmark[16].y - wrist.y)**2) ** 0.5
                        pinky_dist = ((hand_lms.landmark[20].x - wrist.x)**2 + (hand_lms.landmark[20].y - wrist.y)**2) ** 0.5
                        
                        st['index_up'] = (
                            index_dist > middle_dist + 0.05 and
                            index_dist > ring_dist + 0.05 and
                            index_dist > pinky_dist + 0.05 and
                            hand_lms.landmark[8].y < wrist_y
                        )
                        st['index_down'] = (index_dist > middle_dist + 0.05 and index_dist > ring_dist + 0.05 and index_dist > pinky_dist + 0.05)
                        st['thumbs_up'] = (thumb_dist > index_dist + 0.08 and thumb_dist > middle_dist + 0.08 and thumb_dist > ring_dist + 0.08 and thumb_dist > pinky_dist + 0.08)
                        st['palm_down'] = (hand_lms.landmark[8].y > wrist_y and hand_lms.landmark[12].y > wrist_y and hand_lms.landmark[16].y > wrist_y and hand_lms.landmark[20].y > wrist_y)

                        if hand_type == 'Right':
                            if st['open_palm']: st['gesture'] = 'Steering'
                            elif st['fist']: st['gesture'] = 'View Locked'
                            else: st['gesture'] = 'None'
                        else:
                            if st['thumbs_up']: st['gesture'] = 'Reset'
                            elif st['peace']: st['gesture'] = 'Toggle Flight'
                            elif st['palm_down'] and not hand_lms.landmark[8].y > hand_lms.landmark[12].y: st['gesture'] = 'Backward'
                            elif st['index_up']: st['gesture'] = 'Up'
                            elif st['index_down']: st['gesture'] = 'Down'
                            elif st['open_palm']: st['gesture'] = 'Forward'
                            elif st['fist']: st['gesture'] = 'Stop'
                            else: st['gesture'] = 'None'
                
                _draw_skeletons(img_rgb, results, registered_hands)
                
                if init_state == "locked":
                    cv2.putText(img_rgb, f"LEFT : {self.state['Left']['gesture']}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
                    cv2.putText(img_rgb, f"RIGHT: {self.state['Right']['gesture']}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
                
                self.latest_frame = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                time.sleep(0.01)

        def stop(self) -> None:
            """Stops frame updates and releases video capture object."""
            self.running = False
            self.cap.release()

    tracker = HandTracker()


def reset_player() -> None:
    """Resets first-person player position and rotation in Explore Mode to spawn point."""
    if viewer_mode == "explore" and spawn_initialized:
        player.position = spawn_position
        player.rotation_x = spawn_rotation.x
        player.rotation_y = spawn_rotation.y
        player.rotation_z = spawn_rotation.z
        player.prev_x = player.x
        player.prev_z = player.z


# Motion Constants
ALPHA_ROT   = 0.12
ALPHA_TRANS = 0.10
ALPHA_ZOOM  = 0.10
ROT_DECAY   = 0.82
TRANS_DECAY = 0.80
ZOOM_DECAY  = 0.78
MAX_ROT_DELTA   = 60
MAX_TRANS_DELTA = 0.12
MAX_ZOOM_DELTA  = 0.06
PAUSE_ENGAGE_FRAMES  = 8   
PAUSE_RELEASE_FRAMES = 6   


def update() -> None:
    """
    Main frame update function called per tick by Ursina engine.
    Processes camera input, hand gestures, object transformations, terrain collision, and UI.
    """
    global last_rx, last_ry, last_lx, last_ly, smooth_rx, smooth_ry, smooth_tx, smooth_ty, last_zoom, smooth_zoom
    global PAUSE_FRAMES, UNPAUSE_FRAMES, paused, screenshot_cooldown, screenshot_timer
    global rot_sens, trans_sens, zoom_sens, init_state, init_frames, lost_frames, registered_hands
    global is_flying, flight_toggle_cooldown, spawn_position, spawn_rotation, spawn_initialized
    global reset_cooldown

    fps = int(1 / time.dt) if time.dt > 0 else 0
    fps_text.text = f"FPS: {fps}"
    cpu_text.text = f"CPU: {psutil.cpu_percent(interval=None):.0f}%"
    ram_text.text = f"RAM: {psutil.virtual_memory().percent:.0f}%"

    if viewer_mode == "inspect":
        rot_sens = rot_slider.value; trans_sens = trans_slider.value; zoom_sens = zoom_slider.value
        ok, frame = cap.read()
        if not ok:
            return
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = hands_det.process(rgb)
        display_frame = frame.copy()

        seen_this_frame = {}
        if res.multi_hand_landmarks and res.multi_handedness:
            for i, h in enumerate(res.multi_handedness):
                label = h.classification[0].label
                seen_this_frame[label] = res.multi_hand_landmarks[i]

        h_px, w_px, _ = frame.shape

        if init_state != "locked":
            if not seen_this_frame:
                init_frames = 0
                _update_init_bar(0)
                if init_state != "waiting":
                    init_state = "waiting"; init_status_text.text = "Show your hand(s) to begin"; init_status_text.color = color.yellow; init_sub_text.text = "Hold still while scanning..."
            else:
                init_state = "scanning"
                init_frames += 1
                _update_init_bar(init_frames / INIT_HOLD_FRAMES)
                init_status_text.text = "Scanning..." if init_frames % 10 < 5 else "Hold steady..."
                init_status_text.color = color.orange
                if init_frames >= INIT_HOLD_FRAMES:
                    registered_hands = {label: True for label in seen_this_frame}
                    init_state = "locked"; lost_frames = 0
                    _full_motion_reset(); _update_init_bar(1.0); _set_init_overlay(False)
            
            _draw_skeletons(display_frame, res, registered_hands)
            _upload_frame(display_frame)
            gesture_text.text = f"Init: {init_state.upper()}"; gesture_text.color = color.orange
            return

        left = seen_this_frame.get("Left") if "Left" in registered_hands else None
        right = seen_this_frame.get("Right") if "Right" in registered_hands else None

        if not any(lbl in seen_this_frame for lbl in registered_hands):
            lost_frames += 1
            if lost_frames >= LOST_GRACE_FRAMES:
                _reset_init(); _upload_frame(display_frame); gesture_text.text = "Gesture: None"; gesture_text.color = color.white; return
        else:
            lost_frames = 0

        if lost_frames > 0:
            gesture_text.text = f"Hand lost! Re-init in {LOST_GRACE_FRAMES - lost_frames}..."; gesture_text.color = color.red

        left_is_open = left is not None and is_open_palm_relaxed(left)
        if not paused:
            if left_is_open:
                PAUSE_FRAMES += 1; UNPAUSE_FRAMES = 0
            else:
                PAUSE_FRAMES = 0
            if PAUSE_FRAMES >= PAUSE_ENGAGE_FRAMES:
                paused = True; UNPAUSE_FRAMES = 0
                last_rx = last_ry = last_lx = last_ly = last_zoom = None
                smooth_rx = smooth_ry = smooth_tx = smooth_ty = smooth_zoom = 0.0
        else:
            if not left_is_open:
                UNPAUSE_FRAMES += 1; PAUSE_FRAMES = 0
            else:
                UNPAUSE_FRAMES = 0
            if UNPAUSE_FRAMES >= PAUSE_RELEASE_FRAMES:
                paused = False; PAUSE_FRAMES = UNPAUSE_FRAMES = 0
                last_rx = last_ry = last_lx = last_ly = last_zoom = None
                smooth_rx = smooth_ry = smooth_tx = smooth_ty = smooth_zoom = 0.0

        current_gest = "None"
        if paused:
            current_gest = "Paused"
            if right and is_peace(right) and screenshot_cooldown == 0:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                app.win.saveScreenshot(Filename.fromOsSpecific(os.path.abspath(f"screenshots/shot_{ts}.png")))
                screenshot_text.enabled = True; screenshot_timer = 2.0; screenshot_cooldown = 25
        else:
            if right and not model_locked and not is_pinch(right):
                current_gest = "Rotating"
                ix, iy = int(right.landmark[8].x * w_px), int(right.landmark[8].y * h_px)
                if last_rx is not None:
                    dx, dy = max(-MAX_ROT_DELTA, min(MAX_ROT_DELTA, ix - last_rx)), max(-MAX_ROT_DELTA, min(MAX_ROT_DELTA, iy - last_ry))
                    smooth_rx = smooth_rx * (1 - ALPHA_ROT) + (dy * rot_sens) * ALPHA_ROT
                    smooth_ry = smooth_ry * (1 - ALPHA_ROT) + (-dx * rot_sens) * ALPHA_ROT
                    car.rotation_x += smooth_rx; car.rotation_y += smooth_ry
                else:
                    smooth_rx = smooth_ry = 0.0
                last_rx, last_ry = ix, iy
            else:
                smooth_rx *= ROT_DECAY; smooth_ry *= ROT_DECAY; last_rx = last_ry = None

            if right and not camera_locked:
                current_gest += " + Zoom" if current_gest != "None" else "Zooming"
                pd_dist = pinch_distance(right)
                if last_zoom is not None:
                    delta = pd_dist - last_zoom
                    if abs(delta) < 0.003:
                        delta = 0.0
                    delta = max(-MAX_ZOOM_DELTA, min(MAX_ZOOM_DELTA, delta))
                    smooth_zoom = smooth_zoom * (1 - ALPHA_ZOOM) + (delta * zoom_sens * 2) * ALPHA_ZOOM
                    camera.z = clamp(camera.z - smooth_zoom, -35, -3)
                else:
                    smooth_zoom = 0.0
                last_zoom = pd_dist
            else:
                smooth_zoom *= ZOOM_DECAY; last_zoom = None

            if left and not model_locked:
                current_gest = "Moving"
                lx, ly = int(left.landmark[0].x * w_px), int(left.landmark[0].y * h_px)
                if last_lx is not None:
                    dx, dy = (lx - last_lx) / w_px, -(ly - last_ly) / h_px
                    dx, dy = max(-MAX_TRANS_DELTA, min(MAX_TRANS_DELTA, dx)), max(-MAX_TRANS_DELTA, min(MAX_TRANS_DELTA, dy))
                    smooth_tx = smooth_tx * (1 - ALPHA_TRANS) + dx * trans_sens * ALPHA_TRANS
                    smooth_ty = smooth_ty * (1 - ALPHA_TRANS) + dy * trans_sens * ALPHA_TRANS
                    car.position += Vec3(smooth_tx, smooth_ty, 0)
                else:
                    smooth_tx = smooth_ty = 0.0
                last_lx, last_ly = lx, ly
            else:
                smooth_tx *= TRANS_DECAY; smooth_ty *= TRANS_DECAY; last_lx = last_ly = None

        if lost_frames == 0:
            gesture_text.text = f"Gesture: {current_gest}"; gesture_text.color = color.red if paused else color.white
        _draw_skeletons(display_frame, res, registered_hands)
        if paused:
            cv2.rectangle(display_frame, (0, h_px // 2 - 20), (w_px, h_px // 2 + 20), (18, 18, 28), -1)
            cv2.putText(display_frame, "-- PAUSED --", (w_px // 2 - 95, h_px // 2 + 7), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 210, 255), 2)
        _upload_frame(display_frame)

        if screenshot_cooldown > 0: screenshot_cooldown -= 1
        if screenshot_timer > 0: screenshot_timer -= time.dt
        if screenshot_timer <= 0 and screenshot_text.enabled: screenshot_text.enabled = False

    elif viewer_mode == "explore":
        if tracker.latest_frame is not None:
            _upload_frame(tracker.latest_frame)

        left, right = tracker.state['Left'], tracker.state['Right']
        
        seen_this_frame = {}
        if left['visible']: seen_this_frame['Left'] = True
        if right['visible']: seen_this_frame['Right'] = True

        if init_state != "locked":
            if not seen_this_frame:
                init_frames = 0
                _update_init_bar(0)
                if init_state != "waiting":
                    init_state = "waiting"; init_status_text.text = "Show your hand(s) to begin"; init_status_text.color = color.yellow; init_sub_text.text = "Hold still while scanning..."
            else:
                init_state = "scanning"
                init_frames += 1
                _update_init_bar(init_frames / INIT_HOLD_FRAMES)
                init_status_text.text = "Scanning..." if init_frames % 10 < 5 else "Hold steady..."
                init_status_text.color = color.orange
                
                if init_frames >= INIT_HOLD_FRAMES:
                    registered_hands = {label: True for label in seen_this_frame}
                    init_state = "locked"; lost_frames = 0
                    _update_init_bar(1.0); _set_init_overlay(False)
            return

        if not any(lbl in seen_this_frame for lbl in registered_hands):
            lost_frames += 1
            if lost_frames >= LOST_GRACE_FRAMES:
                _reset_init()
                return
        else:
            lost_frames = 0

        left_status.text = f"Left: {left['gesture']}" if left['visible'] else "Left: Not Detected"
        right_status.text = f"Right: {right['gesture']}" if right['visible'] else "Right: Not Detected"

        if right['visible'] and right['gesture'] == 'Steering':
            if right['x'] < 0.4: player.rotation_y -= 80 * time.dt * (0.4 - right['x'])
            elif right['x'] > 0.6: player.rotation_y += 80 * time.dt * (right['x'] - 0.6)
            if right['y'] < 0.4: player.rotation_x -= 60 * time.dt * (0.4 - right['y'])
            elif right['y'] > 0.6: player.rotation_x += 60 * time.dt * (right['y'] - 0.6)

        if left['visible']:
            if left['gesture'] == 'Toggle Flight' and time.time() > flight_toggle_cooldown:
                is_flying = not is_flying
                flight_toggle_cooldown = time.time() + 1.0
                flight_status.text, flight_status.color = ("Mode: Flying", color.red) if is_flying else ("Mode: Grounded", color.green)
            if left['gesture'] == 'Reset' and time.time() > reset_cooldown:
                reset_player()
                reset_cooldown = time.time() + 2.0
                
            if not is_flying:
                if left['gesture'] == 'Backward': player.position -= player.forward * 2.0 * time.dt
                elif left['gesture'] == 'Forward': player.position += player.forward * 2.0 * time.dt

        px, pz = player.x, player.z
        dists_sq = (global_points_xz[:, 0] - px)**2 + (global_points_xz[:, 1] - pz)**2
        ground_mask = dists_sq < 9.0
        ground_y = player.y - 2.0
        
        if np.any(ground_mask):
            ground_y = np.percentile(global_points_y[ground_mask], 25)

        if is_flying:
            if left['visible']:
                if left['gesture'] == 'Up': player.y += 2 * time.dt
                elif left['gesture'] == 'Down': player.y -= 2 * time.dt
                elif left['gesture'] == 'Backward': player.position -= player.forward * 2.0 * time.dt
                elif left['gesture'] == 'Forward': player.position += player.forward * 2.0 * time.dt
            if player.y < ground_y + 0.2: player.y = ground_y + 0.2
        else:
            player.y = lerp(player.y, ground_y + 0.2, time.dt * 10)
            if not spawn_initialized:
                spawn_position, spawn_rotation, spawn_initialized = Vec3(player.position), Vec3(player.rotation_x, player.rotation_y, player.rotation_z), True

        player.x, player.z = clamp(player.x, min_x, max_x), clamp(player.z, min_z, max_z)
        collision_mask = dists_sq < 0.09
        if np.any(collision_mask):
            close_points_y = global_points_y[collision_mask]
            local_foot_level = np.min(close_points_y)
            if player.y < local_foot_level + 1.0: 
                if np.any((close_points_y > local_foot_level + 0.15) & (close_points_y < local_foot_level + 0.5)):
                    player.x, player.z = player.prev_x, player.prev_z
                else: player.prev_x, player.prev_z = player.x, player.z
        else:
            player.prev_x, player.prev_z = player.x, player.z


def input(key: str) -> None:
    """
    Handles keypress events for application exit and player reset.

    Args:
        key (str): Pressed key identifier.
    """
    if key == 'escape' or key == 'q':
        mouse.locked = False
        application.quit()
    elif key == 'r':
        reset_player()


if __name__ == "__main__":
    app.run()
    if viewer_mode == "inspect":
        cap.release()
    else:
        tracker.stop()
    cv2.destroyAllWindows()