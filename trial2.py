"""
Interactive 3D Model & Point Cloud Viewer for Hand-AR Project.
Thin wrapper for backward compatibility — delegates to handarm.engine.viewer.

Usage:
    python3 trial2.py [model_path] [mode]
    mode: 'inspect' (default) or 'explore'
"""
from handarm.engine.viewer import main

if __name__ == "__main__":
    main()