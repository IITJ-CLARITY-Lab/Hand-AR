# this is an test file, contents present in this file are not used anywhere in the project.
from ursina import *
import pandas as pd
import sys
import os
from covariance_align import auto_align_up_axis

# Read the file path passed from the UI
csv_path = "/home/dhaniya/Desktop/pickplace/models/pointcloud_sample.csv" # default
if len(sys.argv) > 1:
    csv_path = sys.argv[1]
    
app = Ursina()

# 1. Load CSV using the dynamic path
df = pd.read_csv(csv_path)


# 2. Downsample (take every 10th point)
df = df.iloc[:10]

# 3. Dynamically align the axes using covariance
df = auto_align_up_axis(df)

# 4. Extract coordinates
vertices = [
    Vec3(x, y, z)
    for x, y, z in zip(df["x"], df["y"], df["z"])
]

# 5. Extract and normalize colors (0-255 -> 0.0-1.0)
point_colors = [
    (r / 255.0, g / 255.0, b / 255.0, 1.0)
    for r, g, b in zip(df["r"], df["g"], df["b"])
]

# 6. Pass the colors list into the Mesh
mesh = Mesh(
    vertices=vertices,
    colors=point_colors,
    mode='point',
    thickness=0.009
)

# Render point cloud
Entity(model=mesh)

# Render XYZ Axes (X=Red, Y=Green, Z=Blue)
axis_length = 20
Entity(model=Mesh(vertices=[Vec3(0,0,0), Vec3(axis_length, 0, 0)], mode='line', thickness=3), color=color.red)
Entity(model=Mesh(vertices=[Vec3(0,0,0), Vec3(0, axis_length, 0)], mode='line', thickness=3), color=color.green)
Entity(model=Mesh(vertices=[Vec3(0,0,0), Vec3(0, 0, axis_length)], mode='line', thickness=3), color=color.blue)

EditorCamera()

app.run()