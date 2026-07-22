# Hand-ArM2

## Gesture-Based 3D Model Inspection and Point Cloud Exploration System

Hand-ArM2 is a real-time computer vision and human-computer interaction platform that enables users to interact with 3D assets using natural hand gestures. The system combines MediaPipe hand tracking, OpenCV, Ursina Engine, Panda3D rendering, and point cloud visualization into a unified interface optimized for Raspberry Pi 5.

The project was designed to provide an intuitive touchless interaction system for both traditional 3D models and large-scale point cloud environments while maintaining low-latency performance on embedded hardware.

---

# Features

## Inspect Mode

Designed for viewing, manipulating, and examining individual 3D assets.

### Supported Formats

* `.glb`
* `.obj`
* `.ply`

### Right Hand Controls

* Index Finger Movement → Rotate Model
* Pinch Close → Zoom In
* Pinch Apart → Zoom Out
* Peace Sign (Paused State) → Capture Screenshot

### Left Hand Controls

* Wrist Movement → Translate Model
* Open Palm → Pause Interaction

### Additional Features

* Front View Preset
* Side View Preset
* Top View Preset
* Isometric View Preset
* Adjustable Rotation Sensitivity
* Adjustable Translation Sensitivity
* Adjustable Zoom Sensitivity
* Screenshot Capture System
* Live Camera Feed Overlay
* FPS Monitoring
* CPU Usage Monitoring
* RAM Usage Monitoring

---

## Explore Mode

Designed for immersive navigation through large-scale point cloud environments.

### Supported Formats

* `.ply`

### Core Features

* First-Person Navigation
* Walk Mode
* Flight Mode
* Dynamic Spawn Positioning
* Ground Detection
* Point Cloud Collision Handling
* Automatic Height-Axis Alignment
* Real-Time Hand-Controlled Navigation
* Environment Boundary Constraints
* Position Reset System

### Right Hand (View Control)

* Open Palm → Enable Camera Steering
* Fist → Lock View
* Move Left → Look Left
* Move Right → Look Right
* Move Up → Look Up
* Move Down → Look Down

### Left Hand (Walk Mode)

* Peace Sign → Toggle Flight Mode
* Open Palm Up → Move Forward
* Open Palm Down → Move Backward
* Fist → Stop Movement

### Left Hand (Flight Mode)

* Thumbs Up → Reset Position
* Peace Sign → Return to Walk Mode
* Index Up → Fly Up
* Index Down → Fly Down
* Open Palm Up → Fly Forward
* Open Palm Down → Fly Backward
* Fist → Stop

---

# System Architecture

```text
Camera Feed
      ↓
MediaPipe Hand Tracking
      ↓
Gesture Recognition
      ↓
Interaction Engine
      ↓
Inspect Mode / Explore Mode
      ↓
Ursina + Panda3D Renderer
      ↓
3D Model or Point Cloud
```

---

# Point Cloud Processing Pipeline

```text
PLY Point Cloud
      ↓
Open3D Loader
      ↓
DataFrame Conversion
      ↓
Covariance-Based Axis Alignment
      ↓
Point Sampling
      ↓
Ursina Point Renderer
      ↓
Inspect / Explore Mode
```

Hand-ArM2 automatically analyzes point cloud covariance and attempts to align the flattest plane to Ursina's X-Z ground plane. This allows datasets originating from different coordinate systems to be navigated without manual axis correction.

---

# Raspberry Pi 5 Setup

## Install Build Dependencies

```bash
sudo apt update

sudo apt install -y \
build-essential \
libssl-dev \
zlib1g-dev \
libbz2-dev \
libreadline-dev \
libsqlite3-dev \
libncurses-dev \
libffi-dev \
liblzma-dev \
tk-dev \
xz-utils \
curl \
git
```

---

## Install Pyenv

```bash
curl https://pyenv.run | bash
```

Add the following lines to:

```bash
~/.bashrc
```

```bash
export PYENV_ROOT="$HOME/.pyenv"
[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init - bash)"
```

Reload the shell:

```bash
source ~/.bashrc
```

---

## Install Python 3.10.14

```bash
pyenv install 3.10.14
pyenv local 3.10.14

python --version
```

Expected output:

```text
Python 3.10.14
```

---

# Clone Repository

```bash
git clone <repository-url>
cd Hand-ArM2
```

---

# Create Virtual Environment

```bash
python -m venv handtrack_env

source handtrack_env/bin/activate
```

Optional Linux line-ending fix:

