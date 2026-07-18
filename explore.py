# this is an test file, contents present in this file are not used anywhere in the project.
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from panda3d.core import Texture as P3DTexture
import pandas as pd
import numpy as np
import cv2
import mediapipe as mp
import threading
import time
import sys
import os
import psutil
from covariance_align import auto_align_up_axis

# ==========================================
# 1. FILE LOADING
# ==========================================
csv_path = "pointcloud_sample.csv" # default fallback
if len(sys.argv) > 1:
    csv_path = sys.argv[1]

if not os.path.exists(csv_path):
    print(f"ERROR: Model file not found: {csv_path}")
    sys.exit(1)

# ==========================================
# 2. THREADED HAND TRACKER WITH VIDEO
# ==========================================
class HandTracker:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
        self.cap = cv2.VideoCapture(0)
        
        self.state = {
            'Left': {
                'visible': False, 'x': 0.5, 'y': 0.5,
                'fist': False, 'open_palm': False, 'index_up': False,
                'index_down': False, 'palm_down': False, 'peace': False,
                'thumbs_up': False, 'gesture': 'None'
            },
            'Right': {
                'visible': False, 'x': 0.5, 'y': 0.5,
                'fist': False, 'open_palm': False, 'thumbs_up': False,
                'gesture': 'None'
            }
        }
        self.latest_frame = None
        self.running = True
        self.thread = threading.Thread(target=self._update_frames, daemon=True)
        self.thread.start()

    def _update_frames(self):
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
                    self.mp_drawing.draw_landmarks(img_rgb, hand_lms, self.mp_hands.HAND_CONNECTIONS)
                    hand_type = results.multi_handedness[idx].classification[0].label
                    
                    st = self.state[hand_type]
                    st['visible'] = True
                    st['x'] = hand_lms.landmark[0].x
                    st['y'] = hand_lms.landmark[0].y
                    
                    # Logic for fingers
                    ring_up    = hand_lms.landmark[16].y < hand_lms.landmark[14].y
                    index_up   = hand_lms.landmark[8].y < hand_lms.landmark[6].y
                    middle_up  = hand_lms.landmark[12].y < hand_lms.landmark[10].y
                    ring_down  = hand_lms.landmark[16].y > hand_lms.landmark[14].y
                    thumb_up   = hand_lms.landmark[4].y < hand_lms.landmark[3].y
                    pinky_up   = hand_lms.landmark[20].y < hand_lms.landmark[18].y
                    pinky_down = hand_lms.landmark[20].y > hand_lms.landmark[18].y
                    
                    st['peace']     = (index_up and middle_up and ring_down and pinky_down)
                    st['open_palm'] = (index_up and middle_up and ring_up and pinky_up)
                    st['fist']      = (not index_up and not middle_up and not ring_up and not pinky_up)
                    st['index_up']  = (index_up and not middle_up and not ring_up and not pinky_up)
                    
                    wrist_y = hand_lms.landmark[0].y
                    wrist = hand_lms.landmark[0]

                    thumb_dist  = ((hand_lms.landmark[4].x - wrist.x)**2 + (hand_lms.landmark[4].y - wrist.y)**2) ** 0.5
                    index_dist  = ((hand_lms.landmark[8].x - wrist.x)**2 + (hand_lms.landmark[8].y - wrist.y)**2) ** 0.5
                    middle_dist = ((hand_lms.landmark[12].x - wrist.x)**2 + (hand_lms.landmark[12].y - wrist.y)**2) ** 0.5
                    ring_dist   = ((hand_lms.landmark[16].x - wrist.x)**2 + (hand_lms.landmark[16].y - wrist.y)**2) ** 0.5
                    pinky_dist  = ((hand_lms.landmark[20].x - wrist.x)**2 + (hand_lms.landmark[20].y - wrist.y)**2) ** 0.5
                    
                    st['index_down'] = (index_dist > middle_dist + 0.05 and index_dist > ring_dist + 0.05 and index_dist > pinky_dist + 0.05)
                    st['thumbs_up']  = (thumb_dist > index_dist + 0.05 and thumb_dist > middle_dist + 0.05 and thumb_dist > ring_dist + 0.05 and thumb_dist > pinky_dist + 0.05)
                    st['palm_down']  = (hand_lms.landmark[8].y > wrist_y and hand_lms.landmark[12].y > wrist_y and hand_lms.landmark[16].y > wrist_y and hand_lms.landmark[20].y > wrist_y)

                    if hand_type == 'Right':
                        if st['open_palm']: st['gesture'] = 'Steering'
                        elif st['fist']:    st['gesture'] = 'View Locked'
                        else:               st['gesture'] = 'None'
                    else:
                        if st['thumbs_up']: st['gesture'] = 'Reset'
                        elif st['peace']:   st['gesture'] = 'Toggle Flight'
                        elif st['palm_down'] and not hand_lms.landmark[8].y > hand_lms.landmark[12].y: st['gesture'] = 'Backward'
                        elif st['index_down']: st['gesture'] = 'Down'
                        elif st['index_up']:   st['gesture'] = 'Up'
                        elif st['open_palm']:  st['gesture'] = 'Forward'
                        elif st['fist']:       st['gesture'] = 'Stop'
                        else:                  st['gesture'] = 'None'
            
            cv2.putText(img_rgb, f"LEFT : {self.state['Left']['gesture']}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
            cv2.putText(img_rgb, f"RIGHT: {self.state['Right']['gesture']}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
            self.latest_frame = cv2.resize(img_rgb, (320, 240))
            time.sleep(0.01)

    def stop(self):
        self.running = False
        self.cap.release()

# ==========================================
# 3. URSINA SETUP & UI
# ==========================================
app = Ursina()
window.color = color.color(0, 0, 0.08)
tracker = HandTracker()

# --- Performance UI ---
fps_text = Text("FPS: --", position=(0.68, 0.46), scale=0.85, color=color.lime)
cpu_text = Text("CPU: --", position=(0.68, 0.41), scale=0.85, color=color.orange)
ram_text = Text("RAM: --", position=(0.68, 0.36), scale=0.85, color=color.cyan)

# --- Webcam UI ---
FEED_W, FEED_H = 320, 240
_p3d_tex = P3DTexture('camera_feed')
_p3d_tex.setup2dTexture(FEED_W, FEED_H, P3DTexture.TUnsignedByte, P3DTexture.FRgb)
_p3d_tex.setMagfilter(P3DTexture.FTLinear)
_p3d_tex.setMinfilter(P3DTexture.FTLinear)

Entity(parent=camera.ui, model='quad', scale=(0.445, 0.315), position=(-0.67, -0.335), color=color.color(0, 0, 0.35), z=0.01)
camera_feed_view = Entity(parent=camera.ui, model='quad', scale=(0.44, 0.31), position=(-0.67, -0.335))
camera_feed_view.model.setTexture(_p3d_tex)
Text("LIVE", position=(-0.67, -0.168), scale=0.9, color=color.red)

# --- Explration UI ---
legend = Text(
    text=
    "<yellow>HAND CONTROLS\n\n"
    "<orange>RIGHT HAND (ALWAYS ACTIVE)\n"
    "<white>🖐 Open Palm   : Enable View Control\n"
    "<white>✊ Fist        : Freeze View\n"
    "<white>← Move Left   : Look Left\n"
    "<white>→ Move Right  : Look Right\n"
    "<white>↑ Move Up     : Look Up\n"
    "<white>↓ Move Down   : Look Down\n\n"
    "<cyan>LEFT HAND (WALK MODE)\n"
    "<white>✌ Peace       : Toggle Flight Mode\n"
    "<white>🖐 move palm up   : Move Forward\n"
    "<white>🖐 move palm Down   : Move Backward\n"
    "<white>✊ Fist        : Stop\n\n"
    "<lime>LEFT HAND (FLIGHT MODE)\n"
    "<white> thumbs up     : position Reset\n"
    "<white>✌ Peace       : Toggle Walk Mode\n"
    "<white>☝  Index Up    : Fly Up\n"
    "<white>👇  Index Down  : Fly Down\n"
    "<white>🖐 move Palm up  : Fly Forward\n"
    "<white>🖐 move Palm Down   : Fly Backward\n"
    "<white>✊ Fist        : ...",
    position=window.top_left + Vec2(0.02, -0.02),
    origin=(-0.5, 0.5), scale=0.8, background=True
)

right_status = Text(text="Right: Not Detected", position=(0.3, -0.35), scale=1.2, color=color.orange)
left_status = Text(text="Left: Not Detected", position=(0.3, -0.40), scale=1.2, color=color.cyan)
flight_status = Text(text="Mode: Grounded", position=(0.3, -0.45), scale=1.2, color=color.green)

# ==========================================
# 4. POINT CLOUD & WORLD SETUP
# ==========================================
print("Loading Point Cloud Environment...")
df = pd.read_csv(csv_path)
df = df.iloc[::6] # Less aggressive downsampling for roaming
df = auto_align_up_axis(df)

points_xz = np.array([df["x"], df["z"]]).T
points_y = np.array(df["y"])

min_x, max_x = np.min(points_xz[:, 0]) + 1.0, np.max(points_xz[:, 0]) - 1.0
min_z, max_z = np.min(points_xz[:, 1]) + 1.0, np.max(points_xz[:, 1]) - 1.0

vertices = [Vec3(x, y, z) for x, y, z in zip(df["x"], df["y"], df["z"])]
point_colors = [(r / 255.0, g / 255.0, b / 255.0, 1.0) for r, g, b in zip(df["r"], df["g"], df["b"])]
mesh = Mesh(vertices=vertices, colors=point_colors, mode='point', thickness=4) # Adjusted thickness for visibility
Entity(model=mesh)

player = FirstPersonController()
player.gravity = 0 
player.speed = 0 
player.mouse_sensitivity = Vec2(0, 0) 
player.prev_x, player.prev_z = player.x, player.z
spawn_position = None
spawn_rotation = None
spawn_initialized = False

is_flying = False
flight_toggle_cooldown = 4 

def reset_player():
    if spawn_initialized:
        player.position = spawn_position
        player.rotation_x = spawn_rotation.x
        player.rotation_y = spawn_rotation.y
        player.rotation_z = spawn_rotation.z
        player.prev_x = player.x
        player.prev_z = player.z

def update():
    global is_flying, flight_toggle_cooldown
    global spawn_position, spawn_rotation, spawn_initialized

    # --- UPDATE PERFORMANCE COUNTERS ---
    fps = int(1 / time.dt) if time.dt > 0 else 0
    fps_text.text = f"FPS: {fps}"
    cpu_text.text = f"CPU: {psutil.cpu_percent(interval=None):.0f}%"
    ram_text.text = f"RAM: {psutil.virtual_memory().percent:.0f}%"
    
    # --- UPDATE WEBCAM FEED ---
    if tracker.latest_frame is not None:
        small = np.flipud(tracker.latest_frame)
        small = np.ascontiguousarray(small, dtype=np.uint8)
        buf = _p3d_tex.modifyRamImage()
        memoryview(buf).cast('B')[:] = small.tobytes()
        _p3d_tex.setRamImage(buf)

    # --- UPDATE UI ---
    left = tracker.state['Left']
    right = tracker.state['Right']
    
    left_status.text = f"Left: {left['gesture']}" if left['visible'] else "Left: Not Detected"
    right_status.text = f"Right: {right['gesture']}" if right['visible'] else "Right: Not Detected"

    # --- RIGHT HAND: STEERING ---
    if right['visible'] and right['gesture'] == 'Steering':
        if right['x'] < 0.4: player.rotation_y -= 80 * time.dt * (0.4 - right['x'])
        elif right['x'] > 0.6: player.rotation_y += 80 * time.dt * (right['x'] - 0.6)
            
        if right['y'] < 0.4: player.rotation_x -= 60 * time.dt * (0.4 - right['y'])
        elif right['y'] > 0.6: player.rotation_x += 60 * time.dt * (right['y'] - 0.6)

    # --- LEFT HAND: ACTIONS ---
    if left['visible']:
        if left['gesture'] == 'Toggle Flight' and time.time() > flight_toggle_cooldown:
            is_flying = not is_flying
            flight_toggle_cooldown = time.time() + 1.0
            flight_status.text = "Mode: Flying" if is_flying else "Mode: Grounded"
            flight_status.color = color.red if is_flying else color.green

        if left['gesture'] == 'Reset':
            reset_player()

        if not is_flying:
            if left['gesture'] == 'Backward':
                player.position -= player.forward * 2.0 * time.dt
            elif left['gesture'] == 'Forward':
                player.position += player.forward * 2.0 * time.dt

    # --- TERRAIN TRACKING & BOUNDARIES ---
    px, pz = player.x, player.z
    dists_sq = (points_xz[:, 0] - px)**2 + (points_xz[:, 1] - pz)**2

    ground_mask = dists_sq < (3.0 ** 2)
    ground_y = player.y - 2.0
    
    if np.any(ground_mask):
        local_y_values = points_y[ground_mask]
        ground_y = np.percentile(local_y_values, 25)

    if is_flying:
        if left['visible']:
            if left['gesture'] == 'Up':          player.y += 2 * time.dt
            elif left['gesture'] == 'Down':      player.y -= 2 * time.dt
            elif left['gesture'] == 'Backward':  player.position -= player.forward * 2.0 * time.dt
            elif left['gesture'] == 'Forward':   player.position += player.forward * 2.0 * time.dt
        
        if player.y < ground_y + 0.2:
            player.y = ground_y + 0.2
            
    else:
        player.y = lerp(player.y, ground_y + 0.2, time.dt * 10)
        if not spawn_initialized:
            spawn_position = Vec3(player.position)
            spawn_rotation = Vec3(player.rotation_x, player.rotation_y, player.rotation_z)
            spawn_initialized = True

    player.x = clamp(player.x, min_x, max_x)
    player.z = clamp(player.z, min_z, max_z)

    collision_mask = dists_sq < (0.3 ** 2)
    if np.any(collision_mask):
        close_points_y = points_y[collision_mask]
        local_foot_level = np.min(close_points_y)
        
        if player.y < local_foot_level + 1.0: 
            hitting_object = np.any((close_points_y > local_foot_level + 0.15) & (close_points_y < local_foot_level + 0.5))
            if hitting_object:
                player.x = player.prev_x
                player.z = player.prev_z
            else:
                player.prev_x = player.x
                player.prev_z = player.z
    else:
        player.prev_x = player.x
        player.prev_z = player.z
        
def input(key):
    if key == 'escape' or key == 'q':
        mouse.locked = False
        application.quit()
    elif key == 'r':
        reset_player()

app.run()
tracker.stop()