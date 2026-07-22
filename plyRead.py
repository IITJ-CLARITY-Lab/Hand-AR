import open3d as o3d
import numpy as np
import pandas as pd

def load_ply(ply_path, step):
    """
    laod a ply point cloud and return a dataframe with:
    x, y, z, r, g, b
    """

    print(f"loadingg : {ply_path}")

    pcd = o3d.io.read_point_cloud(ply_path)
    points = np.asarray(pcd.points)
    colors = (np.asarray(pcd.colors) * 255).astype(np.uint8)

    if step > 1:
        points = points[::step]
        colors = colors[::step]

    df = pd.DataFrame({
        "x": points[:,0],
        "y": points[:,1],
        "z": points[:,2],
        "r": colors[:,0],
        "g": colors[:,1],
        "b": colors[:,2]
    })

    print("loaded : ",len(df), "points")

    return df