```bash
sudo apt install dos2unix

dos2unix handtrack_env/bin/activate

source handtrack_env/bin/activate
```

---

# Install Dependencies

```bash
pip install --upgrade pip

pip install -r requirements.txt
```

---

# requirements.txt

```text
ursina==7.0.0
Panda3D==1.10.16
panda3d-gltf==1.3.0
panda3d-simplepbr==0.13.1

mediapipe==0.10.9
opencv-python==4.9.0.80
opencv-contrib-python==4.9.0.80

numpy==1.26.4
pandas==2.3.3
open3d==0.18.0

Pillow==10.3.0

psutil>=5.9.0
python-dotenv>=1.0.0
requests>=2.31.0

screeninfo==0.8.1
pyperclip==1.11.0

protobuf==3.20.3
```

---

# Dataset Setup

Download the project dataset from the provided Google Drive link.
https://drive.google.com/drive/folders/1CKM0WH3iW31OLrN-uACTaRCPQT6CEjc0
Current dataset organization:

```text
data/
├── inspect/
└── explore/
```

The current dataset primarily contains PLY point-cloud environments intended for Explore Mode.

Copy all downloaded assets into:

```text
models/
```

Example:

```text
Hand-ArM2/
│
├── models/
│   ├── IIMAS_5mill.ply
│   ├── ground_pointcloud.ply
│   ├── Old_Rusty_Car.glb
│   └── ...
│
└── database.json
```

---

# database.json Configuration

Hand-ArM2 uses `database.json` as the central asset registry and discovery database.

Every asset is stored with metadata describing:

* Asset Name
* Local Path
* Source
* Launch Mode

Example:

```json
{
  "results": [
    {
      "name": "Old_Rusty_Car.glb",
      "path": "/home/user/Hand-ArM2/models/Old_Rusty_Car.glb",
      "source": "local",
      "mode": "inspect"
    },

    {
      "name": "IIMAS_5mill.ply",
      "path": "/home/user/Hand-ArM2/models/IIMAS_5mill.ply",
      "source": "local",
      "mode": "explore"
    }
  ]
}
```

## Mode Assignment

### Inspect Mode

Recommended for:

* `.glb`
* `.obj`
* Small `.ply` object scans
* Character Models
* Vehicles
* Buildings
* Individual Objects

### Explore Mode

Recommended for:

* Large `.ply` point clouds
* Campus Scans
* Terrain Reconstructions
* LiDAR Environments
* Indoor Mapping Datasets
* Urban Point Clouds

## Manual Tagging

The `mode` field determines how the asset will be launched.

```json
{
  "name": "IIMAS_5mill.ply",
  "mode": "explore"
}
```

```json
{
  "name": "Old_Rusty_Car.glb",
  "mode": "inspect"
}
```

This manual tagging approach allows complete control over asset behavior regardless of file extension.

---

# Sketchfab Integration (Optional)

Hand-ArM2 supports searching and downloading downloadable Sketchfab assets.

Create a `.env` file:

```env
SKETCHFAB_TOKEN=YOUR_TOKEN_HERE
```

Once configured:

```text
Sketchfab Search
      ↓
Download Asset
      ↓
Store in models/
      ↓
Add to database.json
      ↓
Assign Mode
      ↓
Launch
```

If no API token is provided, the application continues to function normally using local assets.

---

# Running the Application

Launch the main menu:

```bash
python opening.py
```

Workflow:

```text
Opening Menu
      ↓
Asset Selection
      ↓
database.json Mode Detection
      ↓
Inspect Mode or Explore Mode
      ↓
Gesture-Based Interaction
```

---

# Performance Optimizations

The system includes several optimizations for Raspberry Pi 5:

* Reduced camera feed resolution
* Point cloud sampling
* MediaPipe confidence tuning
* Lightweight Ursina rendering
* Efficient point-cloud collision detection
* Background hand-tracking thread in Explore Mode
* Real-time performance monitoring

The focus of the project is responsive real-time interaction rather than full-resolution rendering of extremely large datasets.

---

# Project Structure

```text
Hand-ArM2/
│
├── opening.py
├── trial2.py
├── glb_scanner.py
├── covariance_align.py
├── plyRead.py
│
├── database.json
├── requirements.txt
├── .env
│
├── models/
│
└── screenshots/
```

---

# Technologies Used

* Python 3.10.14
* MediaPipe
* OpenCV
* Ursina Engine
* Panda3D
* Open3D
* NumPy
* Pandas
* Tkinter
* Raspberry Pi 5

---

# License

Add your preferred license information here.
